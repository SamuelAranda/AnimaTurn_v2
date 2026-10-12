from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import random
from pathlib import Path
import socket
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

clients = []
personajes = []
next_personaje_id = 1

rondas = []
ronda_actual = 0
turno_actual = 0
STATE_FILE = Path("session_state.json")

TIPOS_JUGADOR = {"jugador", "aliado"}
TIPOS_ENEMIGO = {"enemigo", "pnj"}
TIPOS_VALIDOS = TIPOS_JUGADOR | TIPOS_ENEMIGO

# Colores admitidos para los Estados/Tags personalizados.
ESTADOS_COLORES = {"rojo", "verde", "amarillo", "azul", "naranja", "morado"}
ESTADOS_MAX = 20
ESTADO_TEXTO_MAX = 24


async def broadcast(message):
    disconnected = []
    for client in clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        if client in clients:
            clients.remove(client)


def guardar_estado():
    payload = {
        "personajes": personajes,
        "next_personaje_id": next_personaje_id,
        "rondas": rondas,
        "ronda_actual": ronda_actual,
        "turno_actual": turno_actual,
    }
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def cargar_estado():
    global personajes, next_personaje_id, rondas, ronda_actual, turno_actual
    if not STATE_FILE.exists():
        return
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    personajes = payload.get("personajes", [])
    for personaje in personajes:
        migrar_personaje(personaje)
    next_personaje_id = int(payload.get("next_personaje_id", 1) or 1)
    rondas = payload.get("rondas", [])
    ronda_actual = int(payload.get("ronda_actual", 0) or 0)
    turno_actual = int(payload.get("turno_actual", 0) or 0)

    if not personajes:
        next_personaje_id = 1
    if ronda_actual >= len(rondas):
        ronda_actual = max(len(rondas) - 1, 0)

    tipos_por_id = {p["id"]: p.get("tipo", "") for p in personajes}
    for ronda in rondas:
        for turno in ronda.get("turnos", []):
            turno.setdefault("tipo", tipos_por_id.get(turno.get("id"), ""))
    normalizar_turno_actual()


def migrar_personaje(personaje):
    tipo = personaje.get("tipo")
    if tipo not in TIPOS_VALIDOS:
        bando = personaje.get("bando", "")
        tipo = bando if bando in TIPOS_VALIDOS else "enemigo"
    personaje["tipo"] = tipo

    if "vida_max" not in personaje:
        vida = personaje.get("vida", 0) or 0
        personaje["vida_max"] = vida
        personaje["vida_actual"] = vida
    personaje.setdefault("vida_actual", personaje.get("vida_max", 0))

    if "defensa" not in personaje:
        personaje["defensa"] = personaje.get("parada", 0) or 0

    for clave, defecto in (
        ("velocidad", 0), ("estilo", 0), ("ta", 0), ("ataque", 0),
        ("dano", 0), ("zeon", 0), ("ki", 0),
    ):
        personaje.setdefault(clave, defecto)
    personaje.setdefault("acumulacion", False)
    personaje.setdefault("criticos", [])
    personaje.setdefault("a_la_defensiva", False)
    personaje.setdefault("estados", [])

    for obsoleto in ("bando", "vida", "parada", "esquiva"):
        personaje.pop(obsoleto, None)


def normalizar_turno_actual():
    global turno_actual
    if not rondas:
        turno_actual = 0
        return
    turnos = rondas[ronda_actual].get("turnos", [])
    if not turnos:
        turno_actual = 0
    else:
        turno_actual = max(0, min(turno_actual, len(turnos) - 1))


def esta_debil(personaje):
    vida_max = personaje.get("vida_max", 0) or 0
    if vida_max <= 0:
        return False
    return (personaje.get("vida_actual", 0) or 0) < 0.30 * vida_max


def esta_caido(personaje):
    return (personaje.get("vida_actual", 0) or 0) <= 0


def ta_efectiva(personaje, reduccion=0):
    """TA interna: siempre mínimo 1, aunque el personaje tenga TA 0.

    La reducción de armadura del ataque baja la TA enemiga, sin bajarla nunca de 1.
    """
    ta = int(personaje.get("ta", 0) or 0)
    reduccion = max(0, int(reduccion or 0))
    return max(1, ta - reduccion)


def datos_ficha(personaje):
    """Datos de combate completos. Solo públicos para jugador/aliado."""
    return {
        "vida_max": personaje.get("vida_max", 0),
        "vida_actual": personaje.get("vida_actual", 0),
        "zeon": personaje.get("zeon", 0),
        "ki": personaje.get("ki", 0),
        "ta": personaje.get("ta", 0),
        "dano": personaje.get("dano", 0),
    }


def etiquetas_publicas(personaje):
    return {
        "acumulacion": personaje.get("acumulacion", False),
        "a_la_defensiva": personaje.get("a_la_defensiva", False),
        "criticos": personaje.get("criticos", []),
        "estados": personaje.get("estados", []),
        "debil": esta_debil(personaje),
        "caido": esta_caido(personaje),
    }


def datos_personaje_publicos(personaje):
    """Los datos de combate de enemigos y PNJ nunca se exponen."""
    datos = {
        "id": personaje["id"],
        "nombre": personaje["nombre"],
        "tipo": personaje.get("tipo", ""),
        "velocidad": personaje.get("velocidad", 0),
        "estilo": personaje.get("estilo", 0),
    }
    datos.update(etiquetas_publicas(personaje))
    if personaje.get("tipo") in TIPOS_JUGADOR:
        datos.update(datos_ficha(personaje))
    return datos


def datos_privados(personaje):
    datos = {
        "id": personaje["id"],
        "nombre": personaje["nombre"],
        "tipo": personaje.get("tipo", ""),
        "velocidad": personaje.get("velocidad", 0),
        "estilo": personaje.get("estilo", 0),
        "ataque": personaje.get("ataque", 0),
        "defensa": personaje.get("defensa", 0),
    }
    datos.update(datos_ficha(personaje))
    datos.update(etiquetas_publicas(personaje))
    return datos


def datos_turno_publicos(turno):
    """Los datos de combate secretos nunca viajan al navegador."""
    personaje = buscar_personaje(turno.get("id"))
    datos = {
        "id": turno["id"],
        "nombre": turno["nombre"],
        "tipo": turno.get("tipo", ""),
        "velocidad": turno["velocidad"],
        "estilo": turno.get("estilo", 0),
        "roll": turno["roll"],
        "rolls": turno["rolls"],
        "tirada": turno["tirada"],
        "total": turno["total"],
        "surprise": turno.get("surprise", []),
        "tipo_sorpresa": turno.get("tipo_sorpresa"),
    }
    if personaje:
        datos.update(etiquetas_publicas(personaje))
        if personaje.get("tipo") in TIPOS_JUGADOR:
            datos.update(datos_ficha(personaje))
    return datos


def ronda_publica(ronda):
    return {
        "ronda": ronda["ronda"],
        "turnos": [datos_turno_publicos(t) for t in ronda.get("turnos", [])],
    }


async def enviar_personajes():
    await broadcast({
        "type": "personajes",
        "data": [datos_personaje_publicos(p) for p in personajes],
    })


async def enviar_estado_inicial(ws: WebSocket):
    ronda = rondas[ronda_actual] if rondas else None
    await ws.send_json({
        "type": "init",
        "personajes": [datos_personaje_publicos(p) for p in personajes],
        "ronda_actual": ronda_publica(ronda) if ronda else None,
        "indice_turno": turno_actual,
        "hay_sesion": bool(rondas),
    })


def mostrar_direcciones():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
    except OSError:
        ip_local = "127.0.0.1"
    finally:
        s.close()
    puerto = 8000
    print("\n==============================")
    print(f"http://localhost:{puerto}")
    print(f"http://{ip_local}:{puerto}")
    print("==============================\n")


@app.on_event("startup")
async def startup_event():
    cargar_estado()
    mostrar_direcciones()


@app.get("/")
async def get():
    with open("templates/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global rondas, ronda_actual, next_personaje_id, turno_actual

    await ws.accept()
    clients.append(ws)
    await enviar_estado_inicial(ws)

    try:
        while True:
            data = await ws.receive_json()
            message_type = data.get("type")

            if message_type == "add":
                personaje, error = construir_personaje(data.get("personaje") or {})
                if error:
                    await ws.send_json({"type": "error", "message": error})
                    continue

                personajes.append(personaje)
                if rondas:
                    # Sin turno en la ronda actual: entra a partir de la siguiente.
                    for ronda in rondas[ronda_actual + 1:]:
                        ronda["turnos"].append(crear_turno_personaje(personaje))
                        recalcular_sorpresas(ronda["turnos"], ronda["ronda"])

                await broadcast({
                    "type": "add",
                    "personaje": datos_personaje_publicos(personaje),
                })
                guardar_estado()
                await enviar_personajes()
                if rondas:
                    await enviar_ronda_actual()
                await ws.send_json({"type": "character_saved"})

            elif message_type == "roll":
                for personaje in personajes:
                    personaje["a_la_defensiva"] = False
                rondas = generar_iniciativa()
                ronda_actual = 0
                turno_actual = 0
                guardar_estado()
                await enviar_personajes()
                await enviar_ronda_actual()

            elif message_type == "delete":
                try:
                    personaje_id = int(data.get("id", 0) or 0)
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "message": "ID de personaje no válido."})
                    continue

                personajes[:] = [p for p in personajes if p["id"] != personaje_id]
                for ronda in rondas:
                    ronda["turnos"] = [t for t in ronda["turnos"] if t["id"] != personaje_id]
                    recalcular_sorpresas(ronda["turnos"], ronda["ronda"])
                normalizar_turno_actual()
                await broadcast({"type": "delete", "id": personaje_id})
                guardar_estado()
                await enviar_personajes()
                if rondas:
                    await enviar_ronda_actual()

            elif message_type == "set_active":
                if not rondas:
                    await ws.send_json({"type": "error", "message": "Genera la iniciativa primero."})
                    continue
                try:
                    personaje_id = int(data.get("id"))
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "message": "ID de personaje no válido."})
                    continue
                turnos = rondas[ronda_actual].get("turnos", [])
                nuevo_indice = next((i for i, t in enumerate(turnos) if t["id"] == personaje_id), None)
                if nuevo_indice is None:
                    await ws.send_json({"type": "error", "message": "El personaje no está en la ronda actual."})
                    continue
                turno_actual = nuevo_indice
                guardar_estado()
                await enviar_ronda_actual()

            elif message_type == "next":
                if rondas:
                    turnos = rondas[ronda_actual].get("turnos", [])
                    if turno_actual < len(turnos) - 1:
                        turno_actual += 1
                    elif ronda_actual < len(rondas) - 1:
                        ronda_actual += 1
                        turno_actual = 0
                        for personaje in personajes:
                            personaje["a_la_defensiva"] = False
                        # Reconsulta velocidad/estilo y vuelve a tirar la ronda que entra.
                        regenerar_ronda(ronda_actual)
                guardar_estado()
                await enviar_personajes()
                await enviar_ronda_actual()

            elif message_type == "get_character":
                try:
                    personaje_id = int(data.get("id"))
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "message": "ID de personaje no válido."})
                    continue
                personaje = buscar_personaje(personaje_id)
                if not personaje:
                    await ws.send_json({"type": "error", "message": "Personaje no encontrado."})
                    continue
                await ws.send_json({"type": "character", "personaje": datos_privados(personaje)})

            elif message_type == "update_character":
                error = actualizar_personaje(data)
                if error:
                    await ws.send_json({"type": "error", "message": error})
                    continue
                guardar_estado()
                await enviar_personajes()
                if rondas:
                    await enviar_ronda_actual()
                await ws.send_json({"type": "character_saved"})

            elif message_type == "critical_level":
                error = registrar_critico(data)
                if error:
                    await ws.send_json({"type": "error", "message": error})
                    continue
                guardar_estado()
                await enviar_personajes()
                if rondas:
                    await enviar_ronda_actual()

            elif message_type == "set_estados":
                error = actualizar_estados(data)
                if error:
                    await ws.send_json({"type": "error", "message": error})
                    continue
                guardar_estado()
                await enviar_personajes()
                if rondas:
                    await enviar_ronda_actual()

            elif message_type == "attack":
                resultado = resolver_ataque(data)
                if resultado.get("error"):
                    await ws.send_json({"type": "error", "message": resultado["error"]})
                else:
                    await broadcast({"type": "attack_result", "data": resultado})
                    guardar_estado()
                    await enviar_personajes()
                    if rondas:
                        await enviar_ronda_actual()

            elif message_type == "counterattack":
                resultado = resolver_ataque(data, contraataque=True)
                if resultado.get("error"):
                    await ws.send_json({"type": "error", "message": resultado["error"]})
                else:
                    await broadcast({"type": "attack_result", "data": resultado})
                    guardar_estado()
                    await enviar_personajes()
                    if rondas:
                        await enviar_ronda_actual()

            elif message_type == "clear":
                personajes.clear()
                rondas = []
                ronda_actual = 0
                turno_actual = 0
                next_personaje_id = 1
                await broadcast({"type": "clear"})
                guardar_estado()

            else:
                await ws.send_json({"type": "error", "message": "Acción desconocida."})

    except Exception as e:
        print("ERROR:", e)
    finally:
        if ws in clients:
            clients.remove(ws)


def construir_personaje(raw):
    global next_personaje_id
    nombre = str(raw.get("nombre", "")).strip()
    if not nombre:
        return None, "El nombre es obligatorio."

    tipo = str(raw.get("tipo", "")).strip().lower()
    if tipo not in TIPOS_VALIDOS:
        return None, "El tipo de personaje no es válido."

    try:
        velocidad = int(raw.get("velocidad", 0))
        estilo = int(raw.get("estilo", 0) or 0)
        vida = float(raw.get("vida", raw.get("vida_max")))
        ta = int(raw.get("ta"))
        zeon = float(raw.get("zeon", 0) or 0)
        ki = float(raw.get("ki", 0) or 0)
        dano = float(raw.get("dano", 0) or 0)
        if tipo in TIPOS_ENEMIGO:
            ataque = int(raw.get("ataque"))
            defensa = int(raw.get("defensa"))
        else:
            ataque = 0
            defensa = 0
    except (TypeError, ValueError):
        if tipo in TIPOS_ENEMIGO:
            return None, "Revisa los valores. Vida, TA, Ataque y Defensa son obligatorios."
        return None, "Revisa los valores. Puntos de Vida y TA son obligatorios."

    personaje = {
        "id": next_personaje_id,
        "nombre": nombre[:100],
        "tipo": tipo,
        "velocidad": velocidad,
        "vida_max": vida,
        "vida_actual": vida,
        "zeon": zeon,
        "ki": ki,
        "estilo": estilo,
        "ta": ta,
        "dano": dano,
        "acumulacion": bool(raw.get("acumulacion", False)),
        "ataque": ataque,
        "defensa": defensa,
        "criticos": [],
        "a_la_defensiva": False,
        "estados": [],
    }
    next_personaje_id += 1
    return personaje, None


def actualizar_personaje(data):
    try:
        personaje_id = int(data.get("id"))
    except (TypeError, ValueError):
        return "ID de personaje no válido."
    personaje = buscar_personaje(personaje_id)
    if not personaje:
        return "Personaje no encontrado."

    if "nombre" in data:
        nombre = str(data.get("nombre", "")).strip()
        if not nombre:
            return "El nombre es obligatorio."
        if nombre != personaje["nombre"]:
            renombrar_personaje(personaje_id, nombre[:100])

    try:
        if "velocidad" in data:
            personaje["velocidad"] = int(data["velocidad"])
        if "vida_max" in data:
            personaje["vida_max"] = float(data["vida_max"])
        if "vida_actual" in data:
            personaje["vida_actual"] = float(data["vida_actual"])
        if "zeon" in data:
            personaje["zeon"] = float(data["zeon"])
        if "ki" in data:
            personaje["ki"] = float(data["ki"])
        if "estilo" in data:
            personaje["estilo"] = int(data["estilo"])
        if "ta" in data:
            personaje["ta"] = int(data["ta"])
        if "dano" in data:
            personaje["dano"] = float(data["dano"])
    except (TypeError, ValueError):
        return "Los valores numéricos no son válidos."

    if personaje.get("tipo") in TIPOS_ENEMIGO:
        try:
            if "ataque" in data:
                personaje["ataque"] = int(data["ataque"])
            if "defensa" in data:
                personaje["defensa"] = int(data["defensa"])
        except (TypeError, ValueError):
            return "El ataque o la defensa no son válidos."

    if "acumulacion" in data:
        personaje["acumulacion"] = bool(data["acumulacion"])

    if personaje.get("vida_max", 0) < personaje.get("vida_actual", 0):
        personaje["vida_actual"] = personaje["vida_max"]
    return None


def registrar_critico(data):
    try:
        personaje_id = int(data.get("id"))
        nivel = int(data.get("level"))
    except (TypeError, ValueError):
        return "Nivel de crítico no válido."
    personaje = buscar_personaje(personaje_id)
    if not personaje:
        return "Personaje no encontrado."
    personaje.setdefault("criticos", []).append(nivel)
    return None


def actualizar_estados(data):
    """Sustituye los Estados/Tags personalizados de un personaje (texto alfanumérico + color)."""
    try:
        personaje_id = int(data.get("id"))
    except (TypeError, ValueError):
        return "ID de personaje no válido."
    personaje = buscar_personaje(personaje_id)
    if not personaje:
        return "Personaje no encontrado."

    estados_raw = data.get("estados")
    if not isinstance(estados_raw, list):
        return "Los estados no son válidos."

    estados = []
    for estado in estados_raw[:ESTADOS_MAX]:
        if not isinstance(estado, dict):
            continue
        texto = str(estado.get("texto", "")).strip()
        if not texto:
            continue
        color = str(estado.get("color", "")).strip().lower()
        if color not in ESTADOS_COLORES:
            color = "azul"
        estados.append({"texto": texto[:ESTADO_TEXTO_MAX], "color": color})
    personaje["estados"] = estados
    return None


def renombrar_personaje(personaje_id, nombre):
    personaje = buscar_personaje(personaje_id)
    if not personaje:
        return
    personaje["nombre"] = nombre
    for ronda in rondas:
        for turno in ronda.get("turnos", []):
            if turno["id"] == personaje_id:
                turno["nombre"] = nombre


async def enviar_ronda_actual():
    if not rondas:
        return
    normalizar_turno_actual()
    ronda = rondas[ronda_actual]
    await broadcast({
        "type": "ronda",
        "data": ronda_publica(ronda),
        "indice_turno": turno_actual,
    })


def buscar_turno(personaje_id):
    if not rondas:
        return None
    for turno in rondas[ronda_actual].get("turnos", []):
        if turno["id"] == personaje_id:
            return turno
    return None


def buscar_personaje(personaje_id):
    return next((p for p in personajes if p["id"] == personaje_id), None)


def tiene_sorpresa(agresor_id, objetivo_id):
    agresor = buscar_turno(agresor_id)
    objetivo = buscar_turno(objetivo_id)
    if not agresor or not objetivo:
        return {"agresor_sorprende": False, "objetivo_sorprende": False}
    return {
        "agresor_sorprende": objetivo["nombre"] in agresor.get("surprise", []),
        "objetivo_sorprende": agresor["nombre"] in objetivo.get("surprise", []),
    }


def redondear_fallo(porcentaje):
    # Todo fallo se comunica en bloques de 10%, redondeando hacia arriba.
    return int((-porcentaje + 9) // 10) * 10


def resolver_ataque(data, contraataque=False):
    try:
        atacante_id = int(data.get("attacker_id"))
        objetivo_id = int(data.get("target_id"))
    except (TypeError, ValueError):
        return {"error": "Datos de ataque no válidos."}

    atacante = buscar_personaje(atacante_id)
    objetivo = buscar_personaje(objetivo_id)
    atacante_turno = buscar_turno(atacante_id)
    objetivo_turno = buscar_turno(objetivo_id)

    if not atacante or not objetivo or not atacante_turno or not objetivo_turno:
        return {"error": "El atacante o el objetivo no están disponibles en la ronda actual."}

    if not contraataque:
        turnos_actuales = rondas[ronda_actual].get("turnos", []) if rondas else []
        if not turnos_actuales or turnos_actuales[turno_actual]["id"] != atacante_id:
            return {"error": "Solo puede actuar el personaje cuyo marcador de turno está activo."}

    if atacante_id == objetivo_id:
        return {"error": "Un personaje no puede atacarse a sí mismo."}

    try:
        numero = int(data.get("numero", 0) or 0)
    except (TypeError, ValueError):
        return {"error": "El número de ataque no es válido."}

    try:
        reduccion_armadura = max(0, int(data.get("reduccion_armadura", 0) or 0))
    except (TypeError, ValueError):
        return {"error": "La reducción de armadura no es válida."}

    # Jugador/aliado introduce el número limpio; enemigo/PNJ usa su Ataque guardado.
    if atacante.get("tipo") in TIPOS_ENEMIGO:
        ataque_final = int(atacante.get("ataque", 0) or 0) + numero
        ataque_detalle = f"{atacante.get('ataque', 0)} + {numero}"
    else:
        ataque_final = numero
        ataque_detalle = f"{numero} (limpio)"

    # Enemigo/PNJ defiende con su Defensa guardada; jugador/aliado introduce la suya limpia.
    if objetivo.get("tipo") in TIPOS_JUGADOR:
        try:
            defensa = int(data.get("defensa_numero", 0) or 0)
        except (TypeError, ValueError):
            return {"error": "La defensa limpia no es válida."}
        defensa_detalle = f"{defensa} (limpia)"
    else:
        defensa = int(objetivo.get("defensa", 0) or 0)
        defensa_detalle = f"{defensa}"

    porcentaje = ataque_final - defensa
    sorpresa = tiene_sorpresa(atacante_id, objetivo_id)

    resultado = {
        "atacante_id": atacante_id,
        "objetivo_id": objetivo_id,
        "atacante": atacante["nombre"],
        "objetivo": objetivo["nombre"],
        "numero": numero,
        "ataque_final": ataque_final,
        "ataque_detalle": ataque_detalle,
        "defensa": defensa,
        "defensa_detalle": defensa_detalle,
        "porcentaje": porcentaje,
        "contraataque": contraataque,
        "sorpresa": sorpresa,
    }

    if porcentaje <= -10:
        resultado["estado"] = "contraataque"
        resultado["fallo"] = redondear_fallo(porcentaje)
        resultado["mensaje"] = f"Contraataque posible: fallo por {resultado['fallo']}%."
        return resultado

    if porcentaje <= 0:
        resultado["estado"] = "fallo"
        resultado["fallo"] = redondear_fallo(porcentaje)
        resultado["mensaje"] = f"Golpe fallido por {resultado['fallo']}%."
        return resultado

    ta = int(objetivo.get("ta", 0) or 0)
    ta_aplicada = ta_efectiva(objetivo, reduccion_armadura)
    porcentaje_post_ta = max(0, porcentaje - ta_aplicada * 10)
    dano_base = atacante.get("dano", 0) or 0
    dano_total = dano_base * porcentaje_post_ta / 100

    vida_antes = objetivo.get("vida_actual", 0) or 0
    objetivo["vida_actual"] = vida_antes - dano_total

    if not objetivo.get("acumulacion"):
        objetivo["a_la_defensiva"] = True

    # Primero se evalúa la caída: si la vida llega a 0 no se ofrece crítico.
    caido = objetivo["vida_actual"] <= 0
    critico = (not caido) and vida_antes > 0 and dano_total >= 0.5 * vida_antes

    resultado.update({
        "estado": "golpe",
        "impacto": True,
        "ta": ta,
        "reduccion_armadura": reduccion_armadura,
        "ta_efectiva": ta_aplicada,
        "porcentaje_post_ta": porcentaje_post_ta,
        "dano_base": dano_base,
        "dano_total": dano_total,
        "vida_antes": vida_antes,
        "vida_actual": objetivo["vida_actual"],
        "critico": critico,
        "caido": caido,
        "a_la_defensiva": objetivo.get("a_la_defensiva", False),
        "mensaje": f"Golpe: {porcentaje_post_ta}% de {dano_base:g} = {dano_total:g} daño.",
    })
    return resultado


def recalcular_sorpresas(turnos, numero_ronda):
    for turno in turnos:
        turno["surprise"] = []
        turno["tipo_sorpresa"] = None
    turnos.sort(key=lambda x: x["total"], reverse=True)
    for t in turnos:
        umbral = obtener_umbral_sorpresa(t["estilo"]) if numero_ronda == 1 else 150
        for other in turnos:
            if t is other:
                continue
            diferencia = t["total"] - other["total"]
            if diferencia >= umbral:
                t["surprise"].append(other["nombre"])
                tipo = obtener_tipo_sorpresa(diferencia)
                if tipo:
                    t["tipo_sorpresa"] = tipo


def crear_turno_personaje(personaje):
    rolls = []
    roll = random.randint(1, 100)
    rolls.append(roll)
    if roll == 1:
        tirada = -125
    elif roll == 2:
        tirada = -100
    elif roll == 3:
        tirada = -75
    else:
        tirada = roll
        umbral_abierta = 90
        while roll >= umbral_abierta and umbral_abierta < 100:
            umbral_abierta += 1
            roll = random.randint(1, 100)
            rolls.append(roll)
            tirada += roll
    total = personaje["velocidad"] + tirada
    return {
        "id": personaje["id"],
        "nombre": personaje["nombre"],
        "tipo": personaje.get("tipo", ""),
        "velocidad": personaje["velocidad"],
        "estilo": personaje.get("estilo", 0),
        "roll": rolls[0],
        "rolls": rolls,
        "tirada": tirada,
        "total": total,
        "surprise": [],
        "tipo_sorpresa": None,
    }


def obtener_umbral_sorpresa(estilo):
    if estilo >= 440:
        return 60
    elif estilo >= 320:
        return 80
    elif estilo >= 280:
        return 90
    elif estilo >= 240:
        return 110
    elif estilo >= 180:
        return 120
    elif estilo >= 140:
        return 130
    elif estilo >= 120:
        return 140
    return 150


def obtener_tipo_sorpresa(diferencia):
    if diferencia >= 440:
        return "ZEN"
    elif diferencia >= 320:
        return "INH"
    elif diferencia >= 280:
        return "IMP"
    elif diferencia >= 240:
        return "CIM"
    elif diferencia >= 180:
        return "ABS"
    elif diferencia >= 140:
        return "MDF"
    elif diferencia >= 120:
        return "DIF"
    return None


def generar_iniciativa():
    if not personajes:
        return []
    todas_rondas = []
    for ronda in range(1, 26):
        turnos = [crear_turno_personaje(p) for p in personajes]
        recalcular_sorpresas(turnos, ronda)
        todas_rondas.append({"ronda": ronda, "turnos": turnos})
    return todas_rondas


def regenerar_ronda(indice):
    """Reconsulta velocidad/estilo actuales y vuelve a tirar la iniciativa de esa ronda."""
    if not rondas or indice >= len(rondas):
        return
    numero = rondas[indice].get("ronda", indice + 1)
    turnos = [crear_turno_personaje(p) for p in personajes]
    recalcular_sorpresas(turnos, numero)
    rondas[indice] = {"ronda": numero, "turnos": turnos}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

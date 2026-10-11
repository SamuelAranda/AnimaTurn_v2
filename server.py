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
        personaje.setdefault("ataque", 0)
        personaje.setdefault("ta", 0)
        personaje.setdefault("parada", 0)
        personaje.setdefault("esquiva", 0)
        personaje.setdefault("dano", 0)
        personaje.setdefault("vida", 0)
    next_personaje_id = int(payload.get("next_personaje_id", 1) or 1)
    rondas = payload.get("rondas", [])
    ronda_actual = int(payload.get("ronda_actual", 0) or 0)
    turno_actual = int(payload.get("turno_actual", 0) or 0)

    if not personajes:
        next_personaje_id = 1
    if ronda_actual >= len(rondas):
        ronda_actual = max(len(rondas) - 1, 0)
    normalizar_turno_actual()


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


def datos_personaje_publicos(personaje):
    """Solo expone datos que no son secretos."""
    return {
        "id": personaje["id"],
        "nombre": personaje["nombre"],
        "velocidad": personaje["velocidad"],
        "estilo": personaje["estilo"],
        "bando": personaje.get("bando", ""),
    }


def datos_turno_publicos(turno):
    """Los datos de combate secretos nunca viajan al navegador."""
    return {
        "id": turno["id"],
        "nombre": turno["nombre"],
        "velocidad": turno["velocidad"],
        "estilo": turno["estilo"],
        "bando": turno.get("bando", ""),
        "roll": turno["roll"],
        "rolls": turno["rolls"],
        "tirada": turno["tirada"],
        "total": turno["total"],
        "surprise": turno.get("surprise", []),
        "tipo_sorpresa": turno.get("tipo_sorpresa"),
    }


def ronda_publica(ronda):
    return {
        "ronda": ronda["ronda"],
        "turnos": [datos_turno_publicos(t) for t in ronda.get("turnos", [])],
    }


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
                raw = data.get("personaje") or {}
                nombre = str(raw.get("nombre", "")).strip()
                if not nombre:
                    await ws.send_json({"type": "error", "message": "El nombre es obligatorio."})
                    continue

                try:
                    velocidad = int(raw.get("velocidad", 0))
                    estilo = int(raw.get("estilo", 0) or 0)
                    ataque = int(raw.get("ataque", 0) or 0)
                    ta = int(raw.get("ta", 0) or 0)
                    parada = int(raw.get("parada", 0) or 0)
                    esquiva = int(raw.get("esquiva", 0) or 0)
                    dano = float(raw.get("dano", 0) or 0)
                    vida = float(raw.get("vida", 0) or 0)
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "message": "Los valores numéricos no son válidos."})
                    continue

                bando = str(raw.get("bando", "")).strip().lower()
                if bando not in {"aliado", "enemigo", ""}:
                    await ws.send_json({"type": "error", "message": "El bando no es válido."})
                    continue

                personaje = {
                    "id": next_personaje_id,
                    "nombre": nombre[:100],
                    "velocidad": velocidad,
                    "estilo": estilo,
                    "bando": bando,
                    "ataque": ataque,
                    "ta": ta,
                    "parada": parada,
                    "esquiva": esquiva,
                    "dano": dano,
                    "vida": vida,
                }
                next_personaje_id += 1
                personajes.append(personaje)

                if rondas:
                    for ronda in rondas[ronda_actual:]:
                        ronda["turnos"].append(crear_turno_personaje(personaje))
                        recalcular_sorpresas(ronda["turnos"], ronda["ronda"])

                await broadcast({"type": "add", "personaje": datos_personaje_publicos(personaje)})
                guardar_estado()
                if rondas:
                    await enviar_ronda_actual()

            elif message_type == "roll":
                rondas = generar_iniciativa()
                ronda_actual = 0
                turno_actual = 0
                guardar_estado()
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
                guardar_estado()
                await enviar_ronda_actual()

            elif message_type == "get_secret":
                try:
                    personaje_id = int(data.get("id"))
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "message": "ID de personaje no válido."})
                    continue
                personaje = buscar_personaje(personaje_id)
                if not personaje:
                    await ws.send_json({"type": "error", "message": "Personaje no encontrado."})
                    continue
                await ws.send_json({"type": "secret", "personaje": personaje})

            elif message_type == "update_secret":
                try:
                    personaje_id = int(data.get("id"))
                    personaje = buscar_personaje(personaje_id)
                    if not personaje:
                        raise ValueError
                    personaje["ataque"] = int(data.get("ataque", 0) or 0)
                    personaje["ta"] = int(data.get("ta", 0) or 0)
                    personaje["parada"] = int(data.get("parada", 0) or 0)
                    personaje["esquiva"] = int(data.get("esquiva", 0) or 0)
                    personaje["dano"] = float(data.get("dano", 0) or 0)
                    personaje["vida"] = float(data.get("vida", 0) or 0)
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "message": "Datos secretos no válidos."})
                    continue
                guardar_estado()
                await ws.send_json({"type": "secret", "personaje": personaje})
                await broadcast({"type": "secret_updated", "personaje": datos_personaje_publicos(personaje)})

            elif message_type == "attack":
                resultado = resolver_ataque(data)
                if resultado.get("error"):
                    await ws.send_json({"type": "error", "message": resultado["error"]})
                else:
                    await broadcast({"type": "attack_result", "data": resultado})
                    guardar_estado()

            elif message_type == "counterattack":
                resultado = resolver_ataque(data, contraataque=True)
                if resultado.get("error"):
                    await ws.send_json({"type": "error", "message": resultado["error"]})
                else:
                    await broadcast({"type": "attack_result", "data": resultado})
                    guardar_estado()

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
        numero = int(data.get("numero"))
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

    defensa = objetivo["esquiva"] if data.get("defensa") == "esquiva" else objetivo["parada"]
    ataque_base = atacante["ataque"]
    porcentaje = ataque_base + numero - defensa
    sorpresa = tiene_sorpresa(atacante_id, objetivo_id)

    resultado = {
        "atacante_id": atacante_id,
        "objetivo_id": objetivo_id,
        "atacante": atacante["nombre"],
        "objetivo": objetivo["nombre"],
        "numero": numero,
        "ataque_base": ataque_base,
        "defensa": defensa,
        "tipo_defensa": data.get("defensa", "parada"),
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

    porcentaje_post_ta = max(0, porcentaje - objetivo["ta"] * 10)
    dano = atacante.get("dano", 0)
    dano_total = dano * porcentaje_post_ta / 100

    resultado.update({
        "estado": "golpe",
        "ta": objetivo["ta"],
        "porcentaje_post_ta": porcentaje_post_ta,
        "dano_base": atacante.get("dano", 0),
        "dano_total": dano_total,
        "vida_objetivo": objetivo["vida"],
        "mensaje": f"Golpe: {porcentaje_post_ta}% de {atacante.get('dano', 0)} = {dano_total:g} daño.",
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
        "velocidad": personaje["velocidad"],
        "estilo": personaje["estilo"],
        "bando": personaje.get("bando", ""),
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


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

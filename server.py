from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import random
import socket

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

clients = []
personajes = []
next_personaje_id = 1

rondas = []
ronda_actual = 0


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


def mostrar_direcciones():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
    except:
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
    mostrar_direcciones()


@app.get("/")
async def get():
    with open("templates/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    global rondas
    global ronda_actual
    global next_personaje_id

    await ws.accept()
    clients.append(ws)

    try:
        while True:

            data = await ws.receive_json()

            if data["type"] == "add":

                raw = data["personaje"]

                personaje = {
                    "id": next_personaje_id,
                    "nombre": str(raw.get("nombre", "")),
                    "velocidad": int(raw.get("velocidad", 0) or 0),
                    "estilo": int(raw.get("estilo", 0) or 0),
                    "bando": str(raw.get("bando", "")).strip().lower()
                }
                next_personaje_id += 1

                personajes.append(personaje)

                if rondas:
                    for ronda in rondas[ronda_actual:]:
                        ronda["turnos"].append(crear_turno_personaje(personaje))
                        recalcular_sorpresas(ronda["turnos"], ronda["ronda"])

                await broadcast({
                    "type": "add",
                    "personaje": personaje
                })

                if rondas:
                    await enviar_ronda_actual()

            elif data["type"] == "roll":

                rondas = generar_iniciativa()
                ronda_actual = 0
                await enviar_ronda_actual()

            elif data["type"] == "delete":

                personaje_id = int(data.get("id", 0) or 0)
                personajes[:] = [p for p in personajes if p["id"] != personaje_id]

                for ronda in rondas:
                    ronda["turnos"] = [
                        turno for turno in ronda["turnos"]
                        if turno["id"] != personaje_id
                    ]
                    recalcular_sorpresas(ronda["turnos"], ronda["ronda"])

                await broadcast({
                    "type": "delete",
                    "id": personaje_id
                })

                await enviar_ronda_actual()

            elif data["type"] == "next":

                if ronda_actual < len(rondas) - 1:
                    ronda_actual += 1

                await enviar_ronda_actual()

            elif data["type"] == "clear":

                personajes.clear()
                rondas = []
                ronda_actual = 0

                await broadcast({"type": "clear"})

    except Exception as e:
        print("ERROR:", e)

    finally:
        if ws in clients:
            clients.remove(ws)


async def enviar_ronda_actual():

    if not rondas:
        return

    ronda = rondas[ronda_actual]

    await broadcast({
        "type": "ronda",
        "data": ronda
    })


def recalcular_sorpresas(turnos, numero_ronda):
    for turno in turnos:
        turno["surprise"] = []
        turno["tipo_sorpresa"] = None

    turnos.sort(key=lambda x: x["total"], reverse=True)

    for t in turnos:
        if numero_ronda == 1:
            umbral = obtener_umbral_sorpresa(t["estilo"])
        else:
            umbral = 150

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

        while roll >= umbral_abierta:
            umbral_abierta = min(umbral_abierta + 1, 100)
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
        "tipo_sorpresa": None
    }


# ---------------------------
# TABLAS DE SISTEMA
# ---------------------------

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
    else:
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
    else:
        return None


# ---------------------------
# GENERADOR
# ---------------------------

def generar_iniciativa():

    if not personajes:
        return []

    todas_rondas = []

    for ronda in range(1, 26):

        turnos = []

        for p in personajes:
            turnos.append(crear_turno_personaje(p))

        recalcular_sorpresas(turnos, ronda)

        todas_rondas.append({
            "ronda": ronda,
            "turnos": turnos
        })

    return todas_rondas

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import random
import socket

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

clients = []
personajes = []

rondas = []
ronda_actual = 0


def mostrar_direcciones():
    hostname = socket.gethostname()
    ip_local = socket.gethostbyname(hostname)

    print("\n==============================")
    print("Servidor iniciado")
    print("Accede desde este PC:")
    print("http://localhost:8000")
    print("")
    print("Accede desde tu móvil:")
    print(f"http://{ip_local}:8000")
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

    await ws.accept()
    clients.append(ws)

    print("[CLIENT CONNECTED]")

    try:
        while True:

            data = await ws.receive_json()

            # -------------------
            # AÑADIR PERSONAJE
            # -------------------
            if data["type"] == "add":

                p = data["personaje"]
                personajes.append(p)

                print(f"[ADD] {p['nombre']} añadido con velocidad {p['velocidad']}")

                for client in clients:
                    await client.send_json({
                        "type": "add",
                        "personaje": p
                    })

            # -------------------
            # GENERAR INICIATIVA
            # -------------------
            elif data["type"] == "roll":

                rondas = generar_iniciativa()
                ronda_actual = 0

                await enviar_ronda_actual()

            # -------------------
            # SIGUIENTE RONDA
            # -------------------
            elif data["type"] == "next":

                if ronda_actual < len(rondas) - 1:
                    ronda_actual += 1

                await enviar_ronda_actual()

            # -------------------
            # LIMPIAR SESION
            # -------------------
            elif data["type"] == "clear":

                personajes.clear()
                rondas = []
                ronda_actual = 0

                print("[SESSION CLEARED]")

                for client in clients:
                    await client.send_json({
                        "type": "clear"
                    })

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        clients.remove(ws)
        print("[CLIENT DISCONNECTED]")


async def enviar_ronda_actual():

    if not rondas:
        return

    ronda = rondas[ronda_actual]

    for client in clients:
        await client.send_json({
            "type": "ronda",
            "data": ronda
        })


def generar_iniciativa():

    if not personajes:
        return []

    todas_rondas = []

    for ronda in range(1, 11):

        turnos = []

        for p in personajes:

            nombre = p["nombre"]
            velocidad = p["velocidad"]

            roll = random.randint(1, 100)
            tirada = 160 if roll >= 90 else roll
            total = velocidad + tirada

            turnos.append({
                "nombre": nombre,
                "velocidad": velocidad,
                "roll": roll,
                "tirada": tirada,
                "total": total,
                "surprise": []
            })

        turnos.sort(key=lambda x: x["total"], reverse=True)

        for t in turnos:
            for other in turnos:
                if t["nombre"] != other["nombre"] and t["total"] > other["total"] + 150:
                    t["surprise"].append(other["nombre"])

        todas_rondas.append({
            "ronda": ronda,
            "turnos": turnos
        })

    return todas_rondas
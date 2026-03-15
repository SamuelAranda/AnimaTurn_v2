from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import random
import socket

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

clients = []
personajes = []


@app.get("/")
async def get():
    with open("templates/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.on_event("startup")
async def startup_event():
    mostrar_direcciones()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()
    clients.append(ws)

    print("[CLIENT CONNECTED]")

    try:
        while True:

            data = await ws.receive_json()

            # ----------------------------
            # AÑADIR PERSONAJE
            # ----------------------------
            if data["type"] == "add":

                p = data["personaje"]
                personajes.append(p)

                print(f"[ADD] {p['nombre']} añadido con velocidad {p['velocidad']}")
                
                # avisar a todos los clientes
                for client in clients:
                    await client.send_json({
                        "type": "add",
                        "personaje": p
                })

            # ----------------------------
            # GENERAR INICIATIVA
            # ----------------------------
            elif data["type"] == "roll":

                resultado = generar_iniciativa()

                print("\n=== INICIATIVA GENERADA ===")

                for r in resultado:

                    print(f"\n--- RONDA {r['ronda']} ---")

                    for t in r["turnos"]:

                        if t["roll"] >= 90:
                            line = f"{t['nombre']}: Vel {t['velocidad']} + d100({t['roll']}) -> 160 = {t['total']}"
                        else:
                            line = f"{t['nombre']}: Vel {t['velocidad']} + d100({t['roll']}) = {t['total']}"

                        if t["surprise"]:
                            line += f" (S - {', '.join(t['surprise'])})"

                        print(line)

                print("\n===========================\n")

                # enviar resultado a todos los clientes
                for client in clients:
                    await client.send_json({
                        "type": "resultado",
                        "data": resultado
                    })

    except Exception as e:

        print(f"[ERROR] {e}")

    finally:

        clients.remove(ws)
        print("[CLIENT DISCONNECTED]")


def mostrar_direcciones():

    hostname = socket.gethostname()
    ip_local = socket.gethostbyname(hostname)

    print("\n==============================")
    print("Servidor iniciado")
    print("")
    print("Accede desde este PC:")
    print("http://localhost:8000")
    print("")
    print("Accede desde otros dispositivos en tu red:")
    print(f"http://{ip_local}:8000")
    print("==============================\n")

# ---------------------------------------------------
# LOGICA DE INICIATIVA
# ---------------------------------------------------

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

        # calcular sorpresa
        for t in turnos:
            for other in turnos:
                if t["nombre"] != other["nombre"] and t["total"] > other["total"] + 150:
                    t["surprise"].append(other["nombre"])

        todas_rondas.append({
            "ronda": ronda,
            "turnos": turnos
        })

    return todas_rondas
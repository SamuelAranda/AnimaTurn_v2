let ws = new WebSocket("ws://" + location.host + "/ws")

ws.onopen = () => {
    console.log("WebSocket conectado")
}

ws.onmessage = (event) => {

    let msg = JSON.parse(event.data)

    console.log(msg)

    // -----------------------------
    // CUANDO SE AÑADE PERSONAJE
    // -----------------------------
    if (msg.type === "add") {

        let p = msg.personaje

        let texto = `${p.nombre} añadido (Vel ${p.velocidad})\n`

        document.getElementById("resultado").textContent += texto
    }

    // -----------------------------
    // RESULTADO DE INICIATIVA
    // -----------------------------
    if (msg.type === "resultado") {

        let out = ""

        msg.data.forEach(ronda => {

            out += "\n--- RONDA " + ronda.ronda + " ---\n"

            ronda.turnos.forEach(p => {

                let line = ""

                if (p.roll >= 90)
                    line = `${p.nombre}: Vel ${p.velocidad} + d100(${p.roll}) -> 160 = ${p.total}`
                else
                    line = `${p.nombre}: Vel ${p.velocidad} + d100(${p.roll}) = ${p.total}`

                if (Array.isArray(p.surprise) && p.surprise.length > 0)
                    line += ` (S - ${p.surprise.join(", ")})`

                out += line + "\n"

            })

        })

        document.getElementById("resultado").textContent = out
    }
}

function add() {

    let nombre = document.getElementById("nombre").value
    let velocidad = parseInt(document.getElementById("velocidad").value)

    ws.send(JSON.stringify({
        type: "add",
        personaje: {
            nombre: nombre,
            velocidad: velocidad
        }
    }))
}

function roll() {

    ws.send(JSON.stringify({
        type: "roll"
    }))
}
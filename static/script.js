let ws = new WebSocket("ws://" + location.host + "/ws")

ws.onopen = () => {
    console.log("WebSocket conectado")
}

ws.onmessage = (event) => {

    let msg = JSON.parse(event.data)

    if (msg.type === "add") {

        let p = msg.personaje

        let box = `
        <div class="info-box">
            <strong>${p.nombre}</strong> añadido (Vel ${p.velocidad})
        </div>
        `

        let resultado = document.getElementById("resultado")

        resultado.innerHTML += box

        scrollResultado()
    }

    if (msg.type === "ronda") {

        mostrarRonda(msg.data)
    }

    if (msg.type === "clear") {

        document.getElementById("resultado").innerHTML = ""
    }
}


function mostrarRonda(ronda) {

    let html = `<h2>Ronda ${ronda.ronda}</h2>`

    ronda.turnos.forEach(p => {

        let sorpresa = ""

        if (Array.isArray(p.surprise) && p.surprise.length > 0) {
            sorpresa = `<em>Sorpresa sobre ${p.surprise.join(", ")}</em>`
        }

        let tirada = ""

        if (p.roll >= 90)
            tirada = `Vel ${p.velocidad} + d100(${p.roll}) → 160 = ${p.total}`
        else
            tirada = `Vel ${p.velocidad} + d100(${p.roll}) = ${p.total}`

        html += `
        <div class="turn-card">
            <div class="turn-name">${p.nombre}</div>
            <div class="turn-roll">${tirada}</div>
            <div class="turn-surprise">${sorpresa}</div>
        </div>
        `
    })

    let resultado = document.getElementById("resultado")

    resultado.innerHTML = html

    scrollResultado()
}


function scrollResultado() {

    let resultado = document.getElementById("resultado")

    resultado.scrollTop = resultado.scrollHeight

    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: "smooth"
    })
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

    document.getElementById("nombre").value = ""
    document.getElementById("velocidad").value = ""
}


function roll() {

    ws.send(JSON.stringify({
        type: "roll"
    }))
}


function nextRound() {

    ws.send(JSON.stringify({
        type: "next"
    }))
}


function clearSession() {

    ws.send(JSON.stringify({
        type: "clear"
    }))
}
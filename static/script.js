let ws = new WebSocket("ws://" + location.host + "/ws")

ws.onmessage = (event) => {

    let msg = JSON.parse(event.data)

    if (msg.type === "add") {

        let p = msg.personaje

        document.getElementById("resultado").innerHTML += `
        <div class="info-box">
            <strong class="${getBandoClass(p.bando)}">${p.nombre}</strong> añadido 
            (Vel ${p.velocidad} | Est ${p.estilo})
        </div>
        `

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

    let titulo = `Ronda ${ronda.ronda}`

    if (ronda.ronda === 1) {
        titulo += " (Estilo activo)"
    } else {
        titulo += " (Sin estilo)"
    }

    let html = `<h2>${titulo}</h2>`

    ronda.turnos.forEach(p => {

        let sorpresa = ""

        if (p.surprise.length > 0) {

            if (p.tipo_sorpresa) {
                sorpresa = `<em>Sorpresa (${p.tipo_sorpresa}) sobre ${p.surprise.join(", ")}</em>`
            } else {
                sorpresa = `<em>Sorpresa sobre ${p.surprise.join(", ")}</em>`
            }
        }

        let tirada = p.roll >= 90
            ? `Vel ${p.velocidad} + d100(${p.roll}) → 160 = ${p.total}`
            : `Vel ${p.velocidad} + d100(${p.roll}) = ${p.total}`

        html += `
        <div class="turn-card">
            <div class="turn-name"><strong class="${getBandoClass(p.bando)}">${p.nombre}</strong></div>
            <div class="turn-roll">${tirada}</div>
            <div class="turn-surprise">${sorpresa}</div>
        </div>
        `
    })

    document.getElementById("resultado").innerHTML = html
    scrollResultado()
}


function scrollResultado() {
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: "smooth"
    })
}


function getBandoSeleccionado() {
    const seleccionado = document.querySelector('input[name="bando"]:checked')
    return seleccionado ? seleccionado.value : ""
}


function getBandoClass(bando) {
    if (bando === "aliado") return "nombre-aliado"
    if (bando === "enemigo") return "nombre-enemigo"
    return "nombre-neutral"
}


function add() {

    let nombre = document.getElementById("nombre").value
    let velocidad = parseInt(document.getElementById("velocidad").value)
    let estilo = Number(document.getElementById("estilo").value)
    let bando = getBandoSeleccionado()

    if (isNaN(estilo)) estilo = 0

    ws.send(JSON.stringify({
        type: "add",
        personaje: { nombre, velocidad, estilo, bando }
    }))

    document.getElementById("nombre").value = ""
    document.getElementById("velocidad").value = ""
    document.getElementById("estilo").value = ""
    document.querySelectorAll('input[name="bando"]').forEach(input => {
        input.checked = false
    })
}


function roll() {
    ws.send(JSON.stringify({ type: "roll" }))
}

function nextRound() {
    ws.send(JSON.stringify({ type: "next" }))
}

function clearSession() {
    ws.send(JSON.stringify({ type: "clear" }))
}

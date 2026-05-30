let ws = new WebSocket("ws://" + location.host + "/ws")

document.addEventListener("DOMContentLoaded", () => {
    renderEmptyState()
    actualizarEstadoRonda("Pendiente de generar")
})

ws.onmessage = (event) => {

    let msg = JSON.parse(event.data)

    if (msg.type === "init") {
        hydrateState(msg)
    }

    if (msg.type === "add") {
        renderPersonaje(msg.personaje)
    }

    if (msg.type === "ronda") {
        setSesionActiva(true)
        mostrarRonda(msg.data)
    }

    if (msg.type === "delete") {
        removePersonaje(msg.id)
    }

    if (msg.type === "clear") {
        document.getElementById("personajes").innerHTML = ""
        document.getElementById("resultado").innerHTML = ""
        setSesionActiva(false)
    }
}


function mostrarRonda(ronda) {

    let titulo = `Ronda ${ronda.ronda}`

    if (ronda.ronda === 1) {
        titulo += " (Estilo activo)"
    } else {
        titulo += " (Sin estilo)"
    }

    actualizarEstadoRonda(titulo)

    let html = ""

    ronda.turnos.forEach(p => {

        let sorpresa = ""

        if (p.surprise.length > 0) {

            if (p.tipo_sorpresa) {
                sorpresa = `
                <div class="surprise-banner">
                    <span class="surprise-tag">${p.tipo_sorpresa}</span>
                    <span>Sorpresa sobre ${p.surprise.join(", ")}</span>
                </div>
                `
            } else {
                sorpresa = `
                <div class="surprise-banner">
                    <span>Sorpresa sobre ${p.surprise.join(", ")}</span>
                </div>
                `
            }
        }

        let tirada = formatTirada(p)
        let tiradaChip = p.tirada >= 0 ? `+${p.tirada}` : `${p.tirada}`
        let detalleTirada = Array.isArray(p.rolls) ? p.rolls.join(" + ") : p.roll

        html += `
        <div class="turn-card">
            <div class="turn-header">
                <div class="turn-name"><strong class="${getBandoClass(p.bando)}">${p.nombre}</strong></div>
                <button type="button" class="delete-button" onclick="deletePersonaje(${p.id})">Eliminar</button>
            </div>
            <div class="turn-meta">
                <div class="stat-chip">Vel <strong>${p.velocidad}</strong></div>
                <div class="stat-chip">Total <strong>${p.total}</strong></div>
                <div class="stat-chip">Tirada <strong>${tiradaChip}</strong></div>
                <div class="stat-chip">Dados <strong>${detalleTirada}</strong></div>
            </div>
            <div class="turn-roll">${tirada}</div>
            <div class="turn-surprise">${sorpresa}</div>
        </div>
        `
    })

    if (!html) {
        html = emptyStateMarkup("No quedan personajes en esta ronda.")
    }

    document.getElementById("resultado").innerHTML = html
    scrollResultado()
}


function hydrateState(data) {
    const personajes = Array.isArray(data.personajes) ? data.personajes : []

    document.getElementById("personajes").innerHTML = ""

    personajes.forEach(renderPersonaje)

    if (data.hay_sesion && data.ronda_actual) {
        setSesionActiva(true)
        mostrarRonda(data.ronda_actual)
        return
    }

    document.getElementById("resultado").innerHTML = ""
    setSesionActiva(false)
}


function scrollResultado() {
    window.scrollTo({
        top: document.body.scrollHeight,
        behavior: "smooth"
    })
}


function setSesionActiva(activa) {
    const seccion = document.getElementById("personajes-seccion")
    seccion.style.display = activa ? "none" : "block"

    if (!activa && !document.getElementById("resultado").innerHTML.trim()) {
        renderEmptyState()
        actualizarEstadoRonda("Pendiente de generar")
    }
}


function renderPersonaje(p) {
    const contenedor = document.getElementById("personajes")

    contenedor.innerHTML += `
    <div class="info-box personaje-card" id="personaje-${p.id}">
        <div class="personaje-header">
            <strong class="${getBandoClass(p.bando)}">${p.nombre}</strong>
            <button type="button" class="delete-button" onclick="deletePersonaje(${p.id})">Eliminar</button>
        </div>
        <div class="personaje-meta">
            <div class="stat-chip">Vel <strong>${p.velocidad}</strong></div>
            <div class="stat-chip">Estilo <strong>${p.estilo}</strong></div>
        </div>
    </div>
    `
}


function removePersonaje(id) {
    const card = document.getElementById(`personaje-${id}`)
    if (card) card.remove()
}


function actualizarEstadoRonda(texto) {
    document.getElementById("estado-ronda").textContent = texto
}


function emptyStateMarkup(texto) {
    return `<div class="empty-state">${texto}</div>`
}


function renderEmptyState() {
    document.getElementById("resultado").innerHTML = emptyStateMarkup(
        "Anade personajes y genera la iniciativa para ver el orden de combate."
    )
}


function formatTirada(p) {
    if (p.roll === 1) {
        return `Vel ${p.velocidad} + d100(1) = -125 -> ${p.total}`
    }

    if (p.roll === 2) {
        return `Vel ${p.velocidad} + d100(2) = -100 -> ${p.total}`
    }

    if (p.roll === 3) {
        return `Vel ${p.velocidad} + d100(3) = -75 -> ${p.total}`
    }

    if (Array.isArray(p.rolls) && p.rolls.length > 1) {
        return `Vel ${p.velocidad} + abierta [${p.rolls.join(" + ")}] = ${p.tirada} -> ${p.total}`
    }

    return `Vel ${p.velocidad} + d100(${p.roll}) = ${p.total}`
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

    if (!document.getElementById("resultado").innerHTML.trim()) {
        setSesionActiva(false)
    }
}


function roll() {
    ws.send(JSON.stringify({ type: "roll" }))
}

function deletePersonaje(id) {
    ws.send(JSON.stringify({ type: "delete", id }))
}

function nextRound() {
    ws.send(JSON.stringify({ type: "next" }))
}

function clearSession() {
    ws.send(JSON.stringify({ type: "clear" }))
}

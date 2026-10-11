let ws = null
let currentRonda = null
let currentTurnIndex = 0
let currentAttack = null
let pendingCounterattack = null
let reconnectTimer = null

const $ = (id) => document.getElementById(id)

window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tab-button").forEach(button => {
        button.addEventListener("click", () => openTab(button.dataset.tab))
    })
    renderEmptyState()
    actualizarEstadoRonda("Pendiente de generar")
    connectWebSocket()
})

function connectWebSocket() {
    ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws")
    ws.onopen = () => {
        setConnectionState(true)
    }
    ws.onclose = () => {
        setConnectionState(false)
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null
                connectWebSocket()
            }, 1500)
        }
    }
    ws.onerror = () => setConnectionState(false)
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === "secret") {
            populateSecretModal(msg.personaje)
            return
        }
        if (msg.type === "init") hydrateState(msg)
        if (msg.type === "add") renderPersonaje(msg.personaje)
        if (msg.type === "ronda") {
            setSesionActiva(true)
            currentTurnIndex = Number(msg.indice_turno || 0)
            mostrarRonda(msg.data)
        }
        if (msg.type === "delete") removePersonaje(msg.id)
        if (msg.type === "clear") {
            $("personajes").innerHTML = ""
            $("resultado").innerHTML = ""
            currentRonda = null
            currentTurnIndex = 0
            setSesionActiva(false)
            actualizarEstadoRonda("Pendiente de generar")
            $("turno-activo").textContent = "Genera la iniciativa para comenzar."
        }
        if (msg.type === "secret_updated") updateCharacterCard(msg.personaje)
        if (msg.type === "attack_result") mostrarResultadoAtaque(msg.data)
        if (msg.type === "error") showToast(msg.message, true)
    }
}

function setConnectionState(connected) {
    document.body.dataset.connected = connected ? "true" : "false"
}

function send(message) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast("Sin conexión con el servidor.", true)
        return false
    }
    ws.send(JSON.stringify(message))
    return true
}

function openTab(tab) {
    document.querySelectorAll(".tab-button").forEach(button => button.classList.toggle("active", button.dataset.tab === tab))
    document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.toggle("active", panel.id === `tab-${tab}`))
}

function openCombatTab() { openTab("combate") }

function mostrarRonda(ronda) {
    currentRonda = ronda
    let titulo = `Ronda ${ronda.ronda}`
    titulo += ronda.ronda === 1 ? " (Estilo activo)" : " (Sin estilo)"
    actualizarEstadoRonda(titulo)

    const turnos = Array.isArray(ronda.turnos) ? ronda.turnos : []
    if (!turnos.length) {
        $("resultado").innerHTML = emptyStateMarkup("No quedan personajes en esta ronda.")
        $("turno-activo").textContent = "No hay personajes que puedan actuar."
        return
    }

    const activo = turnos[currentTurnIndex]
    $("turno-activo").innerHTML = activo
        ? `Turno <strong>${currentTurnIndex + 1}</strong> · Actúa <strong class="${getBandoClass(activo.bando)}">${escapeHtml(activo.nombre)}</strong>`
        : "Turno no disponible."

    let html = ""
    turnos.forEach((p, index) => {
        const sorpresa = renderSorpresa(p)
        const activoClass = index === currentTurnIndex ? " active-turn" : ""
        const tirada = formatTirada(p)
        const tiradaChip = p.tirada >= 0 ? `+${p.tirada}` : `${p.tirada}`
        const detalleTirada = Array.isArray(p.rolls) ? p.rolls.join(" + ") : p.roll
        html += `
        <div class="turn-card${activoClass}">
            <div class="turn-header">
                <div class="turn-title-row">
                    <span class="turn-number">${index + 1}</span>
                    <div class="turn-name"><strong class="${getBandoClass(p.bando)}">${escapeHtml(p.nombre)}</strong></div>
                </div>
                <div class="turn-actions">
                    ${index === currentTurnIndex ? '<span class="active-label">Activo</span>' : `<button type="button" class="turn-select-button" onclick="setActiveCharacter(${p.id})">Hacer activo</button>`}
                    <button type="button" class="action-button" onclick="openAttackModal(${p.id})">Acción</button>
                </div>
            </div>
            <div class="turn-meta">
                <div class="stat-chip">Vel <strong>${p.velocidad}</strong></div>
                <div class="stat-chip">Total <strong>${p.total}</strong></div>
                <div class="stat-chip">Tirada <strong>${tiradaChip}</strong></div>
                <div class="stat-chip">Dados <strong>${detalleTirada}</strong></div>
            </div>
            <div class="turn-roll">${tirada}</div>
            <div class="turn-surprise">${sorpresa}</div>
        </div>`
    })
    $("resultado").innerHTML = html
    openCombatTab()
}

function renderSorpresa(p) {
    if (!Array.isArray(p.surprise) || p.surprise.length === 0) return ""
    const tag = p.tipo_sorpresa ? `<span class="surprise-tag">${escapeHtml(p.tipo_sorpresa)}</span>` : ""
    return `<div class="surprise-banner">${tag}<span>Sorpresa sobre ${p.surprise.map(escapeHtml).join(", ")}</span></div>`
}

function hydrateState(data) {
    $("personajes").innerHTML = ""
    const personajes = Array.isArray(data.personajes) ? data.personajes : []
    personajes.forEach(renderPersonaje)
    currentTurnIndex = Number(data.indice_turno || 0)
    if (data.hay_sesion && data.ronda_actual) {
        setSesionActiva(true)
        mostrarRonda(data.ronda_actual)
    } else {
        $("resultado").innerHTML = ""
        setSesionActiva(false)
    }
}

function setSesionActiva(activa) {
    const seccion = $("personajes")?.parentElement
    if (seccion) seccion.style.display = "block"
    if (!activa && !$("resultado").innerHTML.trim()) renderEmptyState()
}

function renderPersonaje(p) {
    const contenedor = $("personajes")
    const existing = $(`personaje-${p.id}`)
    if (existing) existing.remove()
    contenedor.insertAdjacentHTML("beforeend", `
    <div class="info-box personaje-card" id="personaje-${p.id}" onclick="openSecretModal(${p.id})" tabindex="0" role="button" aria-label="Editar datos secretos de ${escapeHtml(p.nombre)}">
        <div class="personaje-header">
            <strong class="${getBandoClass(p.bando)}">${escapeHtml(p.nombre)}</strong>
            <button type="button" class="delete-button" onclick="event.stopPropagation(); deletePersonaje(${p.id})">Eliminar</button>
        </div>
        <div class="personaje-meta">
            <div class="stat-chip">Vel <strong>${p.velocidad}</strong></div>
            <div class="stat-chip">Estilo <strong>${p.estilo}</strong></div>
        </div>
    </div>`)
}

function updateCharacterCard(p) {
    renderPersonaje(p)
}

function removePersonaje(id) {
    const card = $(`personaje-${id}`)
    if (card) card.remove()
}

function actualizarEstadoRonda(texto) { $("estado-ronda").textContent = texto }
function emptyStateMarkup(texto) { return `<div class="empty-state">${escapeHtml(texto)}</div>` }
function renderEmptyState() { $("resultado").innerHTML = emptyStateMarkup("Añade personajes y genera la iniciativa para ver el orden de combate.") }

function formatTirada(p) {
    if (p.roll === 1) return `Vel ${p.velocidad} + d100(1) = -125 -> ${p.total}`
    if (p.roll === 2) return `Vel ${p.velocidad} + d100(2) = -100 -> ${p.total}`
    if (p.roll === 3) return `Vel ${p.velocidad} + d100(3) = -75 -> ${p.total}`
    if (Array.isArray(p.rolls) && p.rolls.length > 1) return `Vel ${p.velocidad} + abierta [${p.rolls.join(" + ")}] = ${p.tirada} -> ${p.total}`
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
    const nombre = $("nombre").value.trim()
    const velocidad = parseInt($("velocidad").value, 10)
    let estilo = Number($("estilo").value)
    if (Number.isNaN(estilo)) estilo = 0
    if (!nombre || Number.isNaN(velocidad)) {
        showToast("Introduce nombre y velocidad.", true)
        return
    }
    if (!send({ type: "add", personaje: { nombre, velocidad, estilo, bando: getBandoSeleccionado() } })) return
    $("nombre").value = ""
    $("velocidad").value = ""
    $("estilo").value = ""
    document.querySelectorAll('input[name="bando"]').forEach(input => input.checked = false)
}

function roll() { send({ type: "roll" }) }
function deletePersonaje(id) { send({ type: "delete", id }) }
function nextRound() { send({ type: "next" }) }
function setActiveCharacter(id) { send({ type: "set_active", id }) }
function clearSession() { if (confirm("¿Limpiar toda la sesión?")) send({ type: "clear" }) }

function openSecretModal(id) {
    send({ type: "get_secret", id })
}

function populateSecretModal(p) {
    $("secret-title").textContent = p.nombre
    $("secret-ataque").value = p.ataque ?? 0
    $("secret-ta").value = p.ta ?? 0
    $("secret-parada").value = p.parada ?? 0
    $("secret-esquiva").value = p.esquiva ?? 0
    $("secret-dano").value = p.dano ?? 0
    $("secret-vida").value = p.vida ?? 0
    $("secret-modal").dataset.personajeId = p.id
    showModal("secret-modal")
}

function saveSecretData() {
    const id = Number($("secret-modal").dataset.personajeId)
    send({
        type: "update_secret", id,
        ataque: Number($("secret-ataque").value || 0),
        ta: Number($("secret-ta").value || 0),
        parada: Number($("secret-parada").value || 0),
        esquiva: Number($("secret-esquiva").value || 0),
        dano: Number($("secret-dano").value || 0),
        vida: Number($("secret-vida").value || 0),
    })
}

function openAttackModal(attackerId, counter = false) {
    const attacker = findTurn(attackerId)
    if (!attacker) {
        showToast("Ese personaje no está en la ronda actual.", true)
        return
    }
    const targets = currentRonda.turnos.filter(p => p.id !== attackerId)
    if (!targets.length) {
        showToast("No hay objetivos disponibles.", true)
        return
    }
    currentAttack = { attackerId, counter }
    $("attack-title").textContent = counter ? `Contraataque de ${attacker.nombre}` : `Atacar con ${attacker.nombre}`
    $("attack-target").innerHTML = targets.map(t => `<option value="${t.id}">${escapeHtml(t.nombre)}</option>`).join("")
    $("attack-defense").value = "parada"
    $("attack-number").value = ""
    $("surprise-warning").classList.add("hidden")
    updateSurpriseWarning()
    showModal("attack-modal")
}

function updateSurpriseWarning() {
    if (!currentAttack || !currentRonda) return
    const targetId = Number($("attack-target").value)
    const attacker = findTurn(currentAttack.attackerId)
    const target = findTurn(targetId)
    const warning = $("surprise-warning")
    if (!attacker || !target) return
    const attackerSurprises = attacker.surprise?.includes(target.nombre)
    const targetSurprises = target.surprise?.includes(attacker.nombre)
    if (attackerSurprises && targetSurprises) {
        warning.textContent = "⚠ Ambos tienen sorpresa sobre el otro."
    } else if (attackerSurprises) {
        warning.textContent = "⚠ Has conseguido SORPRESA sobre este objetivo."
    } else if (targetSurprises) {
        warning.textContent = "⚠ Este objetivo tiene SORPRESA sobre ti."
    } else {
        warning.classList.add("hidden")
        return
    }
    warning.classList.remove("hidden")
}

$("attack-target")?.addEventListener("change", updateSurpriseWarning)

function performAttack() {
    if (!currentAttack) return
    const numero = Number($("attack-number").value)
    if (!Number.isFinite(numero)) {
        showToast("Introduce un número para el ataque.", true)
        return
    }
    send({
        type: currentAttack.counter ? "counterattack" : "attack",
        attacker_id: currentAttack.attackerId,
        target_id: Number($("attack-target").value),
        numero,
        defensa: $("attack-defense").value,
    })
    closeAttackModal()
}

function mostrarResultadoAtaque(data) {
    pendingCounterattack = data.estado === "contraataque" ? data : null
    let html = `<div class="attack-summary"><p><strong>${escapeHtml(data.atacante)}</strong> → <strong>${escapeHtml(data.objetivo)}</strong></p>`
    if (data.sorpresa?.agresor_sorprende) html += `<div class="surprise-warning">⚠ Sorpresa conseguida sobre el objetivo.</div>`
    if (data.sorpresa?.objetivo_sorprende) html += `<div class="surprise-warning">⚠ El objetivo tiene sorpresa sobre el atacante.</div>`
    html += `<div class="result-message ${data.estado}">${escapeHtml(data.mensaje)}</div>`
    html += `<dl class="result-details"><div><dt>Ataque</dt><dd>${data.ataque_base} + ${data.numero}</dd></div><div><dt>Defensa</dt><dd>− ${data.defensa}</dd></div><div><dt>Porcentaje</dt><dd>${data.porcentaje}%</dd></div>`
    if (data.estado === "golpe") html += `<div><dt>TA</dt><dd>− ${data.ta * 10}%</dd></div><div><dt>Daño</dt><dd>${data.dano_total}</dd></div>`
    if (data.estado !== "golpe") html += `<div><dt>Fallo</dt><dd>${data.fallo}%</dd></div>`
    html += `</dl></div>`
    $("attack-result").innerHTML = html
    $("counterattack-area").classList.toggle("hidden", data.estado !== "contraataque")
    showModal("result-modal")
}

function openCounterattack() {
    if (!pendingCounterattack) return
    const attackerId = pendingCounterattack.objetivo_id
    const targetId = pendingCounterattack.atacante_id
    const previous = pendingCounterattack
    closeResultModal()
    openAttackModal(attackerId, true)
    setTimeout(() => {
        $("attack-target").value = String(targetId)
        $("attack-defense").value = "parada"
        updateSurpriseWarning()
        currentAttack.previous = previous
    }, 0)
}

function findTurn(id) { return currentRonda?.turnos?.find(p => p.id === Number(id)) }

function showModal(id) {
    const modal = $(id)
    modal.classList.remove("hidden")
    modal.setAttribute("aria-hidden", "false")
}
function closeSecretModal() { hideModal("secret-modal") }
function closeAttackModal() { hideModal("attack-modal"); currentAttack = null }
function closeResultModal() { hideModal("result-modal"); pendingCounterattack = null }
function hideModal(id) { $(id).classList.add("hidden"); $(id).setAttribute("aria-hidden", "true") }

function showToast(message, error = false) {
    let toast = $("toast")
    if (!toast) {
        toast = document.createElement("div")
        toast.id = "toast"
        toast.className = "toast"
        document.body.appendChild(toast)
    }
    toast.textContent = message
    toast.classList.toggle("error", error)
    toast.classList.add("visible")
    clearTimeout(showToast.timer)
    showToast.timer = setTimeout(() => toast.classList.remove("visible"), 3000)
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char]))
}

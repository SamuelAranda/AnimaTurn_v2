let ws = null
let currentRonda = null
let currentTurnIndex = 0
let currentAttack = null
let pendingCounterattack = null
let pendingCritical = null
let pendingFallen = null
let reconnectTimer = null
let personajes = []
let activeTab = "preparacion"
let characterModal = { mode: "add", id: null, tipo: "jugador" }

const $ = (id) => document.getElementById(id)
const TIPOS_JUGADOR = ["jugador", "aliado"]

window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".tab-button").forEach(button => {
        button.addEventListener("click", () => openTab(button.dataset.tab))
    })
    document.querySelectorAll('input[name="tipo"]').forEach(input => {
        input.addEventListener("change", updateCharModalVisibility)
    })
    $("attack-target")?.addEventListener("change", updateAttackForm)
    renderEmptyState()
    actualizarEstadoRonda("Pendiente de generar")
    connectWebSocket()
})

function connectWebSocket() {
    ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws")
    ws.onopen = () => setConnectionState(true)
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
        if (msg.type === "init") hydrateState(msg)
        if (msg.type === "personajes") applyPersonajes(msg.data)
        if (msg.type === "ronda") {
            setSesionActiva(true)
            currentTurnIndex = Number(msg.indice_turno || 0)
            mostrarRonda(msg.data)
        }
        if (msg.type === "delete") removeLocal(msg.id)
        if (msg.type === "clear") {
            personajes = []
            currentRonda = null
            currentTurnIndex = 0
            renderPersonajesList()
            renderTabs()
            $("resultado").innerHTML = ""
            setSesionActiva(false)
            actualizarEstadoRonda("Pendiente de generar")
            $("turno-activo").textContent = "Genera la iniciativa para comenzar."
            openTab("preparacion")
        }
        if (msg.type === "character") populateCharacterModal(msg.personaje)
        if (msg.type === "character_saved") closeCharacterModal()
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

/* ----------------------------- Pestañas ----------------------------- */

function openTab(tab) {
    activeTab = tab
    applyActiveTab()
}

function applyActiveTab() {
    document.querySelectorAll(".tab-button").forEach(button => {
        button.classList.toggle("active", button.dataset.tab === activeTab)
    })
    document.querySelectorAll(".tab-panel").forEach(panel => {
        panel.classList.toggle("active", panel.id === `tab-${activeTab}`)
    })
}

function ensureActiveTab() {
    if (activeTab.startsWith("pj-")) {
        const id = Number(activeTab.slice(3))
        if (!personajes.some(p => p.id === id)) activeTab = "combate"
    }
    applyActiveTab()
}

function openCombatTab() { openTab("combate") }

function renderTabs() {
    const jugadores = personajes.filter(p => TIPOS_JUGADOR.includes(p.tipo))
    $("tabs-jugadores").innerHTML = jugadores.map(p =>
        `<span class="tab-button tab-jugador ${getTipoClass(p.tipo)}" data-tab="pj-${p.id}" onclick="openTab('pj-${p.id}')">${escapeHtml(p.nombre)}</span>`
    ).join("")
    $("panels-jugadores").innerHTML = jugadores.map(p =>
        `<section id="tab-pj-${p.id}" class="tab-panel">${playerSheetMarkup(p)}</section>`
    ).join("")
    ensureActiveTab()
}

function playerSheetMarkup(p) {
    const activo = isActive(p.id)
    const vidaPct = p.vida_max > 0 ? Math.max(0, Math.min(100, (p.vida_actual / p.vida_max) * 100)) : 0
    return `<div class="battle-panel player-sheet ${getBorderClass(p.tipo)}${p.a_la_defensiva ? " defensiva" : ""}">
        <div class="panel-heading battle-heading">
            <div><p class="section-kicker">Ficha de personaje</p><h2 class="${getTipoClass(p.tipo)}">${escapeHtml(p.nombre)}</h2></div>
            <div class="tipo-badge ${getTipoClass(p.tipo)}">${getTipoLabel(p.tipo)}</div>
        </div>
        ${activo ? '<div class="es-tu-turno">Es tu turno · puedes lanzar una acción ofensiva</div>' : ''}
        <div class="vida-block">
            <div class="vida-label">Vida <strong>${fmt(p.vida_actual)}</strong> / ${fmt(p.vida_max)}</div>
            <div class="vida-bar"><span style="width:${vidaPct}%"></span></div>
        </div>
        ${tagsMarkup(p)}
        <div class="player-stats">
            ${chip("Velocidad", p.velocidad)}
            ${chip("Zeon", fmt(p.zeon))}
            ${chip("Ki", fmt(p.ki))}
            ${chip("Estilo", p.estilo)}
            ${chip("TA", p.ta)}
            ${chip("Daño", fmt(p.dano))}
        </div>
        <div class="action-row">
            <button class="ghost-button" onclick="openEditModal(${p.id})">Editar ficha</button>
            ${activo ? `<button class="action-button" onclick="openAttackModal(${p.id})">Acción ofensiva</button>` : ''}
        </div>
    </div>`
}

/* ----------------------------- Personajes ----------------------------- */

function applyPersonajes(data) {
    personajes = Array.isArray(data) ? data : []
    renderPersonajesList()
    renderTabs()
}

function renderPersonajesList() {
    $("personajes").innerHTML = ""
    personajes.forEach(renderPersonaje)
}

function renderPersonaje(p) {
    const contenedor = $("personajes")
    const existing = $(`personaje-${p.id}`)
    if (existing) existing.remove()
    contenedor.insertAdjacentHTML("beforeend", `
    <div class="info-box personaje-card ${getBorderClass(p.tipo)}${p.a_la_defensiva ? " defensiva" : ""}" id="personaje-${p.id}" onclick="openCharacter(${p.id})" tabindex="0" role="button" aria-label="Abrir ficha de ${escapeHtml(p.nombre)}">
        <div class="personaje-header">
            <strong class="${getTipoClass(p.tipo)}">${escapeHtml(p.nombre)}</strong>
            <button type="button" class="delete-button" onclick="event.stopPropagation(); deletePersonaje(${p.id})">Eliminar</button>
        </div>
        <div class="personaje-meta">
            <span class="stat-chip tipo-chip ${getTipoClass(p.tipo)}">${getTipoLabel(p.tipo)}</span>
            <span class="stat-chip">Vel <strong>${p.velocidad}</strong></span>
            <span class="stat-chip">Estilo <strong>${p.estilo}</strong></span>
        </div>
        ${tagsMarkup(p)}
    </div>`)
}

function openCharacter(id) {
    const p = personajes.find(x => x.id === Number(id))
    if (!p) return
    if (TIPOS_JUGADOR.includes(p.tipo)) openTab(`pj-${p.id}`)
    else openEditModal(p.id)
}

function removeLocal(id) {
    personajes = personajes.filter(p => p.id !== Number(id))
    renderPersonajesList()
    renderTabs()
}

function setSesionActiva(activa) {
    const seccion = $("personajes")?.parentElement
    if (seccion) seccion.style.display = "block"
    const nextButton = $("next-turn-button")
    if (nextButton) nextButton.disabled = !activa
    if (!activa && !$("resultado").innerHTML.trim()) renderEmptyState()
}

/* ----------------------------- Ronda / turnos ----------------------------- */

function hydrateState(data) {
    currentTurnIndex = Number(data.indice_turno || 0)
    currentRonda = data.ronda_actual || null
    applyPersonajes(data.personajes)
    if (data.hay_sesion && data.ronda_actual) {
        setSesionActiva(true)
        renderRonda(data.ronda_actual)
        openCombatTab()
    } else {
        $("resultado").innerHTML = ""
        setSesionActiva(false)
        renderEmptyState()
    }
}

function mostrarRonda(ronda) {
    currentRonda = ronda
    renderRonda(ronda)
    openCombatTab()
}

function renderRonda(ronda) {
    currentRonda = ronda
    let titulo = `Ronda ${ronda.ronda}`
    titulo += ronda.ronda === 1 ? " (Estilo activo)" : " (Sin estilo)"
    actualizarEstadoRonda(titulo)

    const turnos = Array.isArray(ronda.turnos) ? ronda.turnos : []
    const nextButton = $("next-turn-button")
    if (nextButton) nextButton.disabled = false
    if (!turnos.length) {
        $("resultado").innerHTML = emptyStateMarkup("No quedan personajes en esta ronda.")
        $("turno-activo").textContent = "No hay personajes que puedan actuar."
        if (nextButton) nextButton.disabled = true
        renderTabs()
        return
    }

    const activo = turnos[currentTurnIndex]
    $("turno-activo").innerHTML = activo
        ? `Turno <strong>${currentTurnIndex + 1}</strong> · Actúa <strong class="${getTipoClass(activo.tipo)}">${escapeHtml(activo.nombre)}</strong>`
        : "Turno no disponible."

    let html = ""
    turnos.forEach((p, index) => {
        html += turnCardMarkup(p, index)
    })
    $("resultado").innerHTML = html
    renderTabs()
}

function turnCardMarkup(p, index) {
    const activoClass = index === currentTurnIndex ? " active-turn" : ""
    const defensivaClass = p.a_la_defensiva ? " defensiva" : ""
    const tirada = formatTirada(p)
    const tiradaChip = p.tirada >= 0 ? `+${p.tirada}` : `${p.tirada}`
    const detalleTirada = Array.isArray(p.rolls) ? p.rolls.join(" + ") : p.roll
    const esActivo = index === currentTurnIndex
    return `
    <div class="turn-card ${getBorderClass(p.tipo)}${activoClass}${defensivaClass}">
        <div class="turn-header">
            <div class="turn-title-row">
                <span class="turn-number">${index + 1}</span>
                <div class="turn-name"><strong class="${getTipoClass(p.tipo)}">${escapeHtml(p.nombre)}</strong></div>
            </div>
            <div class="turn-actions">
                <span class="stat-chip tipo-chip ${getTipoClass(p.tipo)}">${getTipoLabel(p.tipo)}</span>
                ${esActivo ? '<span class="active-label">Activo</span>' : `<button type="button" class="turn-select-button" onclick="setActiveCharacter(${p.id})">Hacer activo</button>`}
                ${esActivo ? `<button type="button" class="action-button" onclick="openAttackModal(${p.id})">Acción</button>` : ''}
            </div>
        </div>
        <div class="turn-meta">
            <div class="stat-chip">Vel <strong>${p.velocidad}</strong></div>
            <div class="stat-chip">Total <strong>${p.total}</strong></div>
            <div class="stat-chip">Tirada <strong>${tiradaChip}</strong></div>
            <div class="stat-chip">Dados <strong>${detalleTirada}</strong></div>
        </div>
        <div class="turn-roll">${tirada}</div>
        ${tagsMarkup(p)}
        <div class="turn-surprise">${renderSorpresa(p)}</div>
    </div>`
}

function isActive(id) {
    if (!currentRonda || !currentRonda.turnos) return false
    const activo = currentRonda.turnos[currentTurnIndex]
    return !!activo && activo.id === Number(id)
}

function renderSorpresa(p) {
    if (!Array.isArray(p.surprise) || p.surprise.length === 0) return ""
    const tag = p.tipo_sorpresa ? `<span class="surprise-tag">${escapeHtml(p.tipo_sorpresa)}</span>` : ""
    return `<div class="surprise-banner">${tag}<span>Sorpresa sobre ${p.surprise.map(escapeHtml).join(", ")}</span></div>`
}

function tagsMarkup(p) {
    let tags = ""
    if (Array.isArray(p.criticos)) tags += p.criticos.map(c => `<span class="tag tag-critico">-${c}</span>`).join("")
    if (p.a_la_defensiva) tags += `<span class="tag tag-defensiva">A la Defensiva</span>`
    if (p.debil) tags += `<span class="tag tag-debil">Débil</span>`
    if (p.caido) tags += `<span class="tag tag-caido">Caído</span>`
    if (p.acumulacion) tags += `<span class="tag tag-acumulacion">Acumulación</span>`
    return tags ? `<div class="turn-tags">${tags}</div>` : ""
}

/* ----------------------------- Envíos simples ----------------------------- */

function roll() { send({ type: "roll" }) }
function deletePersonaje(id) { send({ type: "delete", id }) }
function nextRound() { send({ type: "next" }) }
function setActiveCharacter(id) { send({ type: "set_active", id }) }
function clearSession() { if (confirm("¿Limpiar toda la sesión?")) send({ type: "clear" }) }

/* ----------------------------- Modal de personaje ----------------------------- */

function openAddModal() {
    characterModal = { mode: "add", id: null, tipo: "jugador" }
    $("character-kicker").textContent = "Nuevo personaje"
    $("character-title").textContent = "Añadir personaje"
    $("tipo-selector").classList.remove("hidden")
    document.querySelectorAll('input[name="tipo"]').forEach(input => {
        input.disabled = false
        input.checked = input.value === "jugador"
    })
    ;["nombre", "velocidad", "vida-max", "zeon", "ki", "estilo", "ta", "dano", "ataque", "defensa", "vida-actual"].forEach(campo => {
        const el = $(`char-${campo}`)
        if (el) el.value = ""
    })
    $("char-zeon").value = "0"
    $("char-ki").value = "0"
    $("char-estilo").value = "0"
    $("char-dano").value = "0"
    $("char-acumulacion").checked = false
    updateCharModalVisibility()
    showModal("character-modal")
}

function openEditModal(id) {
    characterModal = { mode: "edit", id: Number(id), tipo: "jugador" }
    send({ type: "get_character", id })
}

function populateCharacterModal(p) {
    if (characterModal.mode !== "edit") return
    characterModal.id = p.id
    characterModal.tipo = p.tipo
    $("character-kicker").textContent = "Datos privados"
    $("character-title").textContent = p.nombre
    $("tipo-selector").classList.add("hidden")
    document.querySelectorAll('input[name="tipo"]').forEach(input => {
        input.disabled = true
        input.checked = input.value === p.tipo
    })
    $("char-nombre").value = p.nombre
    $("char-velocidad").value = p.velocidad
    $("char-vida-max").value = p.vida_max
    $("char-vida-actual").value = p.vida_actual
    $("char-zeon").value = p.zeon
    $("char-ki").value = p.ki
    $("char-estilo").value = p.estilo
    $("char-ta").value = p.ta
    $("char-dano").value = p.dano
    $("char-acumulacion").checked = !!p.acumulacion
    $("char-ataque").value = p.ataque ?? 0
    $("char-defensa").value = p.defensa ?? 0
    updateCharModalVisibility()
    showModal("character-modal")
}

function updateCharModalVisibility() {
    const tipo = characterModal.mode === "edit"
        ? characterModal.tipo
        : (document.querySelector('input[name="tipo"]:checked')?.value || "jugador")
    const esEnemigo = !TIPOS_JUGADOR.includes(tipo)
    $("char-enemigo-fields").classList.toggle("hidden", !esEnemigo)
    $("char-vida-actual-field").classList.toggle("hidden", characterModal.mode !== "edit")
    $("tipo-hint").textContent = esEnemigo
        ? "Enemigo/PNJ: usa su Ataque y Defensa guardados. Sus datos de combate no se muestran."
        : "Jugador/Aliado: ataca con el número limpio y defiende con su defensa limpia."
}

function saveCharacterModal() {
    const tipo = characterModal.mode === "edit"
        ? characterModal.tipo
        : (document.querySelector('input[name="tipo"]:checked')?.value || "")
    const nombre = $("char-nombre").value.trim()
    const velocidad = parseInt($("char-velocidad").value, 10)
    const vidaMax = parseFloat($("char-vida-max").value)
    const ta = parseInt($("char-ta").value, 10)
    if (!nombre || Number.isNaN(velocidad)) {
        showToast("Introduce nombre y velocidad.", true)
        return
    }
    if (!Number.isFinite(vidaMax) || !Number.isFinite(ta)) {
        showToast("Puntos de Vida y TA son obligatorios.", true)
        return
    }
    const base = {
        nombre,
        velocidad,
        vida_max: vidaMax,
        zeon: parseFloat($("char-zeon").value) || 0,
        ki: parseFloat($("char-ki").value) || 0,
        estilo: parseInt($("char-estilo").value, 10) || 0,
        ta,
        dano: parseFloat($("char-dano").value) || 0,
        acumulacion: $("char-acumulacion").checked,
    }
    if (!TIPOS_JUGADOR.includes(tipo)) {
        const ataque = parseInt($("char-ataque").value, 10)
        const defensa = parseInt($("char-defensa").value, 10)
        if (!Number.isFinite(ataque) || !Number.isFinite(defensa)) {
            showToast("Enemigos y PNJ requieren Ataque y Defensa.", true)
            return
        }
        base.ataque = ataque
        base.defensa = defensa
    }
    if (characterModal.mode === "edit") {
        const actual = parseFloat($("char-vida-actual").value)
        base.vida_actual = Number.isFinite(actual) ? actual : vidaMax
        send(Object.assign({ type: "update_character", id: characterModal.id }, base))
    } else {
        send({ type: "add", personaje: Object.assign({ tipo, vida: vidaMax }, base) })
    }
}

function closeCharacterModal() { hideModal("character-modal") }

/* ----------------------------- Ataque ----------------------------- */

function openAttackModal(attackerId, counter = false) {
    const attacker = findTurn(attackerId)
    if (!attacker) {
        showToast("Ese personaje no está en la ronda actual.", true)
        return
    }
    const targets = currentRonda.turnos.filter(p => p.id !== Number(attackerId))
    if (!targets.length) {
        showToast("No hay objetivos disponibles.", true)
        return
    }
    currentAttack = { attackerId: Number(attackerId), counter }
    $("attack-title").textContent = counter ? `Contraataque de ${attacker.nombre}` : `Atacar con ${attacker.nombre}`
    $("attack-target").innerHTML = targets.map(t => `<option value="${t.id}">${escapeHtml(t.nombre)}</option>`).join("")
    $("attack-number").value = ""
    updateAttackForm()
    showModal("attack-modal")
}

function updateAttackForm() {
    if (!currentAttack || !currentRonda) return
    const attacker = findTurn(currentAttack.attackerId)
    const targetId = Number($("attack-target").value)
    const target = findTurn(targetId)
    if (!attacker || !target) return

    const enemigoAtaca = !TIPOS_JUGADOR.includes(attacker.tipo)
    $("attack-number-label").textContent = enemigoAtaca
        ? "Número adicional (se suma a su Ataque guardado)"
        : "Ataque final (número limpio)"

    const targetJugador = TIPOS_JUGADOR.includes(target.tipo)
    $("attack-defensa-numero-field").classList.toggle("hidden", !targetJugador)
    $("attack-defense-field").classList.toggle("hidden", true)

    $("attack-formula-hint").textContent = targetJugador
        ? "Ataque − Defensa limpia del objetivo = porcentaje final (se aplica su TA)."
        : "Ataque − Defensa guardada del objetivo = porcentaje final (se aplica su TA)."

    updateSurpriseWarning()
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

function performAttack() {
    if (!currentAttack) return
    const numero = Number($("attack-number").value)
    if (!Number.isFinite(numero)) {
        showToast("Introduce un número para el ataque.", true)
        return
    }
    const targetId = Number($("attack-target").value)
    const target = findTurn(targetId)
    const payload = {
        type: currentAttack.counter ? "counterattack" : "attack",
        attacker_id: currentAttack.attackerId,
        target_id: targetId,
        numero,
    }
    if (target && TIPOS_JUGADOR.includes(target.tipo)) {
        const defensaNumero = Number($("attack-defensa-numero").value)
        if (!Number.isFinite(defensaNumero)) {
            showToast("Introduce la defensa limpia del objetivo.", true)
            return
        }
        payload.defensa_numero = defensaNumero
    }
    send(payload)
    closeAttackModal()
}

function mostrarResultadoAtaque(data) {
    pendingCounterattack = data.estado === "contraataque" ? data : null
    let html = `<div class="attack-summary"><p><strong>${escapeHtml(data.atacante)}</strong> → <strong>${escapeHtml(data.objetivo)}</strong></p>`
    if (data.sorpresa?.agresor_sorprende) html += `<div class="surprise-warning">⚠ Sorpresa conseguida sobre el objetivo.</div>`
    if (data.sorpresa?.objetivo_sorprende) html += `<div class="surprise-warning">⚠ El objetivo tiene sorpresa sobre el atacante.</div>`
    html += `<div class="result-message ${data.estado}">${escapeHtml(data.mensaje)}</div>`
    html += `<dl class="result-details"><div><dt>Ataque</dt><dd>${escapeHtml(data.ataque_detalle)}</dd></div><div><dt>Defensa</dt><dd>− ${escapeHtml(data.defensa_detalle)}</dd></div><div><dt>Porcentaje</dt><dd>${data.porcentaje}%</dd></div>`
    if (data.estado === "golpe") {
        html += `<div><dt>TA</dt><dd>− ${data.ta * 10}%</dd></div><div><dt>Daño</dt><dd>${fmt(data.dano_total)}</dd></div><div><dt>Vida restante</dt><dd>${fmt(data.vida_actual)}</dd></div>`
    } else {
        html += `<div><dt>Fallo</dt><dd>${data.fallo}%</dd></div>`
    }
    html += `</dl></div>`
    $("attack-result").innerHTML = html
    $("counterattack-area").classList.toggle("hidden", data.estado !== "contraataque")
    showModal("result-modal")

    if (data.estado === "golpe" && data.critico) {
        pendingCritical = { id: data.objetivo_id, nombre: data.objetivo, dano: data.dano_total }
        pendingFallen = data.caido ? { id: data.objetivo_id, nombre: data.objetivo } : null
        showCriticalModal()
    } else if (data.estado === "golpe" && data.caido) {
        pendingFallen = { id: data.objetivo_id, nombre: data.objetivo }
        showFallenModal()
    }
}

function openCounterattack() {
    if (!pendingCounterattack) return
    const attackerId = pendingCounterattack.objetivo_id
    const targetId = pendingCounterattack.atacante_id
    closeResultModal()
    openAttackModal(attackerId, true)
    setTimeout(() => {
        $("attack-target").value = String(targetId)
        updateAttackForm()
    }, 0)
}

/* ----------------------------- Críticos y caídos ----------------------------- */

function showCriticalModal() {
    if (!pendingCritical) return
    $("critical-text").textContent = `${pendingCritical.nombre} ha recibido un crítico de ${fmt(pendingCritical.dano)} de daño.`
    $("critical-level").value = ""
    showModal("critical-modal")
}

function saveCriticalLevel() {
    const level = Number($("critical-level").value)
    if (!Number.isFinite(level)) {
        showToast("Introduce el nivel de crítico.", true)
        return
    }
    send({ type: "critical_level", id: pendingCritical.id, level })
    closeCriticalModal()
}

function closeCriticalModal() {
    hideModal("critical-modal")
    pendingCritical = null
    if (pendingFallen) showFallenModal()
}

function showFallenModal() {
    if (!pendingFallen) return
    $("fallen-text").textContent = `${pendingFallen.nombre} ha caído (vida 0 o menos). ¿Retirar del combate?`
    showModal("fallen-modal")
}

function retirarCaido() {
    if (pendingFallen) send({ type: "delete", id: pendingFallen.id })
    closeFallenModal()
}

function closeFallenModal() {
    hideModal("fallen-modal")
    pendingFallen = null
}

/* ----------------------------- Utilidades ----------------------------- */

function findTurn(id) { return currentRonda?.turnos?.find(p => p.id === Number(id)) }

function getTipoLabel(tipo) {
    if (tipo === "jugador") return "Jugador"
    if (tipo === "aliado") return "Aliado"
    if (tipo === "pnj") return "PNJ"
    return "Enemigo"
}

function getTipoClass(tipo) {
    if (TIPOS_JUGADOR.includes(tipo)) return "nombre-aliado"
    if (tipo === "pnj") return "nombre-pnj"
    return "nombre-enemigo"
}

function getBorderClass(tipo) {
    if (TIPOS_JUGADOR.includes(tipo)) return "turn-jugador"
    if (tipo === "pnj") return "turn-pnj"
    return "turn-enemigo"
}

function chip(label, value) {
    return `<div class="stat-chip">${label} <strong>${escapeHtml(value)}</strong></div>`
}

function fmt(value) {
    const numero = Number(value ?? 0)
    if (!Number.isFinite(numero)) return "0"
    return Number.isInteger(numero) ? String(numero) : String(Math.round(numero * 100) / 100)
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

function showModal(id) {
    const modal = $(id)
    modal.classList.remove("hidden")
    modal.setAttribute("aria-hidden", "false")
}
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

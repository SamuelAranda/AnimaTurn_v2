# AGENTS.md

Combat turn/initiative tracker. FastAPI + WebSocket backend, vanilla JS frontend. Single Spanish-language app (keep user-facing strings, README and comments in Spanish).

## Run

Run from the **repo root** — `StaticFiles(directory="static")` and the template path in `server.py` are relative, so another cwd breaks them.

```bash
pip install -r requirements.txt      # deps
python server.py                     # dev server, host 0.0.0.0:8000, reload=True
# equivalent:
python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

There is no build step, no tests, no linter, and no CI. Do not invent test/lint commands.

## Architecture

- `server.py` — everything: FastAPI app, **all** game logic (initiative, surprise, attacks) and the WebSocket protocol handler (`/ws`). Single file, no packages.
- `templates/index.html` — served at `/`. `static/script.js` — WS client, dynamic tabs/sheets and rendering. `static/style.css`.
- No frontend framework; `script.js` builds HTML strings and calls global `onclick` handlers.
- Session state is **process-global, shared by all connected clients** (one table for everyone). Persisted automatically to `session_state.json` (gitignored) after every mutation and reloaded on startup. Delete that file to reset. Writes are atomic (`.tmp` + replace).

## Enemy generation references (data, not code)

These three files are **reference data/templates only** — `server.py` does **not** read them:

- `enemies.json` — master catalogue of 171 enemies (`id`, `name`, `category`, `class_`, `level`, `attack`, `defense`, `hp_max`/`hp_current`, `armor`, `damage`, `weapon`, `stats`, `abilities`, `resistances`, optional `magic`/`psionics`).
- `armors.json` — armour catalogue: `name → { Filo, Contundente, Penetrante, Calor, Electricidad, Frio, Energia }` (protection value per damage type). 100 entries (fabricadas, `Natural N`/natural materials, `Energía N`). In `enemies.json`, `armor` is always a key of this file or `""` (no armour).
- `REGLAS_PERSONAJES.md` — rules an agent must follow to generate coherent enemies (level × category × `class_`; attack+defence budget; magic/psionic projection ≈60 %).

When adding enemies: append to `enemies.json` `enemies[]` with the next free `id`, follow `REGLAS_PERSONAJES.md`, and never mix archetypes (a physical top role with top projection).

## Character model

Four tipos: `jugador`, `aliado`, `enemigo`, `pnj` (replaced the old `bando`).

- **`jugador`/`aliado`** (`TIPOS_JUGADOR`): no stored `ataque`/`defensa`. Attack with a clean number; defend with a clean number supplied at resolution time.
- **`enemigo`/`pnj`** (`TIPOS_ENEMIGO`): store `ataque`/`defensa`; attack = `ataque + numero`, defend with stored `defensa`.
- Common fields: `velocidad`, `vida_max`, `vida_actual`, `zeon`, `ki`, `estilo`, `ta`, `dano`, `acumulacion`. Required: `vida`, `ta` (and `ataque`, `defensa` for enemigo/pnj). `ta` may be `0`; the **effective** TA used in combat is always `max(1, ta − reduccion_armadura)` (`ta_efectiva()`).
- Dynamic state: `a_la_defensiva` (per round), `criticos: []`, `estados: [{texto, color}]` (custom public tags), plus derived `debil`/`caido`.

## Invariants (easy to break)

- **Enemigo/PNJ combat stats must never be broadcast.** Public payloads only expose their identity + tags; `jugador`/`aliado` data *is* public (their sheet). Keep `datos_personaje_publicos` / `datos_turno_publicos` (server.py) using `etiquetas_publicas` and gate `datos_ficha` behind `TIPOS_JUGADOR`. Full stats only leave the server through `datos_privados`, in response to `get_character`.
- The WS protocol is a `type` string switch in `websocket_endpoint`. Client→server: `add`, `roll`, `delete`, `set_active`, `next`, `get_character`, `update_character`, `critical_level`, `set_estados`, `attack`, `counterattack`, `clear`. Server→client: `init`, `personajes`, `ronda`, `add`, `delete`, `clear`, `character`, `character_saved`, `attack_result`, `error`. Any new type must be handled on both `server.py` and `static/script.js`. The character modal only closes on `character_saved`, so failed `add`/`update_character` keep it open.
- Editing `server.py` auto-reloads (uvicorn `reload=True`); `static/*` changes only need a browser refresh.
- `cargar_estado` migrates old saves (`bando`→`tipo`, `vida`→`vida_max`/`vida_actual`, `parada`/`esquiva`→`defensa`). Keep the migration working when you add fields.

## Domain rules

- `roll` generates **25 rounds** at once; `next` advances the active marker and rolls over to the next round, clearing everyone's `a_la_defensiva`. On entering a new round it **re-reads current `velocidad`/`estilo` and re-rolls that round** (`regenerar_ronda`); later rounds are re-rolled when entered.
- Initiative: `velocidad + d100`, open-ended rolls from 90+, and rolls 1/2/3 map to -125/-100/-75.
- Attack: `porcentaje = ataque_final - defensa`; positive is an impact (even for 0 damage), `<= 0` fails, `<= -10` offers a counterattack. On impact: `ta_efectiva = max(1, ta - reduccion_armadura)` (from the attack's "Reducción de armadura" input), `postTA = max(0, porcentaje - ta_efectiva*10)`; `dano = atacante.dano * postTA / 100`, subtracted from `vida_actual`. Result exposes `reduccion_armadura` and `ta_efectiva`.
- Impact sets `a_la_defensiva` unless the target has `acumulacion`. **Caído** is evaluated *before* **Critical**: if `vida_actual <= 0` the target is caído and critical is never offered (`critico = not caido and dano >= 50%` of pre-hit `vida_actual`). Client prompts for the critical level via `critical_level`. **Débil** below 30% of `vida_max`.
- **Modo GM** is a per-browser toggle (localStorage `animaturn-gm`, `body.gm-mode`): dark theme, and the attack-result screen shows full attributes/calculations. Without it the result shows only the verdict + damage dealt. Server always sends the full `attack_result`; the client gates the display.
- A character added mid-session is appended only to **rounds after the current one** (`rondas[ronda_actual + 1:]`), so it has no turn this round.

## Ignore

- `.github/copilot-instructions.md` is stale (references a `main.py` tkinter GUI that does not exist). Don't follow it.

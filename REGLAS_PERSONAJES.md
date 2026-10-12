# Reglas de creación de personajes/enemigos

Guía de consulta para que un agente cree **personajes nuevos coherentes** con los 161 enemigos existentes en `enemies.json`. No es un generador aleatorio: son reglas que combinan **nivel × tipología (categoría) × arquetipo (`class_`)**.

Los personajes nuevos se añaden **al mismo `enemies.json`**, dentro del array `enemies`, con un `id` único. No se crea ningún archivo aparte.

---

## 1. Estructura obligatoria

Todo enemigo debe tener exactamente estas claves (todas presentes en los 161 registros actuales):

```json
{
  "id": 162,
  "name": "Nombre en español",
  "category": "Comunes",
  "class_": "Guerrero",
  "level": 3,
  "turn": 60,
  "attack": 100,
  "defense": 90,
  "hp_max": 130,
  "hp_current": 130,
  "armor": "Cota de cuero",
  "damage": 45,
  "weapon": "Espada larga",
  "stats":     { "AGI": 6, "DES": 8, "CON": 7, "FUE": 8, "PER": 6, "INT": 5, "VOL": 6, "POD": 5 },
  "abilities": { "Advertir": 70, "Buscar": 60, "Intimidar": 70 },
  "resistances": { "RF": 50, "RE": 50, "RV": 50, "RM": 45, "RP": 50 },
  "special": "Rasgo breve; otro rasgo",
  "manual": "Básico, p. 298"
}
```

Opcionales (solo si el arquetipo los exige):

```json
"magic":    { "proyeccion_magica": 100, "act": 50, "zeon": 685, "nivel_via": 40 },
"psionics": { "proyeccion_psiquica": 115, "potencial_psiquico": 80, "disciplinas": { "Disciplina": ["poder 1", "poder 2"] } }
```

**Reglas fijas (romperlas invalida el personaje):**

- `class_` lleva guion bajo final (`class` es palabra reservada en Python). `db.build_enemy` acepta `class` como respaldo, pero el archivo usa `class_`.
- `hp_current` **siempre** igual a `hp_max` al crear.
- Claves de `stats`: exactamente `AGI, DES, CON, FUE, PER, INT, VOL, POD`.
- Claves de `resistances`: exactamente `RF, RE, RV, RM, RP`.
- `armor`: string de `armors.json`, entero (`Natural X`), o valor de "sin armadura" (`"No"`, `"Ninguna"`, `"N/A"`).
- `special`: string o `null` (nunca dict/lista).
- JSON en UTF-8, con acentos correctos (`"Básico"`, no mojibake).

---

## 2. Los tres ejes de diseño

| Eje | Qué controla |
|---|---|
| **Nivel (0–16)** | Presupuesto de poder: ataque, defensa, turno, daño, stats, resistencias. |
| **Categoría (tipología)** | Naturaleza: curva de HP, sesgo de stats/resistencias, armadura/arma, rasgos de `special`, si puede tener magia/psiónica. |
| **`class_` (arquetipo)** | Rol de combate: qué destaca y **qué sistemas puede o no puede tener** (marcial vs proyección mágica vs psíquica). |

Orden de decisión: **nivel → categoría → arquetipo**. El nivel fija los rangos; la categoría los sesga; el arquetipo decide el reparto de stats y las claves opcionales.

---

## 3. Ataque, defensa y daño

El ataque y la defensa **no los acota el nivel**: parten de un rango amplio y crecen con la experiencia. Regla de diseño (aplica igual a ataque y defensa):

- **Nivel 1: 0–100** (0 = sin capacidad de combate; 100 = combatiente entrenado).
- **Por cada nivel adicional: +10 a +20**, según tipo y categoría.
- **Cada dos niveles: un pequeño salto extra de +5.**
- Fórmula del máximo: `máx(L) = 100 + (L−1)·(10 a 20) + 5·⌊(L−1)/2⌋`. El mínimo puede seguir siendo 0.

Tabla de referencia (máximo con crecimiento medio +15):

| Nivel | ATK/DEF | Nivel | ATK/DEF |
|---|---|---|---|
| 1 | 0–100 | 9 | 0–240 |
| 2 | 0–120 | 10 | 0–260 |
| 3 | 0–135 | 11 | 0–275 |
| 4 | 0–155 | 12 | 0–295 |
| 5 | 0–170 | 13 | 0–310 |
| 6 | 0–190 | 14 | 0–330 |
| 7 | 0–205 | 15 | 0–345 |
| 8 | 0–225 | 16 | 0–365 |

Los datos existentes siguen esta envolvente (L3 máx 140, L8 230, L10 300, L16 350). Los `ATK=0` o `DEF=0` de niveles altos provienen de criaturas cuyo valor va en armadura o en `special`, no de que carezcan de combate.

**Bandas de stats (cada característica):**

| Nivel | Rango típico de stats |
|---|---|
| 0–1 | 3–8 (base 5) |
| 2–3 | 4–11 |
| 4–6 | 5–14 |
| 7–9 | 6–15 |
| 10–12 | 7–16 |
| 13–16 | 8–20 |

Los stats primarios del arquetipo van al tope de la banda; los de descarte, al suelo.

**Bandas de resistencias (cada una de RF/RE/RV/RM/RP):**

| Nivel | Rango típico |
|---|---|
| 0–1 | 20–45 |
| 2–3 | 25–60 |
| 4–6 | 30–90 |
| 7–9 | 40–130 |
| 10–12 | 60–165 |
| 13–16 | 90–195 |

**Turno:** arranca en ~40 (L0) y sube ~7 por nivel, techo ~190. Conjuradores y entidades tienden al tope; criaturas lentas por debajo de la media.

### El daño depende del arma y de la Fuerza, no del nivel

El daño de un personaje **no lo marca el nivel**, sino el **arma** y la **Fuerza (FUE)**: cuanto más grande es el arma, más daño hace, salvo si es mágica o especial.

Fórmula: `daño = daño base del arma + bonificación por FUE`.

**Daño base del arma:**

| Tipo de arma | Ejemplos | Daño base |
|---|---|---|
| Desarmado / sin arma | `No`, `Manos`, `Combate desarmado` | 10 |
| Ligera / pequeña | estilete, daga, arco | 25–30 |
| Media-pequeña / una mano | espada corta, estoque, tanto, hacha pequeña, aguja | 40 |
| Media | espada larga | 50 |
| Grande / dos manos | mandoble, lanza de caballería, hacha de guerra | 55–85 |
| Mágica / especial | armas sobrenaturales | fuera de rango (por su naturaleza) |

**Bonificación por Fuerza (FUE):** FUE 10 → **+15**, y **+5 por cada 2 puntos de FUE** (hacia arriba o hacia abajo). Fórmula: `bonus = 15 + 5·⌊(FUE−10)/2⌋`.

| FUE | 2–3 | 4–5 | 6–7 | 8–9 | 10–11 | 12–13 | 14–15 | 16–17 |
|---|---|---|---|---|---|---|---|---|
| Bonificación | −5 | 0 | +5 | +10 | +15 | +20 | +25 | +30 |

Ejemplos: daga (25) + FUE 10 (+15) = **40**; espada larga (50) + FUE 7 (+5) = **55**.

Con FUE típica (5–10) el daño humanoide acaba oscilando entre **30 y 80**. Solo los **monstruos** escalan el daño con el nivel en vez de (o además de) la FUE (garras, mordisco, aliento: 100–300).

---

## 4. Curvas de HP

Hay **dos curvas**; elegir según la categoría:

- **Humanoide (plana):** Comunes, Maleantes, Luchadores y soldados, Hechiceros, Místicos, Espíritus, Guerrero Mentalista. HP 60–350 en cualquier nivel (no escala con nivel).
- **Monstruo (escala):** Animales, Bestias, Criaturas, Elementales, Constructos, Máquinas, No muertos, Demonios, Entidades. El HP crece fuerte con el nivel:

| Nivel | HP (rango práctico) |
|---|---|
| 0–3 | 60–2 200 |
| 4–6 | 200–3 300 |
| 7–9 | 400–6 200 |
| 10–12 | 800–7 000 |
| 13–16 | 2 000–12 500 |

---

## 5. Perfiles por tipología (categoría)

| Categoría | Niveles obs. | HP | Stats altos | Stats bajos | Resistencias | Arma/Armadura | Magia/Psi |
|---|---|---|---|---|---|---|---|
| Comunes | 0–3 | Humanoide | — | — | Base plana | Sin arma / sin armadura | No |
| Maleantes | 1–8 | Humanoide | PER, AGI, INT | FUE, CON, POD | Base | Arma ligera (daga, espada corta) | No |
| Luchadores y soldados | 1–8 | Humanoide | DES, FUE, CON | INT, POD | Medias parejas | Arma + armadura real | No |
| Animales | 0–4 | Monstruo | FUE, CON, AGI | INT, VOL, POD | RP bajo | Natural / garras / mordisco | No |
| Bestias | 1–7 | Monstruo | FUE, CON, DES, PER | INT | Medias | Natural / garras / fauces | No |
| Elementales | 0–13 | Monstruo | Todo parejo (≈9–11) | — | **Parejas y altas** | Natural X o `Ninguna` | **Sí (Warlock)** |
| Criaturas | 2–15 | Monstruo | CON, FUE | INT, VOL | Parejas, altas | Natural | No |
| No muertos | 0–10 | Monstruo | FUE, CON | INT, VOL, POD, **RM/RP** | **RM/RP bajos (0–60)** | Natural X | No |
| Espíritus | 1–10 | Humanoide | VOL, POD, INT, DES | **CON, FUE** | Altas parejas | `Ninguna` / Natural | Psi excepcional |
| Constructos | 2–12 | Monstruo | CON, FUE, DES | VOL, POD, **RM** | RM baja | Natural X / armadura | No |
| Máquinas | 2–9 | Monstruo | CON, VOL, FUE | POD, **RM** | **RM 0–60** | Natural / artefacto | No |
| Plantas | 1–4 | Monstruo | CON, FUE | INT, VOL, POD | RP/RM bajas | Natural | No |
| Insectos | 1–3 | Humanoide | AGI, DES | INT, VOL, POD | Bajas parejas | Natural / aguijón | No |
| Demonios | 3–8 | Monstruo | FUE, CON, POD | INT | Medias | Natural o arma | No |
| Aberraciones | 3-10 | Monstruo | FUE, CON, POD | INT, PER | Altas parejas | Natural | No |
| Entidades | 8–16 | Monstruo | **Todo alto (13–20)** | — | **Muy altas (90–195)** | Natural | Según arquetipo |
| Místicos | 1–8 | Humanoide | POD, INT, VOL | FUE, CON, AGI | RM alta | Sin arma | **Sí (magia)** |
| Hechiceros | 1-9 | Humanoide | DES, INT, POD | ATK/DEF muy bajos | RM alta | Daga, sin armadura | **Sí (magia)** |

**Reglas de sesgo de resistencias (obligatorias):**

- No muertos, Constructos y Máquinas: `RM` (y a menudo `RP`) muy por debajo del resto.
- Elementales, Espíritus, Entidades: las 5 resistencias parejas entre sí.
- Animales, Bestias, Plantas: `RP` bajo.
- Místicos, Hechiceros, Mentalistas: `RM` elevada.

---

## 6. Contratos por arquetipo (`class_`)

El arquetipo decide **el reparto físico y qué sistema de proyección tiene**. Un personaje **no** debe tener a la vez rol físico tope y proyección tope.

### 6.1 Marcial / combatiente
`Guerrero`, `Maestro en armas` (también escrito `Maestro de Armas`), `Guerrero Acróbata`, `Paladín`, `Paladín oscuro`, clase marcial de `Luchadores y soldados`.

- **Destaca:** `attack`, `defense`, `damage`, `CON`/`FUE`/`DES`.
- **`magic`:** no. **`psionics`:** no.
- **Arma y armadura reales** (`armors.json`).
- Turno medio. Resistencias medias.
- `Paladín` / `Paladín oscuro`: híbrido permitido → puede añadir `magic` a costa de bajar ATK/DEF.

### 6.2 Sigilo / precisión
`Asesino`, `Sombra`, `Ladrón`, `Explorador`.

- **Destaca:** `AGI`, `DES`, `PER`; daño puntual alto.
- **`magic` / `psionics`:** no (salvo que la categoría sea intrínsecamente mágica, p. ej. Sombra elemental).
- Arma ligera (daga, estilete, arco). Armadura ligera o ninguna.
- `defense` baja-media. Habilidades: `Sigilo`, `Ocultarse`, `Trampería`, `Venenos`, `Abrir Cerraduras`, `Robar`.

### 6.3 Mago / conjurador
`Hechicero`, `Warlock`, `Convocador`, `Ilusionista`.

- **Débil físico:** `attack`/`defense`/`damage` bajos, HP humanoide bajo.
- **Obligatorio `magic`:** `proyeccion_magica`, `act`, `zeon`, `nivel_via`. `Convocador` añade `convocar`, `dominar`, `atar`, `desconvocar`.
- **Destaca:** `INT`, `VOL`, `POD`. `RM` alta.
- Proyección mágica escala con el nivel (L3 ≈ 60, L7 ≈ 130, L10 ≈ 190).

### 6.4 Psíquico
`Mentalista`, `Guerrero Mentalista`, `Ilusionista`.

- **Obligatorio `psionics`:** `proyeccion_psiquica`, `potencial_psiquico` y `disciplinas` (dict de disciplina → lista de poderes).
- **Destaca:** `VOL`, `POD`; `Guerrero Mentalista` mantiene combate medio (híbrido).
- **`magic`:** no.

### 6.5 Natural / no inteligente
`Natural`, `Novel` en criaturas.

- **Sin `magic` ni `psionics`.**
- `INT` y `VOL` bajos. Ataques naturales, `weapon` tipo `Natural`/`Garras`/`Mordisco`, `armor` `Natural X` o `Ninguna`.

### 6.6 Híbridos / genéricos
`Dual`, `Entre mundos`, `Nobel`, `Tecnicista`.

- Combina un rol físico con un sistema, con valores **intermedios** en ambos (ni ATK/DEF topes ni proyección tope).
- `Tecnicista`: puede llevar `magic` o rasgos técnicos en `special`, defensa media.

**Tabla resumen de sistemas permitidos:**

| Arquetipo | attack/defense/damage | `magic` | `psionics` |
|---|---|---|---|
| Marcial | Alto | No | No |
| Sigilo | Medio / daño alto | No | No |
| Mago | Bajo | **Sí** | No |
| Psíquico | Bajo | No | **Sí** (Guerrero Mentalista: medio) |
| Natural | Medio | No | No |
| Híbrido | Medio | Opcional | Opcional |

---

## 7. Armadura, arma y manual

- **Armadura:** usar un nombre existente de `armors.json` (52 entradas, p. ej. `"Cota de cuero"`, `"Semicompleta"`, `"Mallas"`, `"Piel"`), un entero para armadura natural (`3` → `Natural 3`) o `"No"`/`"Ninguna"`/`"N/A"`.
- **Arma:** español, coherente con el arquetipo (`"Espada larga"`, `"Daga"`, `"Arco corto"`, `"Garras"`, `"Mordisco"`, `"Natural"`).
- **`manual`:** referencia tipo `"Básico, p. 298"`. Si no aplica, cadena vacía.
- **`abilities`:** usar nombres existentes (coherentes con el rol): `Advertir`, `Buscar`, `Sigilo`, `Ocultarse`, `Proezas de fuerza`, `Intimidar`, `Resistir el dolor`, `Ocultismo`, `Valoración mágica`… El valor escala con el nivel.

---

## 8. Checklist de validación

Antes de insertar, verificar:

1. [ ] `hp_current == hp_max`.
2. [ ] `id` único (el siguiente libre; actualmente 167 está ocupado → usar 168+).
3. [ ] `level` dentro del rango observado de la categoría (o justificar la excepción).
4. [ ] `stats` tiene las 8 claves; `resistances` las 5 claves.
5. [ ] ATK/DEF según §3: **L1 0–100** y **+10 a +20 por nivel** (+5 extra cada dos niveles).
6. [ ] Nivel ⇔ bandas de stats y resistencias de §3.
7. [ ] Daño = daño base del arma + bonificación por FUE (§3); coherencia con el tamaño del arma, salvo monstruos o armas mágicas/especiales.
8. [ ] Resistencia sesgada según tipología (§5): RM/RP bajos en No muertos/Máquinas/Constructos; parejas en Elementales/Espíritus/Entidades.
9. [ ] Arquetipo ⇔ sistemas: Mago → `magic`, Psíquico → `psionics`, Marcial → **ninguno**.
10. [ ] `armor` resoluble en `armors.json` o `Natural X` / sin armadura.
11. [ ] `special` es string o `null`.
12. [ ] JSON escrito en UTF-8 con acentos correctos.
13. [ ] `category` usa la grafía canónica (`Luchadores y soldados`, `Místicos`, `Máquinas`, `Espíritus`).

---

## 9. Plantillas de referencia

Extraídas del patrón real de los datos.

**L0 · Común · Novel** — humanoide plano, sin proyección.
ATK 20, DEF 20, HP 70, Turno 40, Daño 10 (desarmado); stats ≈ 5; resistencias ≈ 20; `armor "No"`, `weapon "No"`.

**L3 · Luchadores y soldados · Guerrero** — marcial con armadura.
ATK 100, DEF 100, HP 130, Turno 70, Daño 50 (arma media); DES/FUE/CON altos, INT/POD bajos; resistencias ≈ 50; `armor` real, arma real.

**L6 · Bestias · Sombra** — monstruo natural.
ATK 190, DEF 195, HP 3000, Turno 145, Daño 100; FUE/CON/DES/PER altos, INT 5; RP bajo; `weapon "Garras"`, `armor "Natural 6"`; sin magia/psi.

**L10 · Místicos · Hechicero** — conjurador.
ATK/DEF bajos, HP ~110, Turno alto, `magic {proyeccion_magica≈190, act≈80, zeon≈1150, nivel_via≈90}`; INT/VOL/POD altos; RM alta; `armor "Ninguna"`.

**L13 · Elementales · Warlock** — elemental poderoso.
ATK/DEF ~270, HP 5000–8500, Turno ~90–120, Daño ~220; stats ≈10–12 parejos; las 5 resistencias parejas y altas; `magic` presente; `special` con rasgos elementales ("Filo de luz", "forma elemental", "exención física").

**L16 · Entidades · (arquetipo según rol)** — cúspide.
ATK 350, DEF 350, HP 5000–10500, Turno 190, Daño 200; **todos** los stats 15–20; resistencias 90–195 parejas.

---

## 10. Cómo insertar en `enemies.json`

1. Abrir `enemies.json` (UTF-8) y localizar el array `"enemies"`.
2. Añadir el objeto nuevo al final del array con `id` = siguiente libre.
3. Respetar la estructura completa de §1 y pasar el checklist de §8.
4. Escribir el archivo **en UTF-8** y con `ensure_ascii=False` si se hace por script, para no garbar los acentos.
5. Ejecutar la app (`python main.py`) desde la raíz del repo para confirmar que carga y la card renderiza bien.

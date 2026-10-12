# Reglas de creación de personajes/enemigos

Guía de consulta para que un agente cree **personajes nuevos coherentes** con los 171 enemigos existentes en `enemies.json`. No es un generador aleatorio: son reglas que combinan **nivel × tipología (categoría) × arquetipo (`class_`)**.

Archivos de referencia (el servidor `server.py` **no** los carga; son datos/plantillas):

- `enemies.json` — catálogo maestro de enemigos (171 registros). Aquí se insertan los nuevos.
- `armors.json` — catálogo de armaduras por nombre, con su modificador por tipo de daño (§7).
- `REGLAS_PERSONAJES.md` — este documento.

Los personajes nuevos se añaden **al mismo `enemies.json`**, dentro del array `enemies`, con un `id` único. No se crea ningún archivo aparte.

---

## 1. Estructura obligatoria

Todo enemigo debe tener exactamente estas claves (todas presentes en los 171 registros actuales):

```json
{
  "id": 172,
  "name": "Nombre en español",
  "category": "Comunes",
  "class_": "Guerrero",
  "level": 3,
  "turn": 60,
  "attack": 125,
  "defense": 120,
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

- `class_` lleva guion bajo final (`class` es palabra reservada en Python). El archivo usa siempre `class_`.
- `hp_current` **siempre** igual a `hp_max` al crear.
- Claves de `stats`: exactamente `AGI, DES, CON, FUE, PER, INT, VOL, POD`.
- Claves de `resistances`: exactamente `RF, RE, RV, RM, RP`.
- `armor`: **nombre exacto** de una clave de `armors.json`, o `""` si el personaje no lleva armadura (nunca un entero, `"No"`, `"Ninguna"` ni `"N/A"`).
- `special`: string o `null` (nunca dict/lista).
- JSON en UTF-8, con acentos correctos (`"Básico"`, no mojibake).

---

## 2. Los tres ejes de diseño

| Eje | Qué controla |
|---|---|
| **Nivel (0–16)** | Presupuesto de poder: ataque+defensa (o proyección), turno, daño, stats, resistencias. |
| **Categoría (tipología)** | Naturaleza: curva de HP, sesgo de stats/resistencias, armadura/arma, rasgos de `special`, si puede tener magia/psiónica. |
| **`class_` (arquetipo)** | Rol de combate: qué destaca y **qué sistemas puede o no puede tener** (marcial vs proyección mágica vs psíquica). |

Orden de decisión: **nivel → categoría → arquetipo**. El nivel fija los rangos; la categoría los sesga; el arquetipo decide el reparto de stats y las claves opcionales.

---

## 3. Ataque, defensa y proyección

El ataque y la defensa se reparten un **presupuesto combinado por arquetipo**. No se acota cada valor por separado: se acota la **suma** `ataque + defensa`.

### 3.1 Arquetipos de combate cuerpo a cuerpo

Los arquetipos con función combativa cuerpo a cuerpo (marciales, sigilo, soldados) reparten entre `attack` y `defense` un total de:

- **Nivel 1: ≈180 puntos** en total (mínimo siempre **160**, máximo **200**).
- **+30 por nivel**, más **+5 cada dos niveles** (aprox.).
- **Diferencia máxima de 30 puntos** entre ataque y defensa: `|attack − defense| ≤ 30`.

Fórmula del presupuesto: `T(L) = 180 + 30·(L−1) + 5·⌊(L−1)/2⌋`.

| Nivel | Total (attack + defense) | Nivel | Total (attack + defense) |
|---|---|---|---|
| 1 | 160–200 (≈180) | 9 | ≈440 |
| 2 | ≈210 | 10 | ≈470 |
| 3 | ≈245 | 11 | ≈505 |
| 4 | ≈275 | 12 | ≈535 |
| 5 | ≈310 | 13 | ≈570 |
| 6 | ≈340 | 14 | ≈600 |
| 7 | ≈375 | 15 | ≈635 |
| 8 | ≈405 | 16 | ≈665 |

Reparte ese total entre ataque y defensa sin pasarte del tope de 30 de diferencia (p. ej. L1 → 90/90, 105/75 o 95/85). No tienen por qué ser iguales, pero no deben distar más de 30.

### 3.2 Arquetipos de combate mágico o psíquico

Mago, conjurador y psíquico son **débiles físicamente**: su `attack`/`defense`/`damage` van bajos o directamente `0`, y el grueso de su poder va en la **proyección** (`proyeccion_magica` o `proyeccion_psiquica`).

Esa proyección lleva **≈60 % del presupuesto marcial** del mismo nivel: `P(L) ≈ 0.6 · T(L)`.

| Nivel | Proyección (≈0.6·T) | Nivel | Proyección (≈0.6·T) |
|---|---|---|---|
| 1 | ≈108–120 | 9 | ≈264 |
| 2 | ≈126 | 10 | ≈282 |
| 3 | ≈147 | 11 | ≈303 |
| 4 | ≈165 | 12 | ≈321 |
| 5 | ≈186 | 13 | ≈342 |
| 6 | ≈204 | 14 | ≈360 |
| 7 | ≈225 | 15 | ≈381 |
| 8 | ≈243 | 16 | ≈399 |

Así, si un soldado de nivel 1 reparte ≈180 (100/80) o hasta 200 (100/100), un combatiente mágico del mismo nivel tendrá una proyección de ≈110–120. Los **híbridos** (Paladín, Guerrero Mentalista, `Dual`, `Entre mundos`) quedan a medio camino: proyección al ~60 % **y** un reparto físico intermedio (por debajo del tope marcial).

### 3.3 Arquetipos no combatientes

`Novel`/`Natural` y personajes sin rol de combate (Comunes, etc.) no usan el presupuesto anterior: conservan el rango amplio (**0–100 en L1**, +10 a +20 por nivel), pudiendo ser `0` si no combaten.

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
| Elementales | 0–13 | Monstruo | Todo parejo (≈9–11) | — | **Parejas y altas** | Natural X o sin armadura | **Sí (Warlock)** |
| Criaturas | 2–15 | Monstruo | CON, FUE | INT, VOL | Parejas, altas | Natural | No |
| No muertos | 0–10 | Monstruo | FUE, CON | INT, VOL, POD, **RM/RP** | **RM/RP bajos (0–60)** | Natural X | No |
| Espíritus | 1–10 | Humanoide | VOL, POD, INT, DES | **CON, FUE** | Altas parejas | sin armadura / Natural | Psi excepcional |
| Constructos | 2–12 | Monstruo | CON, FUE, DES | VOL, POD, **RM** | RM baja | Natural X / armadura | No |
| Máquinas | 2–9 | Monstruo | CON, VOL, FUE | POD, **RM** | **RM 0–60** | Natural / artefacto | No |
| Plantas | 1–4 | Monstruo | CON, FUE | INT, VOL, POD | RP/RM bajas | Natural | No |
| Insectos | 1–3 | Humanoide | AGI, DES | INT, VOL, POD | Bajas parejas | Natural / aguijón | No |
| Demonios | 3–8 | Monstruo | FUE, CON, POD | INT | Medias | Natural o arma | No |
| Aberraciones | 3-10 | Monstruo | FUE, CON, POD | INT, PER | Altas parejas | Natural | No |
| Entidades | 8–16 | Monstruo | **Todo alto (13–20)** | — | **Muy altas (90–195)** | Natural | Según arquetipo |
| Místicos | 1–8 | Humanoide | POD, INT, VOL | FUE, CON, AGI | RM alta | Sin arma | **Sí (magia)** |
| Hechiceros | 1-9 | Humanoide | DES, INT, POD | ATK/DEF muy bajos | RM alta | Daga, sin armadura | **Sí (magia)** |

El reparto de `attack`/`defense` y de la proyección de cada fila sigue §3: los perfiles con combate cuerpo a cuerpo usan el presupuesto `T(L)` (≈180 en L1), y los mágicos/psíquicos van a proyección `≈0.6·T(L)` con físico bajo o nulo.

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
- **Presupuesto físico:** reparte `attack + defense` según §3.1 → `T(L)` (L1 ≈180, mín 160, máx 200) con **≤30** de diferencia entre ambos.
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
- Proyección mágica escala con el nivel a ≈60 % del presupuesto marcial (§3.2): L1 ≈110–120, L3 ≈150, L5 ≈190, L8 ≈245, L10 ≈280.

### 6.4 Psíquico
`Mentalista`, `Guerrero Mentalista`, `Ilusionista`.

- **Obligatorio `psionics`:** `proyeccion_psiquica` (≈60 % del presupuesto marcial, §3.2), `potencial_psiquico` y `disciplinas` (dict de disciplina → lista de poderes).
- **Destaca:** `VOL`, `POD`; `Guerrero Mentalista` mantiene combate medio (híbrido).
- **`magic`:** no.

### 6.5 Natural / no inteligente
`Natural`, `Novel` en criaturas.

- **Sin `magic` ni `psionics`.**
- `INT` y `VOL` bajos. Ataques naturales, `weapon` tipo `Natural`/`Garras`/`Mordisco`, `armor` `Natural X` o `""` (sin armadura).

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

- **Armadura:** usar un nombre exacto de `armors.json` (100 entradas), o `""` si el personaje no lleva armadura (nunca un entero, `"No"`, `"Ninguna"` ni `"N/A"`).

### 7.1 Armaduras (`armors.json`)

`armors.json` es un objeto `nombre → { tipo_de_daño: valor }`. El **valor** es el grado de protección de esa armadura frente a cada tipo de daño (más alto = más protección; `0` = sin protección de ese tipo). Los siete tipos de daño son siempre las mismas claves:

`Filo`, `Contundente`, `Penetrante`, `Calor`, `Electricidad`, `Frio`, `Energia`.

Familias de entradas:

- **Fabricadas** (humanoides): desde `Acolchada`, `Cota de cuero`, `Gabardina`, `Piel`, `Mallas`, `Peto`, `Semicompleta`, `Placas`, `Completa`, `Completa pesada`, `De campaña pesada`… hasta sus variantes `… reforzada` (`Acolchada reforzada`, `Mallas reforzadas`, `Completa pesada reforzada`, etc.).
- **Naturales** (criaturas/constructos): `Natural 2`…`Natural 12`, `Natural escamas 4/7/8/9/10/12`, `Natural + Reforzada 6`, `Cuerpo de piedra`, `Cuerpo de piedra pulida`, `Cuerpo de diamante`, `Caparazón de metal`, `Cuerpo de metal`, `Armadura quitinosa`, `Quitina 2/8/13`, `Huesos 5`, `Madera 2`, `Roca 10`, `Escamas de Cristal 12`, `Escamas negras 12`, `Metal 6/7`, `Metal Estelar 6`, `Sombras 4`, `Necrod 3`, `Absodian 10`, `Infernal 6`, `Demoníaca 2`, `Fase 8`, `Placas sombrías`.
- **Energía** (elementales/entidades): `Energía 2`…`Energía 12` (solo protegen `Energia`; el resto a `0`).

Reglas al asignar armadura:

- Usa **exactamente** uno de los nombres del archivo (respeta mayúsculas y acentos). No inventes nombres nuevos ni variantes que no existan.
- No cambies los valores por tipo de daño: la armadura "es lo que dice" `armors.json`.
- Para monstruos usa `Natural N` (N = grado), o `""` si no lleva armadura; nunca fuerces una armadura fabricada en una criatura natural.
- Si el catálogo no cubre un caso y no encaja en ninguna familia, usa `""` (sin armadura) en vez de inventar una entrada.
- **Arma:** español, coherente con el arquetipo (`"Espada larga"`, `"Daga"`, `"Arco corto"`, `"Garras"`, `"Mordisco"`, `"Natural"`).
- **`manual`:** referencia tipo `"Básico, p. 298"`. Si no aplica, cadena vacía.
- **`abilities`:** usar nombres existentes (coherentes con el rol): `Advertir`, `Buscar`, `Sigilo`, `Ocultarse`, `Proezas de fuerza`, `Intimidar`, `Resistir el dolor`, `Ocultismo`, `Valoración mágica`… El valor escala con el nivel.

---

## 8. Checklist de validación

Antes de insertar, verificar:

1. [ ] `hp_current == hp_max`.
2. [ ] `id` único (el siguiente libre; actualmente 171 está ocupado → usar 172+).
3. [ ] `level` dentro del rango observado de la categoría (o justificar la excepción).
4. [ ] `stats` tiene las 8 claves; `resistances` las 5 claves.
5. [ ] ATK/DEF según §3: cuerpo a cuerpo = `T(L)` (L1 ≈180, mín 160, máx 200; **+30/nivel y +5 cada dos niveles**; `|ATK−DEF| ≤ 30`); mágico/psíquico = físico bajo y proyección `≈0.6·T(L)`.
6. [ ] Nivel ⇔ bandas de stats y resistencias de §3.
7. [ ] Daño = daño base del arma + bonificación por FUE (§3); coherencia con el tamaño del arma, salvo monstruos o armas mágicas/especiales.
8. [ ] Resistencia sesgada según tipología (§5): RM/RP bajos en No muertos/Máquinas/Constructos; parejas en Elementales/Espíritus/Entidades.
9. [ ] Arquetipo ⇔ sistemas: Mago → `magic`, Psíquico → `psionics`, Marcial → **ninguno**. La proyección va a ≈60 % del presupuesto marcial (§3.2).
10. [ ] `armor` es una clave de `armors.json` o `""` (sin armadura).
11. [ ] `special` es string o `null`.
12. [ ] JSON escrito en UTF-8 con acentos correctos.
13. [ ] `category` usa la grafía canónica (`Luchadores y soldados`, `Místicos`, `Máquinas`, `Espíritus`).

---

## 9. Plantillas de referencia

Extraídas del patrón real de los datos.

**L0 · Común · Novel** — humanoide plano, sin proyección.
ATK 20, DEF 20, HP 70, Turno 40, Daño 10 (desarmado); stats ≈ 5; resistencias ≈ 20; `armor ""`, `weapon "No"`.

**L3 · Luchadores y soldados · Guerrero** — marcial con armadura.
ATK+DEF ≈245 (p. ej. ATK 125 / DEF 120, máx 30 de diferencia), HP 130, Turno 70, Daño 50 (arma media); DES/FUE/CON altos, INT/POD bajos; resistencias ≈ 50; `armor` real (`armors.json`), arma real.

**L6 · Bestias · Sombra** — monstruo natural.
ATK+DEF ≈340 (p. ej. ATK 170 / DEF 170), HP 3000, Turno 145, Daño 100; FUE/CON/DES/PER altos, INT 5; RP bajo; `weapon "Garras"`, `armor "Natural 6"`; sin magia/psi.

**L10 · Místicos · Hechicero** — conjurador.
ATK/DEF bajos (0), HP ~110, Turno alto, `magic {proyeccion_magica≈280, act≈80, zeon≈1150, nivel_via≈90}`; INT/VOL/POD altos; RM alta; `armor ""`.

**L13 · Elementales · Warlock** — elemental poderoso.
ATK+DEF ≈570 (p. ej. ATK 285 / DEF 285), HP 5000–8500, Turno ~90–120, Daño ~220; stats ≈10–12 parejos; las 5 resistencias parejas y altas; `magic` presente; `special` con rasgos elementales ("Filo de luz", "forma elemental", "exención física").

**L16 · Entidades · (arquetipo según rol)** — cúspide.
ATK+DEF ≈665 (p. ej. ATK 335 / DEF 330), HP 5000–10500, Turno 190, Daño 200; **todos** los stats 15–20; resistencias 90–195 parejas.

---

## 10. Cómo insertar en `enemies.json`

1. Abrir `enemies.json` (UTF-8) y localizar el array `"enemies"`.
2. Añadir el objeto nuevo al final del array con `id` = siguiente libre (172+).
3. Respetar la estructura completa de §1 y pasar el checklist de §8.
4. Escribir el archivo **en UTF-8** y con `ensure_ascii=False` si se hace por script, para no garbar los acentos.
5. Ejecutar la app (`python server.py`) desde la raíz del repo para confirmar que carga y la card renderiza bien.

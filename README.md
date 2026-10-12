# Combat Turn Simulator

Aplicación web en Python para gestionar la iniciativa y resolver combates por turnos durante 25 rondas.

## Descripción

La aplicación permite añadir personajes de cuatro tipos:

- **Jugador** y **Aliado**: no guardan Ataque ni Defensa. Atacan introduciendo el **número limpio** (ya con sus bonos y malus calculados) y defienden introduciendo su **defensa limpia** cuando son el objetivo.
- **Enemigo** y **PNJ**: guardan Ataque y Defensa en su creación. Al atacar usan su Ataque guardado (más un número adicional) y al defender usan su Defensa guardada.

Campos comunes: `nombre`, `velocidad` (iniciativa), `puntos de vida`, `zeon`, `ki`, `estilo`, `TA`, `daño` y un check de `acumulación`. `Puntos de Vida` y `TA` son obligatorios (la `TA` **puede ser 0**); en Enemigo/PNJ también lo son `Ataque` y `Defensa`.

## Iniciativa

En cada ronda cada personaje realiza una tirada de `d100` que se suma a su velocidad base:

- Primer resultado `90-100`: tirada abierta, se vuelve a lanzar subiendo el umbral (`91-100`, `92-100`, ... hasta `100-100`).
- Resultados `1`, `2` y `3` se convierten en `-125`, `-100` y `-75` respectivamente.

Se generan **25 rondas** de una vez y se avanza por ellas. El botón **Siguiente personaje** pasa el marcador de turno al siguiente personaje y, al terminar la ronda, pasa a la siguiente ronda automáticamente. Al entrar en una ronda nueva se **vuelven a consultar la velocidad y el estilo** actuales de los contendientes y se **re-tiran** las iniciativas de esa ronda.

La sorpresa entre personajes se calcula por diferencia de iniciativa y umbrales de `estilo` en la ronda 1 (`DIF`, `MDF`, `ABS`, `CIM`, `IMP`, `INH`, `ZEN`).

## Combate

El personaje activo puede lanzar una **acción ofensiva** contra cualquier otro personaje de la ronda.

- **Enemigo/PNJ ataca**: `ataque_final = Ataque guardado + número`.
- **Jugador/Aliado ataca**: `ataque_final = número limpio`.
- **Defensa**: si el objetivo es Enemigo/PNJ se usa su Defensa guardada; si es Jugador/Aliado, la defensa limpia que introduce.

`porcentaje = ataque_final - defensa`. Un resultado positivo es impacto (aunque el daño final sea 0); `0` o menos es fallo; `-10` o menos ofrece **contraataque**.

En la acción ofensiva hay un bloque de **Reducción de armadura**: resta valor a la **TA** del objetivo antes de calcular el daño. La **TA efectiva** es siempre `max(1, TA − reducción)`, de modo que la TA nunca baja de 1 (aunque el personaje tenga TA `0`). El daño se calcula como `daño_base × porcentaje_post_TA / 100`, restándose de la vida actual.

### Estados y etiquetas

- **A la Defensiva** (tarjeta azul claro): el personaje impactado la recibe, salvo que tenga marcada la `Acumulación`. Se limpia al terminar la ronda.
- **Crítico**: si el daño de un golpe es `≥ 50%` de la vida actual del objetivo, salta una ventana roja que pide el **Nivel de Crítico** (mostrando el daño recibido). El nivel se muestra como etiqueta negativa, p. ej. `-5`. Si el golpe **deja al personaje caído** (vida `0` o menos), no se ofrece crítico: se evalúa la caída primero.
- **Débil**: la vida está por debajo del 30% de la vida máxima.
- **Caído**: la vida llega a 0 o menos. Aparece un aviso con la opción de retirar al personaje del combate (su tarjeta desaparece) o mantenerlo.
- **Estados/Tags personalizados**: en la pestaña **Combate**, al pulsar sobre cualquier personaje se abre una ventana para añadir **estados** de texto libre (alfanumérico) eligiendo color entre **rojo, verde, amarillo, azul, naranja y morado**. Se pueden borrar y se muestran sobre las tarjetas de combate, en la reserva y en la ficha.

## Modo GM

En la cabecera hay un switch de **Modo GM** (por navegador, se guarda en el navegador):

- **Activado**: el tema pasa a **fondo oscuro** y la pantalla de resultado del ataque muestra todos los datos (**Ataque, Defensa, Porcentaje, Reducción de armadura, TA efectiva, Daño y Vida restante**).
- **Desactivado**: la pantalla de resultado solo muestra el veredicto (**impacto, fallo o contraataque posible**) y el **Daño causado**, sin atributos ni cálculos ni la vida restante.

## Fichas y pestañas

Además de **Preparación** y **Combate**, cada **Jugador/Aliado** tiene su propia pestaña que funciona como ficha: muestra vida, zeon, ki, estilo, TA, daño y sus etiquetas, y permite editar sus datos. Cuando es su turno, la ficha indica **"Es tu turno"** y ofrece la acción ofensiva.

Las tarjetas del orden de turnos colorean su borde según el tipo cuando están activas: verde (Jugador/Aliado), amarillo (PNJ) y rojo (Enemigo). Los datos de combate de Enemigos y PNJ están ocultos en sus fichas (solo se muestran sus etiquetas); se abren mediante el botón de edición para consultarlos o cambiarlos.

Se puede añadir un personaje nuevo en cualquier momento: queda sin turno durante la ronda en curso y se incorpora con normalidad a partir de la siguiente.

## Cómo ejecutarlo

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

2. Arranca el servidor:
   ```bash
   python server.py
   ```

   Alternativa equivalente:
   ```bash
   python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
   ```

3. Abre la aplicación en el navegador:
   - Local: [http://localhost:8000](http://localhost:8000)
   - Red local: `http://TU_IP:8000`

## Estructura

- `server.py`: servidor FastAPI, WebSocket y toda la lógica de iniciativa y combate.
- `templates/index.html`: interfaz principal y modales.
- `static/script.js`: cliente WebSocket, pestañas/fichas y renderizado de rondas.
- `static/style.css`: estilos, estados y adaptación móvil.
- `enemies.json`: catálogo de referencia con 171 enemigos (nivel, categoría, arquetipo, stats, armadura, daño, etc.).
- `armors.json`: catálogo de armaduras de referencia (100 entradas) con su modificador por tipo de daño (Filo, Contundente, Penetrante, Calor, Electricidad, Frío, Energía).
- `REGLAS_PERSONAJES.md`: reglas para generar personajes/enemigos coherentes con el catálogo.

Los archivos `enemies.json`, `armors.json` y `REGLAS_PERSONAJES.md` son **datos y plantillas de referencia**: el servidor **no** los carga, solo sirven de guía para crear enemigos nuevos.

## Requisitos

- Python 3.x
- FastAPI
- Uvicorn

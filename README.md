# Combat Turn Simulator

Aplicacion web en Python para calcular la iniciativa de combate durante 25 rondas.

## Descripcion

La aplicacion permite anadir personajes con estos datos:

- `nombre`
- `velocidad`
- `estilo`

En cada ronda, cada personaje realiza una tirada de `d100` que se suma a su velocidad base. La iniciativa usa estas reglas especiales:

- Si el primer resultado es `90-100`, hay tirada abierta y se vuelve a lanzar.
- Tras una abierta, el nuevo umbral sube a `91-100`, luego `92-100` y asi sucesivamente hasta `100-100`.
- Si el primer resultado es `1`, la tirada pasa a `-125`.
- Si el primer resultado es `2`, la tirada pasa a `-100`.
- Si el primer resultado es `3`, la tirada pasa a `-75`.

La version web tambien calcula:

- Sorpresa entre personajes segun la diferencia de iniciativa.
- Umbrales especiales basados en `estilo` durante la ronda 1.
- Tipos de sorpresa como `DIF`, `MDF`, `ABS`, `CIM`, `IMP`, `INH` y `ZEN`.

La comunicacion entre cliente y servidor se hace en tiempo real mediante `WebSocket`.

## Como ejecutarlo

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

3. Abre la aplicacion en el navegador:
   - Local: [http://localhost:8000](http://localhost:8000)
   - Red local: `http://TU_IP:8000`

## Estructura

- `server.py`: servidor FastAPI y logica de iniciativa.
- `templates/index.html`: interfaz principal.
- `static/script.js`: cliente WebSocket y renderizado de rondas.
- `static/style.css`: estilos basicos y adaptacion movil.

## Requisitos

- Python 3.x
- FastAPI
- Uvicorn
## Combate y ataques

La interfaz incluye una pestaña de **Combate** separada de la preparación. Al pulsar sobre un personaje en preparación se pueden editar sus datos privados de combate: `Ataque`, `TA`, `Parada`, `Esquiva`, `Daño` y `Vida`. Estos valores no se muestran en las tarjetas públicas ni se envían al cliente salvo cuando se abre su editor privado.

Durante el combate cada personaje recibe un marcador de turno. El personaje activo puede realizar una acción de ataque seleccionando un objetivo, una defensa (`Parada` o `Esquiva`) y un número. El servidor calcula `Ataque + número - defensa`. Con resultado positivo se aplica TA (`TA x 10`) y se calcula el daño porcentual sobre el daño base del atacante. Los resultados de `0` o menos son fallos; a partir de `-10` se ofrece un contraataque.

La pantalla de ataque también avisa si existe sorpresa entre atacante y objetivo en la ronda actual. El botón **Siguiente personaje** avanza el marcador y, al terminar la ronda, pasa automáticamente a la siguiente.

### Personaje activo
La pestaña Combate permite cambiar manualmente el personaje activo con **Hacer activo**. El botón **Siguiente personaje** continúa avanzando por el orden de iniciativa y también cambia el activo.

Los personajes de la pestaña **Preparación** permanecen visibles después de generar la iniciativa para poder seguir consultando y editando sus datos secretos.

# Combat Turn Simulator

Aplicacion web en Python para calcular la iniciativa de combate durante 25 rondas.

## Descripcion

La aplicacion permite anadir personajes con estos datos:

- `nombre`
- `velocidad`
- `estilo`

En cada ronda, cada personaje realiza una tirada de `d100`. Si el resultado es `90` o superior, la tirada pasa a valer `160`. Ese valor se suma a la velocidad base y el sistema ordena los turnos de mayor a menor.

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

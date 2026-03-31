# Combat Turn Simulator

A simple Python program with a GUI for simulating combat turns in a game.

## Description

This program allows players and enemies to input their speeds. It then simulates 10 rounds of combat, where each round a d100 (1-100) roll is added to each entity's speed, and the entities are sorted from highest to lowest total speed.

## How to Run

### GUI Version
Run `python main.py` to start the GUI.

Add players and enemies by entering name and speed, then click "Simulate" to see the results.

### Web Version
1. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

2. Start the server:
   ```powershell
   python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000
   ```

3. Access the application:
   - **Local:** http://localhost:8000
   - **Other devices:** http://YOUR_IP:8000

## Requirements

- Python 3.x
- Tkinter (usually included with Python)
- FastAPI
- Uvicorn
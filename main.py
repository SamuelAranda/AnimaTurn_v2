import tkinter as tk
from tkinter import ttk
import random

personajes = []

def agregar_personaje():
    nombre = entrada_nombre.get().strip()

    if not nombre:
        return

    try:
        velocidad = int(entrada_velocidad.get())
    except ValueError:
        return

    personajes.append((nombre, velocidad))
    lista_personajes.insert(tk.END, f"{nombre} (Vel: {velocidad})")

    entrada_nombre.delete(0, tk.END)
    entrada_velocidad.delete(0, tk.END)


def limpiar_personajes():
    personajes.clear()
    lista_personajes.delete(0, tk.END)


def generar_rondas():
    resultado.delete("1.0", tk.END)

    for ronda in range(1, 11):
        turnos = []

        for nombre, velocidad in personajes:
            roll = random.randint(1, 100)
            tirada = 160 if roll >= 90 else roll
            total = velocidad + tirada
            turnos.append((nombre, velocidad, roll, tirada, total))

        turnos.sort(key=lambda x: x[4], reverse=True)

        resultado.insert(tk.END, f"\n--- RONDA {ronda} ---\n")

        for nombre, velocidad, roll, tirada, total in turnos:

            surprise = [
                other_nombre
                for other_nombre, _, _, _, other_total in turnos
                if nombre != other_nombre and total > other_total + 150
            ]

            s_str = f" (S - {', '.join(surprise)})" if surprise else ""

            if roll >= 90:
                resultado.insert(
                    tk.END,
                    f"{nombre}: Vel {velocidad} + d100({roll}) -> 160 = {total}{s_str}\n"
                )
            else:
                resultado.insert(
                    tk.END,
                    f"{nombre}: Vel {velocidad} + d100({roll}) = {total}{s_str}\n"
                )


ventana = tk.Tk()
ventana.title("Turnos de Combate")
ventana.geometry("600x800")

frame = ttk.Frame(ventana, padding=10)
frame.grid(row=0, column=0, sticky=tk.NSEW)

ventana.rowconfigure(0, weight=1)
ventana.columnconfigure(0, weight=1)

frame.rowconfigure(3, weight=1)
frame.rowconfigure(6, weight=1)
frame.columnconfigure(0, weight=1)
frame.columnconfigure(1, weight=1)

ttk.Label(frame, text="Nombre").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
entrada_nombre = ttk.Entry(frame)
entrada_nombre.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

ttk.Label(frame, text="Velocidad").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
entrada_velocidad = ttk.Entry(frame)
entrada_velocidad.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

ttk.Button(frame, text="Agregar", command=agregar_personaje).grid(
    row=2, column=0, sticky=tk.EW, padx=5, pady=5
)

ttk.Button(frame, text="Limpiar", command=limpiar_personajes).grid(
    row=2, column=1, sticky=tk.EW, padx=5, pady=5
)

lista_personajes = tk.Listbox(frame, height=6)
lista_personajes.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)

ttk.Button(frame, text="Generar 10 rondas", command=generar_rondas).grid(
    row=4, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10
)

resultado = tk.Text(frame, width=40, height=20)
resultado.grid(row=6, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)

entrada_velocidad.bind("<Return>", lambda e: agregar_personaje())

ventana.mainloop()
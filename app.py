import json
import os
import threading
import time
import webbrowser

import serial
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

from registro import ENTRADA, SALIDA, Registro

app = Flask(__name__)
app.config["SECRET_KEY"] = "oniet30-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

IMG_DIR = os.path.join(os.path.dirname(__file__), "img")

SERIAL_PORT = os.environ.get("ARDUINO_PORT", "COM3")
SERIAL_BAUDRATE = int(os.environ.get("ARDUINO_BAUDRATE", "9600"))

attendee_count = 0
registro = None  # se crea al arrancar (punto 0)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/img/<path:filename>")
def serve_img(filename):
    """Serves files from the project's img/ folder (logo, background video, etc.)."""
    return send_from_directory(IMG_DIR, filename)


@app.route("/reporte")
def reporte():
    """Reporte en vivo de la sesion actual (entradas/salidas por hora)."""
    return render_template("reporte.html", estado_json=estado_json(registro.estado()))


def estado_json(estado):
    return json.dumps(estado).replace("</", "<\\/")


def emitir_registro(estado):
    socketio.emit("registro_update", estado)


@socketio.on("connect")
def handle_connect():
    socketio.emit("count_update", {"count": attendee_count})


def set_count(new_count: int):
    """Call this from your entry-counting logic (scanner, sensor, admin panel, etc.)
    to broadcast the updated attendee count to every connected screen."""
    global attendee_count
    attendee_count = max(0, new_count)
    socketio.emit("count_update", {"count": attendee_count})


def increment(delta: int = 1):
    set_count(attendee_count + delta)


COUNT_PREFIX = "Personas presentes:"
EVENTOS = {"Entrada detectada": ENTRADA, "Salida detectada": SALIDA}


def read_from_arduino():
    """Lee el conteo desde el Arduino por cable USB (puerto serie).
    El sketch manda varias líneas de log; la del conteo tiene el formato
    "Personas presentes: N", que es la única que nos interesa parsear."""
    while True:
        try:
            with serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1) as ser:
                print(f"Conectado al Arduino en {SERIAL_PORT} @ {SERIAL_BAUDRATE} baud")
                while True:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue
                    print(f"Arduino: {line}")
                    if line in EVENTOS:
                        registro.registrar(EVENTOS[line])
                    if line.startswith(COUNT_PREFIX):
                        try:
                            set_count(int(line[len(COUNT_PREFIX):].strip()))
                        except ValueError:
                            pass
        except serial.SerialException as exc:
            print(f"No se pudo abrir {SERIAL_PORT} ({exc}). Reintentando en 5s...")
            time.sleep(5)


if __name__ == "__main__":
    registro = Registro(on_change=emitir_registro)
    registro.iniciar_cortes_horarios()
    threading.Timer(2, webbrowser.open, ["http://localhost:5000/reporte"]).start()
    threading.Thread(target=read_from_arduino, daemon=True).start()
    try:
        socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        ruta = registro.finalizar()
        print(f"Reporte final: {ruta}")
        webbrowser.open("file:///" + ruta.replace("\\", "/"))

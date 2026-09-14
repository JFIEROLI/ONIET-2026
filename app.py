import os

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "oniet30-secret"
socketio = SocketIO(app, cors_allowed_origins="*")

IMG_DIR = os.path.join(os.path.dirname(__file__), "img")

attendee_count = 0


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/img/<path:filename>")
def serve_img(filename):
    """Serves files from the project's img/ folder (logo, background video, etc.)."""
    return send_from_directory(IMG_DIR, filename)


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


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)

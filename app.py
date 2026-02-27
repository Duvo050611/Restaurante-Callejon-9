"""
Módulo Principal de la Aplicación Flask - Restaurante Callejón 9
"""
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, session, redirect, url_for
from flask_cors import CORS
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room
from datetime import datetime
import os
import sys

from routes import routes_bp

# ================================
# CONFIG PYSPARK (si lo usas)
# ================================
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
# Inicialización de Flask
# En app.py
app = Flask(__name__,template_folder="resources/views",static_folder="static")
# Configuración de CORS
# ================================
# FLASK
# ================================
app = Flask(
    __name__,
    template_folder="resources/views",
    static_folder="static"
)

# ================================
# CORS
# ================================
lista_origenes = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://localhost:5000",
]

CORS(app, supports_credentials=True, resources={r"/*": {"origins": lista_origenes}})

# ================================
# SOCKET.IO
# ================================
socketio = SocketIO(
    app,
    cors_allowed_origins=lista_origenes,
        async_mode="threading",
    manage_session=False
)

# Registrar Blueprint de rutas
app.register_blueprint(routes_bp)

# Registrar rutas de reportes
from routes import register_reports_routes
register_reports_routes(app)

# 🔑 CLAVE SECRETA (Usa una variable de entorno en producción)
app.secret_key = os.getenv("SECRET_KEY", "22d6225b061b6b75979d7b4fd5bfb6993b32a66346c0d188fd6f3a37ac36698e")

session_dir = os.path.join(os.getcwd(), "flask_session")
os.makedirs(session_dir, exist_ok=True)

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = session_dir
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # True en producción
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "callejon9_session"

# Inicializar extensión de sesiones
Session(app)

# ================================
# CONTEXT
# ================================
@app.context_processor
def inject_now():
    return {"now": datetime.now}

# ================================
# LOG REQUEST
# ================================
@app.before_request
def log_request():
    if request.path.startswith("/static"):
        return
    print(f"\n📡 {request.method} {request.path}")
    print("🍪 Cookies:", request.cookies.keys())

# ================================
# SOCKET EVENTS
# ================================
@socketio.on("connect")
def socket_connect(auth):
    print("🔌 Socket conectado")
    print("Auth:", auth)

@socketio.on("disconnect")
def socket_disconnect():
    print("❌ Socket desconectado")

@socketio.on("join_room")
def on_join_room(room):
    join_room(room)
    print(f"📥 Cliente unido a sala: {room}")

# ================================
# ERRORES
# ================================
@app.errorhandler(404)
def not_found(e):
    return redirect(url_for("routes.login"))

@app.errorhandler(403)
def forbidden(e):
    return redirect(url_for("routes.login"))

# ================================
# BLUEPRINT
# ================================
app.register_blueprint(routes_bp)

# ================================
# RUN
# ================================
if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print("=" * 60)
    print("🍽️ CALLEJÓN 9 - SOCKET.IO ACTIVO")
    print(f"📍 http://127.0.0.1:5000")
    print(f"📍 http://{local_ip}:5000")
    print("=" * 60)

    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )

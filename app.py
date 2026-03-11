"""
Módulo Principal de la Aplicación Flask - Restaurante Callejón 9
"""
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, session, redirect, url_for
from flask_cors import CORS
from routes import routes_bp
import os
import sys
from flask_session import Session
from datetime import datetime
# Configuración de entorno para PySpark
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable


app = Flask(__name__, template_folder="resources/views", static_folder="static")

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# Configuración de CORS
lista_origenes = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:3000",
    "http://localhost:5000",
]

CORS(app, resources={r"/*": {"origins": lista_origenes}}, supports_credentials=True)

# Logging de peticiones
@app.before_request
def log_request_info():
    """Log de información de cada petición"""
    if request.path.startswith("/static"):
        return
    
    print(f"\n📡 Petición: {request.method} {request.path}")
    print(f"   🍪 Cookies: {list(request.cookies.keys())}")
    
    if 'usuario_id' in session:
        print(f"   ✅ Usuario: {session.get('usuario_nombre')} (Rol: {session.get('usuario_rol')})")
    else:
        print(f"   ❌ Sin sesión activa")

# Registrar Blueprint de rutas
app.register_blueprint(routes_bp)

# Registrar rutas de reportes
from routes import register_reports_routes
register_reports_routes(app)

# CLAVE SECRETA
app.secret_key = os.getenv("SECRET_KEY", "22d6225b061b6b75979d7b4fd5bfb6993b32a66346c0d188fd6f3a37ac36698e")

# Configuración de Sesiones
session_dir = os.path.join(os.getcwd(), "flask_session")
if not os.path.exists(session_dir):
    os.makedirs(session_dir)

# Limpiar sesiones antiguas al iniciar
import time
try:
    for archivo in os.listdir(session_dir):
        filepath = os.path.join(session_dir, archivo)
        if os.path.isfile(filepath):
            # Eliminar archivos de sesión mayores a 24 horas
            if os.path.getmtime(filepath) < time.time() - 86400:
                os.remove(filepath)
                print(f"🗑️  Sesión antigua eliminada: {archivo}")
except Exception as e:
    print(f"⚠️  Error limpiando sesiones: {e}")

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = session_dir
app.config["SESSION_PERMANENT"] = False  
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # True en producción con HTTPS
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_NAME"] = "callejon9_session"
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# Inicializar extensión de sesiones
Session(app)
@app.context_processor
def inject_now():
    return {"now": datetime.now}
# Manejador de errores 404
@app.errorhandler(404)
def page_not_found(e):
    return redirect(url_for('routes.login'))

# Manejador de errores 403
@app.errorhandler(403)
def forbidden(e):
    return redirect(url_for('routes.login'))

if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    import platform
    is_windows = platform.system() == "Windows"
    
    print("=" * 60)
    print("🍽️  CALLEJÓN 9 - SISTEMA DE RESTAURANTE")
    print("=" * 60)
    print(f"🚀 Servidor iniciado en modo HTTP")
    print(f"   📍 Local:  http://127.0.0.1:5000")
    print(f"   📍 Red:    http://{local_ip}:5000")
    print("=" * 60)
    reloader_config = not is_windows  
    
    print(f" Auto-reload: {'Activado' if reloader_config else 'Desactivado (Windows)'}")
    print("=" * 60 + "\n")
    
    app.run(
        debug=True,
        use_reloader=reloader_config,
        host='0.0.0.0',
        port=5000,
        threaded=True  
    )
"""
Script de inicialización de PostgreSQL para Restaurante Callejón 9

Uso:
    python scripts/init_postgres.py

Requiere que DATABASE_URL esté definido en .env o como variable de entorno.
Crea todas las tablas y siembra un usuario administrador inicial.
"""
import sys
import os

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config.database import db, init_db
from models.sql.usuario import Usuario
from models.sql.menu import Categoria, Platillo
from models.sql.venta import Venta, Cuenta, CorteCaja  # noqa: F401 — needed for db.create_all()


def crear_app():
    app = Flask(__name__)
    init_db(app)
    return app


def crear_tablas(app):
    with app.app_context():
        try:
            db.create_all()
            print("[PostgreSQL] Tablas creadas (o ya existían).")
        except Exception as e:
            print(f"\n[ERROR] No se pudo conectar a PostgreSQL: {e}")
            print("        Verifica que:")
            print("        1. PostgreSQL está corriendo")
            print("        2. La base de datos 'callejon9' existe:")
            print("              psql -U postgres -c \"CREATE DATABASE callejon9;\"")
            print("        3. Las credenciales en DATABASE_URL son correctas")
            raise


def seed_categorias(app):
    """Crea las categorías base del menú si no existen."""
    categorias_base = [
        {"nombre": "Entrada",      "slug": "entrada",      "descripcion": "Entradas y aperitivos"},
        {"nombre": "Plato Fuerte", "slug": "plato_fuerte", "descripcion": "Platos principales"},
        {"nombre": "Bebida",       "slug": "bebida",       "descripcion": "Bebidas y refrescos"},
        {"nombre": "Postre",       "slug": "postre",       "descripcion": "Postres y dulces"},
        {"nombre": "Especial",     "slug": "especial",     "descripcion": "Platillos especiales del día"},
    ]

    with app.app_context():
        creadas = 0
        for cat in categorias_base:
            if not Categoria.find_by_slug(cat["slug"]):
                Categoria.create(cat)
                creadas += 1
        print(f"[PostgreSQL] {creadas} categorías creadas ({len(categorias_base) - creadas} ya existían).")


def seed_admin(app):
    """Crea el usuario administrador inicial si no existe."""
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@callejon9.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    ADMIN_NOMBRE = os.getenv("ADMIN_NOMBRE", "Administrador")
    ADMIN_APELLIDOS = os.getenv("ADMIN_APELLIDOS", "Sistema")

    with app.app_context():
        if Usuario.find_by_email(ADMIN_EMAIL):
            print(f"[PostgreSQL] Admin '{ADMIN_EMAIL}' ya existe, no se crea de nuevo.")
            return

        admin = Usuario.create({
            "usuario_nombre": ADMIN_NOMBRE,
            "usuario_apellidos": ADMIN_APELLIDOS,
            "usuario_email": ADMIN_EMAIL,
            "usuario_clave": ADMIN_PASSWORD,
            "usuario_rol": "1",
            "usuario_status": 1,
            "perfil_extra": {},
        })
        print(f"[PostgreSQL] Admin creado: {admin.usuario_email} / password: {ADMIN_PASSWORD}")
        print("             IMPORTANTE: Cambia la contrasena despues del primer login.")


if __name__ == "__main__":
    app = crear_app()
    print(f"[PostgreSQL] Conectando a: {os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/callejon9')}")
    crear_tablas(app)
    seed_categorias(app)
    seed_admin(app)
    print("[PostgreSQL] Inicialización completa.")

"""
Controlador de Autenticación - Sistema Restaurante Callejón 9
Roles: 1=Admin, 2=Mesero, 3=Cocina, 4=Inventario
Base de datos: PostgreSQL (SQLAlchemy)
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from models.sql.usuario import Usuario
from models.empleado_model import RolPermisos
from controllers.notificaciones.notificacion_controller import NotificacionSistemaController
import secrets
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO)


class AuthController:

    # =====================================================
    # LOGIN
    # =====================================================
    @staticmethod
    def login():
        if request.method == "POST":
            data = request.get_json()

            if not data:
                return jsonify({"status": "error", "message": "Datos inválidos"})

            email = data.get("email", "").strip().lower()
            password = data.get("password", "")

            print(f"\n🔐 Intento de login: {email}")

            if not email or not password:
                return jsonify({"status": "error", "message": "Por favor completa todos los campos"})

            try:
                usuario = Usuario.find_by_email(email)
            except Exception as e:
                print(f"   ❌ Error al buscar usuario: {e}")
                return jsonify({"status": "error", "message": f"Error de base de datos: {str(e)}"})

            if not usuario:
                return jsonify({"status": "error", "message": "Credenciales incorrectas"})

            rol = str(usuario.usuario_rol)
            if rol not in ["1", "2", "3", "4"]:
                return jsonify({"status": "error", "message": "No tienes permisos para acceder al sistema"})

            if usuario.usuario_clave != password:
                return jsonify({"status": "error", "message": "Credenciales incorrectas"})

            # =====================================================
            # LOGIN EXITOSO
            # =====================================================
            token_session = secrets.token_urlsafe(32)
            user_id = str(usuario.id)

            try:
                Usuario.update_session_token(user_id, token_session, 1)
            except Exception as e:
                print(f"⚠️ Error al actualizar token: {e}")

            session["usuario_id"] = user_id
            session["usuario_nombre"] = usuario.usuario_nombre
            session["usuario_apellidos"] = usuario.usuario_apellidos
            session["usuario_email"] = usuario.usuario_email
            session["usuario_rol"] = rol
            session["usuario_foto"] = usuario.usuario_foto or ""
            session["token_session"] = token_session
            session["theme"] = "light"

            permisos = RolPermisos.get_permisos(rol)
            session["permisos"] = permisos

            if rol == "2":
                session["perfil_mesero"] = Usuario.get_perfil_mesero(usuario)
            elif rol == "3":
                session["perfil_cocina"] = Usuario.get_perfil_cocina(usuario)

            try:
                NotificacionSistemaController.notificar_login(
                    usuario_id=user_id,
                    nombre_usuario=usuario.usuario_nombre,
                    rol=rol,
                )
            except Exception as e:
                logging.warning(f"Error notificando login: {e}")

            rol_endpoints = {
                "1": "dashboard_admin",
                "2": "dashboard_mesero",
                "3": "dashboard_cocina",
                "4": "dashboard_inventario",
            }
            endpoint = rol_endpoints.get(rol)

            if endpoint:
                logging.info(f"✅ Login exitoso: {email} | Rol: {RolPermisos.get_nombre_rol(rol)}")
                return jsonify({
                    "status": "success",
                    "dashboard": url_for(f"routes.{endpoint}"),
                    "user": {
                        "nombre": usuario.usuario_nombre,
                        "rol": RolPermisos.get_nombre_rol(rol),
                    },
                })

            return jsonify({"status": "error", "message": "Rol no reconocido"})

        return render_template("login.html")

    # =====================================================
    # LOGOUT
    # =====================================================
    @staticmethod
    def logout():
        usuario_id = session.get("usuario_id")
        usuario_nombre = session.get("usuario_nombre")
        usuario_rol = session.get("usuario_rol")

        if usuario_id:
            try:
                Usuario.update_session_token(usuario_id, None, 0)
                NotificacionSistemaController.notificar_logout(
                    usuario_id=usuario_id,
                    nombre_usuario=usuario_nombre,
                    rol=usuario_rol,
                )
            except Exception as e:
                logging.error(f"Error en logout: {e}")

        session.clear()
        return redirect(url_for("routes.login"))

    # =====================================================
    # 2FA (Deshabilitado)
    # =====================================================
    @staticmethod
    def verify_2fa():
        return jsonify({"status": "error", "message": "2FA no implementado en esta versión"}), 400


# ==========================================================
# DECORADORES
# ==========================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("routes.login"))
        return f(*args, **kwargs)
    return decorated_function


def rol_required(roles_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("routes.login"))
            rol_actual = session.get("usuario_rol")
            if str(rol_actual) not in [str(r) for r in roles_permitidos]:
                flash("No tienes permisos para acceder a esta página", "error")
                return redirect(url_for("routes.login"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permiso_required(permiso):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("routes.login"))
            rol_actual = session.get("usuario_rol")
            if not RolPermisos.tiene_permiso(rol_actual, permiso):
                flash("No tienes permisos para realizar esta acción", "error")
                return redirect(url_for("routes.login"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

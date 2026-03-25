"""
Controlador de Autenticación - Sistema Restaurante Callejón 9
Versión simplificada sin 2FA y sin bcrypt para desarrollo local
Roles: 1=Admin, 2=Mesero, 3=Cocina, 4=Inventario
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from models.empleado_model import Usuario, RolPermisos
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
        """Endpoint de login simplificado para desarrollo local"""

        if request.method == "POST":
            data = request.get_json()

            if not data:
                return jsonify({
                    "status": "error",
                    "message": "Datos inválidos"
                })

            email = data.get("email", "").strip().lower()
            password = data.get("password", "")

            print(f"\n🔐 Intento de login:")
            print(f"   Email: {email}")
            print(f"   Password: {'*' * len(password)}")

            # 1. Validaciones básicas
            if not email or not password:
                return jsonify({
                    "status": "error",
                    "message": "Por favor completa todos los campos"
                })

            # 2. Buscar usuario por email
            try:
                usuario_doc = Usuario.find_by_email(email)
                print(f"   Usuario encontrado: {usuario_doc is not None}")

                if usuario_doc:
                    print(f"   Rol del usuario: {usuario_doc.get('usuario_rol')}")
                    print(f"   Status: {usuario_doc.get('usuario_status')}")

            except Exception as e:
                print(f"   ❌ Error al buscar usuario: {e}")
                return jsonify({
                    "status": "error",
                    "message": f"Error de base de datos: {str(e)}"
                })

            if not usuario_doc:
                return jsonify({
                    "status": "error",
                    "message": "Credenciales incorrectas"
                })

            # 3. Validar rol permitido
            rol = str(usuario_doc.get("usuario_rol", ""))
            if rol not in ["1", "2", "3", "4"]:
                return jsonify({
                    "status": "error",
                    "message": "No tienes permisos para acceder al sistema"
                })

            # 4. Validar contraseña (comparación directa)
            stored_password = usuario_doc.get("usuario_clave", "")

            print(f"   ¿Coinciden?: {stored_password == password}")

            if stored_password != password:
                return jsonify({
                    "status": "error",
                    "message": "Credenciales incorrectas"
                })

            # =====================================================
            # LOGIN EXITOSO
            # =====================================================

            token_session = secrets.token_urlsafe(32)
            user_id = str(usuario_doc["_id"])

            # Actualizar token en BD
            try:
                Usuario.update_session_token(user_id, token_session, 1)
            except Exception as e:
                print(f"⚠️ Error al actualizar token: {e}")

            # Poblar sesión Flask
            session["usuario_id"] = user_id
            session["usuario_nombre"] = usuario_doc.get("usuario_nombre", "")
            session["usuario_apellidos"] = usuario_doc.get("usuario_apellidos", "")
            session["usuario_email"] = usuario_doc.get("usuario_email", "")
            session["usuario_rol"] = rol
            session["usuario_foto"] = usuario_doc.get("usuario_foto", "")
            session["token_session"] = token_session
            session["theme"] = "light"

            # Permisos
            permisos = RolPermisos.get_permisos(rol)
            session["permisos"] = permisos

            # Perfiles específicos
            if rol == "2":
                session["perfil_mesero"] = Usuario.get_perfil_mesero(usuario_doc)
            elif rol == "3":
                session["perfil_cocina"] = Usuario.get_perfil_cocina(usuario_doc)

            # ✨ Notificar Login
            try:
                NotificacionSistemaController.notificar_login(
                    usuario_id=user_id,
                    nombre_usuario=usuario_doc.get("usuario_nombre"),
                    rol=rol
                )
            except Exception as e:
                logging.warning(f"Error notificando login: {e}")

            # Dashboards por rol
            rol_endpoints = {
                "1": "dashboard_admin",
                "2": "dashboard_mesero",
                "3": "dashboard_cocina",
                "4": "dashboard_inventario"
            }

            endpoint = rol_endpoints.get(rol)

            if endpoint:
                logging.info(f"✅ Login exitoso: {email} | Rol: {RolPermisos.get_nombre_rol(rol)}")

                return jsonify({
                    "status": "success",
                    "dashboard": url_for(f"routes.{endpoint}"),
                    "user": {
                        "nombre": usuario_doc.get("usuario_nombre"),
                        "rol": RolPermisos.get_nombre_rol(rol)
                    }
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": "Rol no reconocido"
                })

        # GET → mostrar login
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

                # ✨ Notificar Logout
                NotificacionSistemaController.notificar_logout(
                    usuario_id=usuario_id,
                    nombre_usuario=usuario_nombre,
                    rol=usuario_rol
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
        return jsonify({
            "status": "error",
            "message": "2FA no implementado en esta versión"
        }), 400


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
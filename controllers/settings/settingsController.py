from flask import session, redirect, url_for, render_template, request, jsonify
from models.sql.usuario import Usuario
from services.security.two_factor_service import TwoFactorService
import logging

logging.basicConfig(level=logging.INFO)


class SettingsController:
    """Controlador para configuracion de cuenta — PostgreSQL"""

    @staticmethod
    def settings():
        if "usuario_id" not in session:
            return redirect(url_for('routes.login'))

        user = Usuario.find_by_id(session["usuario_id"])
        if not user:
            return "Usuario no encontrado", 404

        template_map = {
            "1": "admin/config/config.html",
            "2": "mesero/config/config.html",
            "3": "cocina/config/config.html",
            "4": "inventario/config/config.html",
        }
        template = template_map.get(str(session.get("usuario_rol")), "admin/config/config.html")
        return render_template(template, is_2fa_active=user.twofa_enabled)

    # ==========================================
    # DATOS DE USUARIO
    # ==========================================

    @staticmethod
    def get_telefono():
        if "usuario_id" not in session:
            return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

        try:
            user = Usuario.find_by_id(session["usuario_id"])
            return jsonify({
                'status': 'success',
                'telefono': user.usuario_telefono or '' if user else ''
            })
        except Exception as e:
            logging.error(f"Error al obtener telefono: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @staticmethod
    def actualizar_perfil():
        if "usuario_id" not in session:
            return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

        data    = request.json or {}
        user_id = session["usuario_id"]

        update_data = {}
        if 'nombre'    in data: update_data['usuario_nombre']    = data['nombre']
        if 'apellidos' in data: update_data['usuario_apellidos'] = data['apellidos']
        if 'telefono'  in data: update_data['usuario_telefono']  = data['telefono']

        if not update_data:
            return jsonify({'status': 'error', 'message': 'No hay datos para actualizar'}), 400

        try:
            usuario = Usuario.update(user_id, update_data)
            if usuario:
                if 'usuario_nombre'    in update_data: session['usuario_nombre']    = update_data['usuario_nombre']
                if 'usuario_apellidos' in update_data: session['usuario_apellidos'] = update_data['usuario_apellidos']
                return jsonify({'status': 'success', 'message': 'Perfil actualizado correctamente'})
            return jsonify({'status': 'error', 'message': 'No se pudo actualizar'}), 500
        except Exception as e:
            logging.error(f"Error al actualizar perfil: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # ==========================================
    # 2FA
    # ==========================================

    @staticmethod
    def generate_2fa_setup():
        if "usuario_id" not in session:
            return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

        user = Usuario.find_by_id(session["usuario_id"])
        if not user:
            return jsonify({'status': 'error', 'message': 'Usuario no encontrado'}), 404

        tipo = request.json.get('tipo', 'app')

        if tipo == 'app':
            secret_key = TwoFactorService.generar_secret()
            if not user.usuario_email:
                return jsonify({'status': 'error', 'message': 'Email no disponible'}), 400

            qr_base64 = TwoFactorService.generar_qr_code(secret_key, user.usuario_email)
            session['temp_2fa_secret'] = secret_key
            session['temp_2fa_tipo']   = 'app'
            return jsonify({'status': 'success', 'secret_key': secret_key, 'qr_image': qr_base64, 'tipo': 'app'})

        elif tipo == 'email':
            if not user.usuario_email:
                return jsonify({'status': 'error', 'message': 'Email no disponible'}), 400

            email_code = TwoFactorService.generar_codigo_sms()
            session['temp_2fa_secret'] = email_code
            session['temp_2fa_tipo']   = 'email'
            session['temp_2fa_email']  = user.usuario_email
            logging.info(f"Codigo 2FA email: {email_code} -> {user.usuario_email}")
            return jsonify({'status': 'success', 'message': f'Codigo enviado a {user.usuario_email}.', 'tipo': 'email'})

        return jsonify({'status': 'error', 'message': 'Tipo no valido'}), 400

    @staticmethod
    def verify_and_enable_2fa():
        if "usuario_id" not in session:
            return jsonify({'status': 'error', 'message': 'Sesion no valida'}), 401

        data       = request.json or {}
        otp_code   = data.get('otp_code') or data.get('code')
        secret_key = session.get('temp_2fa_secret')
        tipo       = session.get('temp_2fa_tipo')

        if not secret_key or not otp_code or not tipo:
            return jsonify({'status': 'error', 'message': 'Datos faltantes'}), 400

        is_valid       = False
        secret_to_save = None

        if tipo == 'app':
            is_valid = TwoFactorService.verificar_totp(secret_key, otp_code)
            if is_valid:
                secret_to_save = secret_key
        elif tipo == 'email':
            is_valid = str(otp_code) == str(secret_key)

        if not is_valid:
            return jsonify({'status': 'error', 'message': 'Codigo invalido'}), 401

        usuario = Usuario.update_2fa_status(
            user_id=session["usuario_id"],
            is_enabled=True,
            tipo=tipo,
            secret=secret_to_save,
            telefono=None,
        )

        session.pop('temp_2fa_secret', None)
        session.pop('temp_2fa_tipo',   None)
        session.pop('temp_2fa_email',  None)
        session['2fa_enabled'] = True
        session['2fa_tipo']    = tipo

        if usuario:
            return jsonify({'status': 'success', 'message': '2FA activado correctamente'})
        return jsonify({'status': 'error', 'message': 'Error al guardar en BD'}), 500

    @staticmethod
    def disable_2fa():
        if "usuario_id" not in session:
            return jsonify({'status': 'error', 'message': 'No autorizado'}), 401

        usuario = Usuario.update_2fa_status(
            user_id=session["usuario_id"],
            is_enabled=False,
            tipo=None,
            secret=None,
            telefono=None,
        )

        session['2fa_enabled'] = False
        session['2fa_tipo']    = None

        if usuario:
            return jsonify({'status': 'success', 'message': '2FA desactivado'})
        return jsonify({'status': 'error', 'message': 'Error al desactivar'}), 500

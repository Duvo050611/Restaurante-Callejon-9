"""
Módulo de Rutas - Sistema de Restaurante Callejón 9
Roles: 1=Admin, 2=Mesero, 3=Cocina
"""
from flask import Blueprint, render_template, session, redirect, url_for, request
from flask import render_template, session, redirect, url_for, jsonify
from controllers.auth.AuthController import AuthController, login_required, rol_required, permiso_required
from controllers.dashboard.dashboard_controller import DashboardController
from controllers.admin.BackupController import BackupController
from controllers.historial.historialController import HistorialController
from controllers.inventario.inventarioController import InventarioController
from controllers.dashboard.dashboardApiController import DashboardAPIController
from controllers.comanda.comandaController import ComandaController
from controllers.mesa.mesaController import MesaController
from flask import jsonify, request
from controllers.notificaciones.notificacion_controller import NotificacionController
from controllers.propina.propinasController import PropinasController
from controllers.cocina.cocinaController import CocinaController
from models.mesa_model import Mesa
from models.comanda_model import Comanda
from models.producto_model import Producto
from config.db import db
from controllers.settings.settingsController import SettingsController
from controllers.pago.mercadoPagoController import MercadoPagoController

routes_bp = Blueprint("routes", __name__)

# ============================================
#  AUTENTICACIÓN
# ============================================

# Ruta raíz - redirige según estado de sesión
@routes_bp.route("/")
def home():
    return DashboardController.index()

# Login y Logout
routes_bp.add_url_rule("/login", view_func=AuthController.login, methods=["GET", "POST"], endpoint="login")
routes_bp.add_url_rule("/logout", view_func=AuthController.logout, endpoint="logout")
routes_bp.add_url_rule("/verify-2fa", view_func=AuthController.verify_2fa, methods=["POST"], endpoint="verify_2fa")

# ============================================
#  API ENDPOINTS
# ============================================

# API de estadísticas del dashboard
@routes_bp.route('/api/dashboard/admin/stats')
@login_required
@rol_required(['1'])
def api_dashboard_stats():
    """API endpoint para obtener estadísticas reales del dashboard"""
    return DashboardAPIController.get_stats()

@routes_bp.route("/api/dashboard/admin/actividad")
@login_required
@rol_required(['1'])
def api_dashboard_actividad():
    """API endpoint para obtener actividad reciente"""
    return DashboardAPIController.get_actividad_reciente()

@routes_bp.route("/api/dashboard/admin/personal")
@login_required
@rol_required(['1'])
def api_dashboard_personal():
    """API endpoint para obtener personal activo"""
    return DashboardAPIController.get_personal_activo()

@routes_bp.route("/api/empleados/todos")
@login_required
@rol_required(['1'])
def api_empleados_todos():
    """API endpoint para obtener todos los empleados"""
    return DashboardAPIController.get_todos_empleados()

# ============================================
#  API NOTIFICACIONES
# ============================================

# Obtener datos del usuario para Socket.IO
@routes_bp.route('/api/me', methods=['GET'])
@login_required
def api_me():
    """Endpoint para obtener datos del usuario autenticado y token de socket"""
    return NotificacionController.get_datos_socket()

# Obtener todas las notificaciones
@routes_bp.route('/api/notificaciones', methods=['GET'])
@login_required
def api_notificaciones():
    """Obtiene todas las notificaciones del usuario"""
    return NotificacionController.get_notificaciones()

# Obtener solo notificaciones no leídas
@routes_bp.route('/api/notificaciones/no-leidas', methods=['GET'])
@login_required
def api_notificaciones_no_leidas():
    """Obtiene notificaciones no leídas"""
    return NotificacionController.get_notificaciones_no_leidas()

# Contador de notificaciones no leídas
@routes_bp.route('/api/notificaciones/contador', methods=['GET'])
@login_required
def api_notificaciones_contador():
    """Obtiene el número de notificaciones no leídas"""
    return NotificacionController.get_contador()

# Marcar una notificación como leída
@routes_bp.route('/api/notificaciones/<id_notificacion>/leida', methods=['PUT'])
@login_required
def api_notificacion_leida(id_notificacion):
    """Marca una notificación específica como leída"""
    return NotificacionController.marcar_leida(id_notificacion)

# Marcar todas como leídas
@routes_bp.route('/api/notificaciones/marcar-todas-leidas', methods=['POST'])
@login_required
def api_marcar_todas_leidas():
    """Marca todas las notificaciones del usuario como leídas"""
    return NotificacionController.marcar_todas_leidas()

# Eliminar notificación
@routes_bp.route('/api/notificaciones/<id_notificacion>', methods=['DELETE'])
@login_required
def api_eliminar_notificacion(id_notificacion):
    """Elimina una notificación específica"""
    return NotificacionController.eliminar_notificacion(id_notificacion)

# ============================================
#  CONFIGURACIÓN DE CUENTA
# ============================================

# Página de configuración
@routes_bp.route("/settings")
@login_required
def settings():
    """Página de configuración de cuenta"""
    return SettingsController.settings()

# API: Obtener teléfono
@routes_bp.route('/api/usuario/telefono', methods=['GET'])
@login_required
def api_usuario_telefono():
    return SettingsController.get_telefono()

# API: Actualizar perfil
@routes_bp.route('/api/usuario/actualizar', methods=['POST'])
@login_required
def api_usuario_actualizar():
    return SettingsController.actualizar_perfil()

# API: Setup 2FA
@routes_bp.route('/api/2fa/setup', methods=['POST'])
@login_required
def api_2fa_setup():
    return SettingsController.generate_2fa_setup()

# API: Verificar 2FA
@routes_bp.route('/api/2fa/verify', methods=['POST'])
@login_required
def api_2fa_verify():
    return SettingsController.verify_and_enable_2fa()

# API: Desactivar 2FA
@routes_bp.route('/api/2fa/disable', methods=['POST'])
@login_required
def api_2fa_disable():
    return SettingsController.disable_2fa()

# API: Recovery 2FA (emergencia)
@routes_bp.route('/api/2fa/emergency-disable')
def api_2fa_emergency_disable():
    """Deshabilita 2FA para usuarios bloquados (sin login)"""
    email = request.args.get('email', '')
    return AuthController.emergency_disable_2fa(email)

# ============================================
#  PANEL DE ADMINISTRACIÓN (Rol 1)
# ============================================

# Dashboard Principal
@routes_bp.route("/dashboard/admin")
@login_required
@rol_required(['1'])
def dashboard_admin():
    return DashboardController.admin()

# --- Gestión de Empleados ---
@routes_bp.route("/admin/empleados")
@login_required
@rol_required(['1'])
def admin_empleados_lista():
    return DashboardController.empleados_lista()

@routes_bp.route("/admin/empleados/crear", methods=["GET", "POST"])
@login_required
@rol_required(['1'])
def admin_empleados_crear():
    return DashboardController.empleados_crear()

# --- Reportes y Analítica ---
@routes_bp.route("/support/reportes")
@login_required
@rol_required(['1'])
def admin_reportes():
    return DashboardController.reportes()

# ============================================
#  PANEL DE MESERO (Rol 2)
# ============================================

@routes_bp.route("/dashboard/mesero")
@login_required
@rol_required(['2'])
def dashboard_mesero():
    return DashboardController.mesero()

@routes_bp.route("/mesero/mesas")
@login_required
@rol_required(['2'])
def mesero_mesas():
    perfil_mesero = session.get("perfil_mesero")
    if not perfil_mesero:
        return redirect(url_for("routes.login"))

    stats = {
        "mesas_asignadas": perfil_mesero.get("mesas_asignadas", []),
        "comandas_activas": 0,
        "propinas_dia": perfil_mesero.get("propinas", {}).get("acumulada_dia", 0)
    }

    return render_template(
        "mesero/dashboard.html",
        perfil=perfil_mesero,
        stats=stats
    )

@routes_bp.route("/mesero/comandas")
@login_required
@rol_required(['2'])
def mesero_comandas():
    perfil_mesero = session.get("perfil_mesero")
    if not perfil_mesero:
        return redirect(url_for("routes.login"))

    return render_template(
        "mesero/comandas.html",
        perfil=perfil_mesero,
        stats={"mesas_asignadas": perfil_mesero.get("mesas_asignadas", [])}
    )


@routes_bp.route("/mesero/menu")
@login_required
@rol_required(['2'])
def mesero_menu():
    perfil_mesero = session.get("perfil_mesero")
    if not perfil_mesero:
        return redirect(url_for("routes.login"))

    return render_template(
        "mesero/mesero_menu.html",
        perfil=perfil_mesero,
        stats={"mesas_asignadas": perfil_mesero.get("mesas_asignadas", [])}
    )


@routes_bp.route("/mesero/propinas")
@login_required
@rol_required(['2'])
def mesero_propinas():
    perfil_mesero = session.get("perfil_mesero")
    if not perfil_mesero:
        return redirect(url_for("routes.login"))

    return render_template("mesero/mesero_propinas.html", perfil=perfil_mesero)

@routes_bp.route("/api/mesero/propinas/hoy", methods=["GET"])
@login_required
@rol_required(['2'])
def api_propinas_hoy():
    return PropinasController.propinas_hoy()

@routes_bp.route("/mesero/historial")
@login_required
@rol_required(['2'])
def mesero_historial():
    perfil_mesero = session.get("perfil_mesero")
    if not perfil_mesero:
        return redirect(url_for("routes.login"))

    return render_template("mesero/mesero_historial.html", perfil=perfil_mesero)

@routes_bp.route("/api/mesero/historial", methods=["GET"])
@login_required
@rol_required(['2'])
def api_mesero_historial():
    return HistorialController.historial_mesero()

# =========================
# API GENERALES
# =========================

@routes_bp.route("/api/menu", methods=["GET"])
@login_required
@rol_required(['1', '2'])
def api_get_menu():
    productos = Producto.obtener_todo()
    return jsonify({"success": True, "menu": productos})


@routes_bp.route("/api/mesero/estadisticas/dia", methods=["GET"])
@login_required
@rol_required(['2'])
def api_mesero_estadisticas_dia():
    return ComandaController.estadisticas_dia_mesero()


# =========================
# API MESAS
# =========================

@routes_bp.route("/api/mesero/mesas/estado", methods=["GET"])
@login_required
@rol_required(['2'])
def api_mesero_mesas_estado():
    return MesaController.estado_mesas_mesero()


@routes_bp.route("/api/mesero/mesa/<numero>", methods=["GET"])
@login_required
def api_mesero_mesa_detalle(numero):
    return MesaController.detalle_mesa(numero)

# =========================
# API COMANDAS
# =========================

@routes_bp.route("/api/mesero/comandas/activas", methods=["GET"])
@login_required
@rol_required(['2'])
def api_mesero_comandas_activas():
    return ComandaController.comandas_activas()

@routes_bp.route("/api/mesero/cuenta/abrir", methods=["POST"])
@login_required
@rol_required(['2'])
def api_abrir_cuenta():
    return ComandaController.abrir_cuenta()

@routes_bp.route("/api/mesero/comanda/<cuenta_id>/items", methods=["POST"])
@login_required
@rol_required(['2'])
def api_guardar_items_comanda(cuenta_id):
    return ComandaController.guardar_items(cuenta_id)

@routes_bp.route("/api/mesero/cuenta/<cuenta_id>/cerrar", methods=["POST"])
@login_required
@rol_required(['2'])
def api_cerrar_cuenta(cuenta_id):
    return ComandaController.cerrar_cuenta(cuenta_id)

@routes_bp.route("/api/mesero/comandas/cerradas", methods=["GET"])
@login_required
@rol_required(['2'])
def api_comandas_cerradas():
    return ComandaController.comandas_cerradas()


# ============================================
# PANEL DE COCINA (Rol 3)
# ============================================

@routes_bp.route("/dashboard/cocina")
@login_required
@rol_required(['3'])
def dashboard_cocina():
    """Dashboard principal de cocina"""
    return DashboardController.cocina()

@routes_bp.route("/cocina/pedidos")
@login_required
@rol_required(['3'])
def cocina_pedidos():
    """Vista de pedidos pendientes"""
    if "usuario_rol" not in session or str(session["usuario_rol"]) != "3":
        return redirect(url_for("routes.login"))
    
    perfil_cocina = session.get("perfil_cocina", {})
    
    return render_template("cocina/pedidos.html",
                         perfil=perfil_cocina)

@routes_bp.route("/cocina/en-proceso")
@login_required
@rol_required(['3'])
def cocina_en_proceso():
    """Vista de pedidos en preparación"""
    # Placeholder: implementar vista
    return render_template("cocina/en_proceso.html")

@routes_bp.route("/cocina/listos")
@login_required
@rol_required(['3'])
def cocina_listos():
    """Vista de pedidos listos"""
    if "usuario_rol" not in session or str(session["usuario_rol"]) != "3":
        return redirect(url_for("routes.login"))
    
    # Placeholder: implementar vista
    return render_template("cocina/listos.html")

@routes_bp.route("/cocina/inventario")
@login_required
@rol_required(['3'])
def cocina_inventario():
    """Vista de consulta de inventario (solo lectura)"""
    if "usuario_rol" not in session or str(session["usuario_rol"]) != "3":
        return redirect(url_for("routes.login"))
    
    # Placeholder: implementar vista de inventario
    return render_template("cocina/dashboard.html")


# API: Obtener pedidos pendientes
@routes_bp.route("/api/cocina/pedidos/pendientes", methods=["GET"])
@login_required
@rol_required(['1', '3'])  # Admin y Cocina
def api_cocina_pedidos_pendientes():
    """Obtiene todos los pedidos pendientes de preparación"""
    return CocinaController.obtener_pedidos_pendientes()

# API: Obtener pedidos en proceso
@routes_bp.route("/api/cocina/pedidos/en-proceso", methods=["GET"])
@login_required
@rol_required(['1', '3'])
def api_cocina_pedidos_en_proceso():
    """Obtiene pedidos que están siendo preparados"""
    return CocinaController.obtener_pedidos_en_proceso()

# API: Obtener pedidos listos
@routes_bp.route("/api/cocina/pedidos/listos", methods=["GET"])
@login_required
@rol_required(['1', '3'])
def api_cocina_pedidos_listos():
    """Obtiene pedidos listos para servir"""
    return CocinaController.obtener_pedidos_listos()

# API: Iniciar preparación de pedido
@routes_bp.route("/api/cocina/pedido/iniciar", methods=["POST"])
@login_required
@rol_required(['1', '3'])
def api_cocina_iniciar_preparacion():
    """Marca items como en preparación"""
    return CocinaController.iniciar_preparacion()

# API: Marcar pedido como listo
@routes_bp.route("/api/cocina/pedido/listo", methods=["POST"])
@login_required
@rol_required(['1', '3'])
def api_cocina_marcar_listo():
    """Marca items como listos para servir"""
    return CocinaController.marcar_como_listo()

# API: Marcar pedido como entregado (desde mesero)
@routes_bp.route("/api/cocina/pedido/entregado", methods=["POST"])
@login_required
@rol_required(['1', '2', '3'])  # Admin, Mesero y Cocina
def api_cocina_marcar_entregado():
    """Marca items como entregados"""
    return CocinaController.marcar_como_entregado()

# API: Estadísticas de cocina
@routes_bp.route("/api/cocina/estadisticas", methods=["GET"])
@login_required
@rol_required(['1', '3'])
def api_cocina_estadisticas():
    """Obtiene estadísticas de rendimiento de cocina"""
    return CocinaController.obtener_estadisticas_cocina()

# ============================================
#  PANEL DE INVENTARIO (Rol 4)
# ============================================

# Dashboard
@routes_bp.route("/inventario/dashboard")
@login_required
@rol_required(['1', '4'])  # Admin e Inventario
def dashboard_inventario():
    return InventarioController.dashboard()

# --- Gestión de Insumos ---
@routes_bp.route("/inventario/insumos")
@login_required
@rol_required(['1', '4'])
def inventario_insumos():
    return InventarioController.lista_insumos()

@routes_bp.route("/inventario/insumos/crear", methods=["GET", "POST"])
@login_required
@rol_required(['1', '4'])
def inventario_crear_insumo():
    return InventarioController.crear_insumo()

# --- Movimientos ---
@routes_bp.route("/inventario/movimientos/entrada", methods=["GET", "POST"])
@login_required
@rol_required(['1', '4'])
def inventario_registrar_entrada():
    return InventarioController.registrar_entrada()

@routes_bp.route("/inventario/movimientos/salida", methods=["GET", "POST"])
@login_required
@rol_required(['1', '4'])
def inventario_registrar_salida():
    return InventarioController.registrar_salida()

@routes_bp.route("/inventario/movimientos/merma", methods=["GET", "POST"])
@login_required
@rol_required(['1', '4'])
def inventario_registrar_merma():
    return InventarioController.registrar_merma()

@routes_bp.route("/inventario/movimientos/historial")
@login_required
@rol_required(['1', '4'])
def inventario_historial():
    return InventarioController.historial_movimientos()

# --- Alertas ---
@routes_bp.route("/inventario/alertas")
@login_required
@rol_required(['1', '4'])
def inventario_alertas():
    return InventarioController.alertas_stock()

@routes_bp.route("/api/inventario/alertas/resolver", methods=["POST"])
@login_required
@rol_required(['1', '4'])
def inventario_resolver_alerta():
    return InventarioController.resolver_alerta()

# --- Proveedores ---
@routes_bp.route("/inventario/proveedores")
@login_required
@rol_required(['1', '4'])
def inventario_proveedores():
    return InventarioController.lista_proveedores()

@routes_bp.route("/inventario/proveedores/crear", methods=["GET", "POST"])
@login_required
@rol_required(['1', '4'])
def inventario_crear_proveedor():
    return InventarioController.crear_proveedor()

# --- Reportes ---
@routes_bp.route("/inventario/reportes")
@login_required
@rol_required(['1', '4'])
def inventario_reportes():
    return InventarioController.reportes()

# ============================================
#  MÓDULO DE SEGURIDAD Y BACKUP
# ============================================

# Gestión Principal de Respaldos
@routes_bp.route('/admin/backup', methods=['GET'])
@login_required
@rol_required(['1'])
def admin_backup_view():
    return BackupController.index()

# Creación de Respaldo
@routes_bp.route('/admin/backup/create', methods=['POST'])
@login_required
@rol_required(['1'])
def admin_backup_create():
    return BackupController.create()

# Eliminación de Archivo Físico
@routes_bp.route('/admin/backup/delete/<filename>', methods=['GET'])
@login_required
@rol_required(['1'])
def admin_backup_delete(filename):
    return BackupController.delete_file(filename)

# Restauración
@routes_bp.route('/admin/backup/restore', methods=['POST'])
@login_required
@rol_required(['1'])
def admin_backup_restore():
    return BackupController.restore()

# Configuración de Backup Automático
@routes_bp.route('/admin/backup/configure', methods=['POST'])
@login_required
@rol_required(['1'])
def admin_backup_configure():
    return BackupController.configure_auto_backup()

# ============================================
#  MÓDULO DE REPORTES
# ============================================

from controllers.reports.reports_controller import reports_bp

def register_reports_routes(app):
    """Registra las rutas de reportes en la aplicación"""
    app.register_blueprint(reports_bp)

# ============================================
#  FIN DEL MÓDULO DE RUTAS
# ============================================
# ============================================
# 💳 MERCADO PAGO - PAGOS EN LÍNEA
# ============================================

@routes_bp.route("/api/pago/crear/<cuenta_id>", methods=["POST"])
@login_required
@rol_required(['2'])
def crear_pago(cuenta_id):
    """Crea una preferencia de pago en Mercado Pago"""
    from bson import ObjectId
    return MercadoPagoController.crear_preferencia(ObjectId(cuenta_id))

# 🔥 RUTAS DE RESPUESTA DE MERCADO PAGO
@routes_bp.route("/pago/exitoso")
def pago_exitoso():
    """Procesa el pago exitoso y cierra la cuenta"""
    return MercadoPagoController.procesar_pago_exitoso()

@routes_bp.route("/pago/fallido")
def pago_fallido():
    """Procesa un pago fallido"""
    return MercadoPagoController.procesar_pago_fallido()

@routes_bp.route("/pago/pendiente")
def pago_pendiente():
    """Procesa un pago pendiente"""
    return MercadoPagoController.procesar_pago_pendiente()

# 🔥 WEBHOOK DE MERCADO PAGO (IPN)
@routes_bp.route("/api/webhook/mercadopago", methods=["POST"])
def webhook_mercadopago():
    """Recibe notificaciones de estado de pagos de Mercado Pago"""
    return MercadoPagoController.webhook()

@routes_bp.route("/api/pago/verificar", methods=["GET"])
@login_required
@rol_required(['2'])
def verificar_pago():
    """Verifica el estado de un pago consultando Mercado Pago"""
    cuenta_id = request.args.get("cuenta_id")
    
    if not cuenta_id:
        return jsonify({
            "success": False,
            "error": "Falta cuenta_id"
        }), 400
    
    return MercadoPagoController.verificar_pago_mercadopago(cuenta_id)

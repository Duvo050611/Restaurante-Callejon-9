"""
Handler de Comandos - Notificaciones Sistema Restaurante
Gestiona la creación y actualización de notificaciones
"""

from datetime import datetime
from bson import ObjectId
from pytz import timezone
from models.notificacion import Notificacion
from services.notificaciones.notification_service import notificar_usuario

# Zona horaria de Mexico City (CST/CDT)
Mexico_TZ = timezone('America/Mexico_City')

def get_mexico_datetime():
    """Obtiene la fecha y hora actual en zona horaria de Mexico"""
    return datetime.now(Mexico_TZ)


class NotificacionCommandHandler:
    """
    Handler para procesar comandos relacionados con notificaciones
    """

    @staticmethod
    def crear_notificacion(tipo, mensaje, id_usuario, datos_extra=None):
        """
        Crea una nueva notificación en la BD y envía push en tiempo real
        
        Args:
            tipo: Tipo de notificación (LOGIN, LOGOUT, ERROR, BACKUP, etc.)
            mensaje: Mensaje descriptivo
            id_usuario: ID del usuario destinatario
            datos_extra: Datos adicionales opcionales
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            # 1. Crear notificación en BD
            nueva_notif = {
                "tipo": tipo,
                "mensaje": mensaje,
                "id_usuario": ObjectId(id_usuario),
                "leida": False,
                "fecha": get_mexico_datetime(),
                "created_at": get_mexico_datetime(),
                "updated_at": get_mexico_datetime(),
                "datos_extra": datos_extra or {}
            }
            
            result = Notificacion.create(nueva_notif)
            
            # 2. Enviar notificación push en tiempo real
            notificar_usuario(
                user_id=id_usuario,
                evento=tipo,
                mensaje=mensaje,
                datos_extra=datos_extra
            )
            
            return {
                "success": True,
                "id": str(result.inserted_id),
                "mensaje": "Notificación creada y enviada"
            }
            
        except Exception as e:
            print(f"❌ Error creando notificación: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def marcar_como_leida(id_notificacion):
        """
        Marca una notificación como leída
        
        Args:
            id_notificacion: ID de la notificación
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            result = Notificacion.update(
                id_notificacion,
                {"leida": True}
            )
            
            return {
                "success": result.modified_count > 0,
                "mensaje": "Notificación marcada como leída"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def marcar_todas_leidas(id_usuario):
        """
        Marca todas las notificaciones de un usuario como leídas
        
        Args:
            id_usuario: ID del usuario
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            result = Notificacion.marcar_todas_leidas(id_usuario)
            
            return {
                "success": True,
                "modificadas": result.modified_count,
                "mensaje": f"{result.modified_count} notificaciones marcadas como leídas"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def eliminar_notificacion(id_notificacion):
        """
        Elimina una notificación
        
        Args:
            id_notificacion: ID de la notificación
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            result = Notificacion.delete(id_notificacion)
            
            return {
                "success": result.deleted_count > 0,
                "mensaje": "Notificación eliminada"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class NotificacionSistemaHandler:
    """
    Handler especializado para notificaciones del sistema según rol
    """

    # Tipos de notificaciones por rol
    TIPOS_ADMIN = {
        "LOGIN": " Inicio de Sesión",
        "LOGOUT": " Cierre de Sesión",
        "ERROR_SISTEMA": " Error del Sistema",
        "BACKUP_CREADO": " Backup Creado",
        "BACKUP_RESTAURADO": " Backup Restaurado",
        "EMPLEADO_CREADO": " Nuevo Empleado",
        "EMPLEADO_ELIMINADO": " Empleado Eliminado",
        "ALERTA_INVENTARIO": " Alerta de Inventario"
    }

    TIPOS_MESERO = {
        "LOGIN": " Inicio de Sesión",
        "LOGOUT": " Cierre de Sesión",
        "PEDIDO_ASIGNADO": " Nuevo Pedido",
        "PEDIDO_LISTO": " Pedido Listo",
        "MESA_ASIGNADA": " Mesa Asignada",
        "PROPINA_RECIBIDA": "Propina Recibida"
    }

    TIPOS_COCINA = {
        "LOGIN": " Inicio de Sesión",
        "LOGOUT": " Cierre de Sesión",
        "PEDIDO_NUEVO": " Nuevo Pedido",
        "PEDIDO_URGENTE": " Pedido Urgente",
        "INGREDIENTE_FALTANTE": " Ingrediente Faltante"
    }

    TIPOS_INVENTARIO = {
        "LOGIN": " Inicio de Sesión",
        "LOGOUT": " Cierre de Sesión",
        "STOCK_BAJO": " Stock Bajo",
        "ENTRADA_REGISTRADA": " Entrada Registrada",
        "SALIDA_REGISTRADA": " Salida Registrada",
        "MERMA_REGISTRADA": " Merma Registrada"
    }

    @classmethod
    def notificar_login(cls, id_usuario, nombre_usuario, rol):
        """Notifica inicio de sesión a los administradores"""
        from models.empleado_model import Usuario
        
        mensaje = f" {nombre_usuario} ha iniciado sesión"
        
        # Obtener todos los administradores activos
        admins = Usuario.find_by_rol("1")
        
        # Filtrar solo admins activos
        admins_activos = [admin for admin in admins if admin.get("usuario_status") == 1]
        
        resultados = []
        for admin in admins_activos:
            resultado = NotificacionCommandHandler.crear_notificacion(
                tipo="LOGIN",
                mensaje=mensaje,
                id_usuario=str(admin["_id"]),
                datos_extra={
                    "rol": rol,
                    "usuario_id": id_usuario,
                    "nombre_usuario": nombre_usuario,
                    "timestamp": get_mexico_datetime().isoformat()
                }
            )
            resultados.append(resultado)
        
        return {
            "success": any(r.get("success") for r in resultados),
            "notificaciones_enviadas": len(resultados)
        }

    @classmethod
    def notificar_logout(cls, id_usuario, nombre_usuario, rol):
        """Notifica cierre de sesión a los administradores"""
        from models.empleado_model import Usuario
        
        mensaje = f"🚪 {nombre_usuario} ha cerrado sesión"
        
        # Obtener todos los administradores activos
        admins = Usuario.find_by_rol("1")
        
        # Filtrar solo admins activos
        admins_activos = [admin for admin in admins if admin.get("usuario_status") == 1]
        
        resultados = []
        for admin in admins_activos:
            resultado = NotificacionCommandHandler.crear_notificacion(
                tipo="LOGOUT",
                mensaje=mensaje,
                id_usuario=str(admin["_id"]),
                datos_extra={
                    "rol": rol,
                    "usuario_id": id_usuario,
                    "nombre_usuario": nombre_usuario,
                    "timestamp": get_mexico_datetime().isoformat()
                }
            )
            resultados.append(resultado)
        
        return {
            "success": any(r.get("success") for r in resultados),
            "notificaciones_enviadas": len(resultados)
        }

    @classmethod
    def notificar_error(cls, id_usuario, tipo_error, descripcion):
        """Notifica un error del sistema"""
        mensaje = f"Error: {descripcion}"
        
        return NotificacionCommandHandler.crear_notificacion(
            tipo="ERROR_SISTEMA",
            mensaje=mensaje,
            id_usuario=id_usuario,
            datos_extra={
                "tipo_error": tipo_error,
                "timestamp": get_mexico_datetime().isoformat()
            }
        )

    @classmethod
    def notificar_backup(cls, id_usuario, tipo_backup, nombre_archivo):
        """Notifica operaciones de backup"""
        tipo = "BACKUP_CREADO" if tipo_backup == "crear" else "BACKUP_RESTAURADO"
        mensaje = f"Backup {tipo_backup}: {nombre_archivo}"
        
        return NotificacionCommandHandler.crear_notificacion(
            tipo=tipo,
            mensaje=mensaje,
            id_usuario=id_usuario,
            datos_extra={
                "archivo": nombre_archivo,
                "timestamp": get_mexico_datetime().isoformat()
            }
        )

    @classmethod
    def notificar_empleado(cls, id_admin, accion, nombre_empleado):
        """Notifica acciones sobre empleados (solo admin)"""
        tipo = "EMPLEADO_CREADO" if accion == "crear" else "EMPLEADO_ELIMINADO"
        mensaje = f"Empleado {accion}: {nombre_empleado}"
        
        return NotificacionCommandHandler.crear_notificacion(
            tipo=tipo,
            mensaje=mensaje,
            id_usuario=id_admin,
            datos_extra={
                "empleado": nombre_empleado,
                "timestamp": get_mexico_datetime().isoformat()
            }
        )

    @classmethod
    def notificar_inventario(cls, id_usuario, tipo_movimiento, nombre_insumo, cantidad):
        """Notifica movimientos de inventario"""
        tipos = {
            "entrada": "ENTRADA_REGISTRADA",
            "salida": "SALIDA_REGISTRADA",
            "merma": "MERMA_REGISTRADA",
            "stock_bajo": "STOCK_BAJO"
        }
        
        tipo = tipos.get(tipo_movimiento, "STOCK_BAJO")
        mensaje = f"{tipo_movimiento.title()}: {nombre_insumo} - {cantidad} unidades"
        
        return NotificacionCommandHandler.crear_notificacion(
            tipo=tipo,
            mensaje=mensaje,
            id_usuario=id_usuario,
            datos_extra={
                "insumo": nombre_insumo,
                "cantidad": cantidad,
                "timestamp": get_mexico_datetime().isoformat()
            }
        )
        
        @staticmethod
        def notificar_pedido_listo(mesero_id, comanda_id, mesa_numero):
            """
            Notifica al mesero que su pedido está listo para servir
            
            Args:
                mesero_id (str): ID del mesero
                comanda_id (str): ID de la comanda
                mesa_numero (int): Número de mesa
            
            Returns:
                dict: Resultado de la operación
            """
            try:
                notificacion = {
                    "id_usuario": ObjectId(mesero_id),
                    "tipo": "pedido_listo",
                    "titulo": f"✅ Pedido Listo - Mesa {mesa_numero}",
                    "mensaje": f"Tu pedido para la mesa {mesa_numero} está listo para servir",
                    "leida": False,
                    "fecha": datetime.utcnow(),
                    "datos": {
                        "comanda_id": comanda_id,
                        "mesa": mesa_numero,
                        "accion_requerida": True
                    }
                }
                
                result = db.notificaciones.insert_one(notificacion)
                
                return {
                    "success": True,
                    "notificacion_id": str(result.inserted_id),
                    "message": "Notificación enviada al mesero"
                }
                
            except Exception as e:
                print(f"❌ Error al notificar pedido listo: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }

    @staticmethod
    def notificar_nuevo_pedido_cocina(usuarios_cocina_ids, comanda_id, mesa_numero, num_items):
        """
        Notifica a cocina sobre un nuevo pedido
        
        Args:
            usuarios_cocina_ids (list): Lista de IDs de usuarios de cocina
            comanda_id (str): ID de la comanda
            mesa_numero (int): Número de mesa
            num_items (int): Número de items en el pedido
        
        Returns:
            dict: Resultado de la operación
        """
        try:
            notificaciones = []
            
            for usuario_id in usuarios_cocina_ids:
                notificacion = {
                    "id_usuario": ObjectId(usuario_id),
                    "tipo": "nuevo_pedido",
                    "titulo": f"🍽️ Nuevo Pedido - Mesa {mesa_numero}",
                    "mensaje": f"{num_items} platillo(s) para preparar",
                    "leida": False,
                    "fecha": datetime.utcnow(),
                    "datos": {
                        "comanda_id": comanda_id,
                        "mesa": mesa_numero,
                        "num_items": num_items,
                        "accion_requerida": True
                    }
                }
                notificaciones.append(notificacion)
            
            if notificaciones:
                result = db.notificaciones.insert_many(notificaciones)
                return {
                    "success": True,
                    "notificaciones_enviadas": len(result.inserted_ids),
                    "message": "Notificaciones enviadas a cocina"
                }
            
            return {
                "success": False,
                "error": "No hay usuarios de cocina para notificar"
            }
            
        except Exception as e:
            print(f"❌ Error al notificar nuevo pedido a cocina: {e}")
            return {
                "success": False,
                "error": str(e)
            }

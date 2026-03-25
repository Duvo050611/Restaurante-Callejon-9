"""
API Controller para Dashboard de Administración
Usuarios: PostgreSQL | Operaciones (mesas, comandas, ventas): MongoDB
"""
from flask import jsonify, session, request
from config.db import db as mongo_db
from models.sql.usuario import Usuario
from datetime import datetime


class DashboardAPIController:

    # ==============================
    # KPIs GENERALES
    # ==============================

    @staticmethod
    def get_stats():
        if session.get("usuario_rol") != "1":
            return jsonify({"error": "No autorizado"}), 403

        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Usuarios — PostgreSQL
        total_empleados   = Usuario.query.filter(Usuario.usuario_rol.in_(["1","2","3","4"])).count()
        empleados_activos = Usuario.query.filter(
            Usuario.usuario_rol.in_(["1","2","3","4"]),
            Usuario.usuario_status == 1
        ).count()
        total_admin      = Usuario.count_by_rol("1")
        total_meseros    = Usuario.count_by_rol("2")
        total_cocina     = Usuario.count_by_rol("3")
        total_inventario = Usuario.count_by_rol("4")

        # Operaciones — MongoDB
        ventas_dia       = 0
        mesas_ocupadas   = 0
        comandas_activas = 0
        en_cocina        = 0

        try:
            cols = mongo_db.list_collection_names()
            if "ventas" in cols:
                res = list(mongo_db.ventas.aggregate([
                    {"$match": {"fecha": {"$gte": hoy_inicio}}},
                    {"$group": {"_id": None, "total": {"$sum": "$total"}}}
                ]))
                ventas_dia = float(res[0]["total"]) if res else 0
            if "mesas" in cols:
                mesas_ocupadas = mongo_db.mesas.count_documents({"estado": "ocupada"})
            if "comandas" in cols:
                comandas_activas = mongo_db.comandas.count_documents(
                    {"estado": {"$in": ["nueva", "en_cocina", "preparando"]}}
                )
                en_cocina = mongo_db.comandas.count_documents({"estado": "en_cocina"})
        except Exception:
            pass

        return jsonify({
            "total_empleados":   total_empleados,
            "empleados_activos": empleados_activos,
            "total_admin":       total_admin,
            "total_meseros":     total_meseros,
            "total_cocina":      total_cocina,
            "total_inventario":  total_inventario,
            "mesas_ocupadas":    mesas_ocupadas,
            "comandas_activas":  comandas_activas,
            "ventas_dia":        ventas_dia,
            "en_cocina":         en_cocina,
        })

    # ==============================
    # PERSONAL ACTIVO (CONECTADO)
    # ==============================

    @staticmethod
    def get_personal_activo():
        if session.get("usuario_rol") != "1":
            return jsonify({"error": "No autorizado"}), 403

        personal = Usuario.query.filter(
            Usuario.usuario_rol.in_(["1","2","3","4"]),
            Usuario.fecha_conexion.isnot(None)
        ).order_by(Usuario.usuario_nombre).all()

        ahora = datetime.utcnow()
        resultado = []

        for p in personal:
            tiempo_conectado = ""
            if p.fecha_conexion:
                delta = ahora - p.fecha_conexion
                if delta.days > 0:
                    tiempo_conectado = f"{delta.days}d {delta.seconds // 3600}h"
                elif delta.seconds >= 3600:
                    tiempo_conectado = f"{delta.seconds // 3600}h {(delta.seconds % 3600) // 60}m"
                elif delta.seconds >= 60:
                    tiempo_conectado = f"{delta.seconds // 60}m"
                else:
                    tiempo_conectado = f"{delta.seconds}s"

            resultado.append({
                "nombre":           f"{p.usuario_nombre} {p.usuario_apellidos}".strip(),
                "rol":              p.usuario_rol,
                "email":            p.usuario_email,
                "tiempo_conectado": tiempo_conectado,
                "fecha_conexion":   p.fecha_conexion.isoformat() if p.fecha_conexion else None,
            })

        return jsonify(resultado)

    # ==============================
    # TODOS LOS EMPLEADOS
    # ==============================

    @staticmethod
    def get_todos_empleados():
        if session.get("usuario_rol") != "1":
            return jsonify({"error": "No autorizado"}), 403

        empleados = Usuario.query.filter(
            Usuario.usuario_rol.in_(["1","2","3","4"])
        ).order_by(Usuario.usuario_nombre).all()

        return jsonify({
            "success": True,
            "data": [
                {
                    "id":     str(e.id),
                    "nombre": f"{e.usuario_nombre} {e.usuario_apellidos}".strip(),
                    "email":  e.usuario_email,
                    "rol":    e.usuario_rol,
                    "status": e.usuario_status,
                }
                for e in empleados
            ],
        })

    # ==============================
    # ACTIVIDAD RECIENTE (MongoDB — log operacional)
    # ==============================

    @staticmethod
    def get_actividad_reciente():
        if session.get("usuario_rol") != "1":
            return jsonify([])

        try:
            actividades = list(
                mongo_db.actividad_reciente.find().sort("timestamp", -1).limit(10)
            )
            for a in actividades:
                a["_id"] = str(a["_id"])
                if isinstance(a.get("timestamp"), datetime):
                    a["timestamp"] = a["timestamp"].isoformat()
            return jsonify(actividades)
        except Exception:
            return jsonify([])

    # ==============================
    # DETALLE DE EMPLEADO
    # ==============================

    @staticmethod
    def get_empleado_detalle(empleado_id):
        if session.get("usuario_rol") != "1":
            return jsonify({"success": False, "error": "No autorizado"}), 403

        try:
            empleado = Usuario.find_by_id(empleado_id)
            if not empleado:
                return jsonify({"success": False, "error": "Empleado no encontrado"}), 404

            rol_nombres = {"1": "Administrador", "2": "Mesero", "3": "Cocina", "4": "Inventario"}

            return jsonify({
                "success": True,
                "empleado": {
                    "id":                str(empleado.id),
                    "usuario_nombre":    empleado.usuario_nombre,
                    "usuario_apellidos": empleado.usuario_apellidos,
                    "usuario_email":     empleado.usuario_email,
                    "usuario_telefono":  empleado.usuario_telefono or "",
                    "rol":               empleado.usuario_rol,
                    "rol_nombre":        rol_nombres.get(empleado.usuario_rol, "Usuario"),
                    "usuario_status":    empleado.usuario_status,
                },
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ==============================
    # ELIMINAR EMPLEADO
    # ==============================

    @staticmethod
    def eliminar_empleado(empleado_id):
        if session.get("usuario_rol") != "1":
            return jsonify({"success": False, "error": "No autorizado"}), 403

        try:
            empleado = Usuario.find_by_id(empleado_id)
            if not empleado:
                return jsonify({"success": False, "error": "Empleado no encontrado"}), 404

            if empleado.usuario_rol == "1":
                return jsonify({"success": False, "error": "No se puede eliminar administradores"}), 400

            from config.database import db as pg_db
            pg_db.session.delete(empleado)
            pg_db.session.commit()
            return jsonify({"success": True, "message": "Empleado eliminado correctamente"})

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ==============================
    # ACTUALIZAR EMPLEADO
    # ==============================

    @staticmethod
    def actualizar_empleado(empleado_id):
        if session.get("usuario_rol") != "1":
            return jsonify({"success": False, "error": "No autorizado"}), 403

        try:
            data = request.get_json()
            empleado = Usuario.find_by_id(empleado_id)
            if not empleado:
                return jsonify({"success": False, "error": "Empleado no encontrado"}), 404

            update_data = {}
            if "nombre"    in data: update_data["usuario_nombre"]    = data["nombre"]
            if "apellidos" in data: update_data["usuario_apellidos"] = data["apellidos"]
            if "email"     in data: update_data["usuario_email"]     = data["email"]
            if "telefono"  in data: update_data["usuario_telefono"]  = data["telefono"]
            if "rol"       in data: update_data["usuario_rol"]       = data["rol"]
            if "status"    in data: update_data["usuario_status"]    = int(data["status"])
            if data.get("password"):
                update_data["usuario_clave"] = data["password"]

            if update_data:
                Usuario.update(empleado_id, update_data)

            return jsonify({"success": True, "message": "Empleado actualizado correctamente"})

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ==============================
    # DESCONECTAR USUARIO
    # ==============================

    @staticmethod
    def desconectar_usuario(empleado_id):
        if session.get("usuario_rol") != "1":
            return jsonify({"success": False, "error": "No autorizado"}), 403

        try:
            Usuario.update_session_token(empleado_id, None, 0)
            return jsonify({"success": True, "message": "Usuario desconectado correctamente"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

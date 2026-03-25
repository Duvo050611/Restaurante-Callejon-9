"""
Dashboard Controller - Sistema Restaurante Callejón 9
Admin: PostgreSQL (SQLAlchemy) | Otros módulos: MongoDB
"""
from flask import request, session, redirect, url_for, render_template, jsonify
from controllers.inventario.inventarioController import InventarioController
from models.sql.usuario import Usuario
from models.empleado_model import RolPermisos
from config.db import db as mongo_db
from datetime import datetime


class DashboardController:

    @staticmethod
    def home():
        return render_template("login.html")

    @staticmethod
    def index():
        if "usuario_rol" not in session:
            return redirect(url_for("routes.login"))

        rol = str(session["usuario_rol"])
        rol_endpoints = {
            "1": "dashboard_admin",
            "2": "dashboard_mesero",
            "3": "dashboard_cocina",
            "4": "dashboard_inventario",
        }
        endpoint = rol_endpoints.get(rol)
        if endpoint:
            return redirect(url_for(f"routes.{endpoint}"))
        return "⚠ Rol no reconocido", 403

    # ==========================================
    # DASHBOARDS POR ROL
    # ==========================================

    @staticmethod
    def admin():
        """Dashboard principal de Administración (Rol 1) — PostgreSQL"""
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "1":
            return redirect(url_for("routes.login"))

        stats = {
            "total_usuarios": Usuario.count_activos(),
            "total_admin": Usuario.count_by_rol("1"),
            "total_meseros": Usuario.count_by_rol("2"),
            "total_cocina": Usuario.count_by_rol("3"),
            "total_inventario": Usuario.count_by_rol("4"),
        }

        return render_template(
            "admin/dashboard.html",
            usuario=session.get("usuario_nombre"),
            rol_nombre=RolPermisos.get_nombre_rol("1"),
            stats=stats,
        )

    @staticmethod
    def mesero():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "2":
            return redirect(url_for("routes.login"))

        perfil_mesero = session.get("perfil_mesero", {})
        stats = {
            "mesas_asignadas": perfil_mesero.get("mesas_asignadas", []),
            "comandas_activas": 0,
            "propinas_dia": perfil_mesero.get("propinas", {}).get("acumulada_dia", 0),
            "ventas_promedio": perfil_mesero.get("rendimiento", {}).get("ventas_promedio_dia", 0),
        }
        return render_template(
            "mesero/dashboard.html",
            usuario=session.get("usuario_nombre"),
            rol_nombre=RolPermisos.get_nombre_rol("2"),
            perfil=perfil_mesero,
            comandas=[],
            stats=stats,
        )

    @staticmethod
    def cocina():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "3":
            return redirect(url_for("routes.login"))

        perfil_cocina = session.get("perfil_cocina", {})
        stats = {
            "area": perfil_cocina.get("area", "general"),
            "turno": perfil_cocina.get("turno", ""),
            "platillos_pendientes": 0,
            "especialidad": perfil_cocina.get("especialidad", []),
        }
        return render_template(
            "cocina/dashboard.html",
            usuario=session.get("usuario_nombre"),
            rol_nombre=RolPermisos.get_nombre_rol("3"),
            perfil=perfil_cocina,
            comandas=[],
            stats=stats,
        )

    @staticmethod
    def inventario():
        rol = str(session.get("usuario_rol", ""))
        if rol not in ["1", "3", "4"]:
            return redirect(url_for("routes.login"))
        return InventarioController.dashboard()

    # ==========================================
    # GESTIÓN DE EMPLEADOS (PostgreSQL)
    # ==========================================

    @staticmethod
    def empleados_lista():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "1":
            return redirect(url_for("routes.login"))

        empleados_raw = Usuario.find_all()
        empleados = []
        for emp in empleados_raw:
            d = emp.to_dict()
            d["rol_nombre"] = RolPermisos.get_nombre_rol(emp.usuario_rol)
            empleados.append(d)

        return render_template("admin/empleados/lista.html", empleados=empleados)

    @staticmethod
    def empleados_crear():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "1":
            return redirect(url_for("routes.login"))

        if request.method == "POST":
            try:
                data = request.get_json()

                for field in ("nombre", "apellidos", "email", "password", "rol"):
                    if not data.get(field):
                        return jsonify({"success": False, "message": f"El campo '{field}' es obligatorio"}), 400

                if Usuario.find_by_email(data["email"]):
                    return jsonify({"success": False, "message": "Ya existe un empleado con este correo"}), 400

                if data["rol"] not in ["1", "2", "3", "4"]:
                    return jsonify({"success": False, "message": "Rol no válido"}), 400

                perfil_extra = {}
                if data["rol"] == "2":  # Mesero
                    perfil_extra = {
                        "mesero_numero": data.get("numero_empleado", ""),
                        "mesero_turno": data.get("turno", ""),
                        "mesero_mesas": data.get("mesas_asignadas", []),
                        "mesero_puede_cerrar_cuenta": data.get("puede_cerrar_cuenta", False),
                        "mesero_puede_aplicar_descuento": data.get("puede_aplicar_descuento", False),
                        "mesero_propina_sugerida": 10,
                        "mesero_propina_acumulada_dia": 0,
                        "mesero_ventas_promedio_dia": 0,
                        "mesero_calificacion_cliente": 0,
                    }
                elif data["rol"] == "3":  # Cocina
                    perfil_extra = {
                        "cocina_numero": data.get("numero_empleado", ""),
                        "cocina_puesto": data.get("puesto", ""),
                        "cocina_area": data.get("area", "general"),
                        "cocina_turno": data.get("turno", ""),
                        "cocina_especialidad": data.get("especialidad", []),
                        "cocina_puede_modificar_menu": data.get("puede_modificar_menu", False),
                        "cocina_puede_ver_recetas_completas": data.get("puede_ver_recetas", False),
                        "cocina_certificaciones": data.get("certificaciones", []),
                    }
                elif data["rol"] == "4":  # Inventario
                    perfil_extra = {
                        "inventario_numero": data.get("numero_empleado", ""),
                        "inventario_area": data.get("area", ""),
                        "inventario_turno": data.get("turno", ""),
                        "inventario_puede_gestionar_proveedores": data.get("puede_gestionar_proveedores", False),
                        "inventario_puede_realizar_auditorias": data.get("puede_realizar_auditorias", False),
                    }

                nuevo = Usuario.create({
                    "usuario_nombre": data["nombre"],
                    "usuario_apellidos": data["apellidos"],
                    "usuario_email": data["email"].lower(),
                    "usuario_clave": data["password"],
                    "usuario_rol": data["rol"],
                    "usuario_telefono": data.get("telefono", ""),
                    "usuario_foto": None,
                    "usuario_status": 1,
                    "perfil_extra": perfil_extra,
                })

                return jsonify({"success": True, "message": "Empleado creado exitosamente", "id": str(nuevo.id)})

            except Exception as e:
                print(f"Error al crear empleado: {e}")
                return jsonify({"success": False, "message": "Error al crear empleado"}), 500

        return render_template("admin/empleados/crear.html")

    @staticmethod
    def empleados_editar(empleado_id):
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "1":
            return redirect(url_for("routes.login"))

        try:
            empleado = Usuario.find_by_id(empleado_id)
            if not empleado:
                return "Empleado no encontrado", 404

            emp_dict = empleado.to_dict()
            emp_dict["rol_nombre"] = RolPermisos.get_nombre_rol(empleado.usuario_rol)

            if request.method == "POST":
                data = request.get_json()
                update_data = {}

                if "nombre" in data:
                    update_data["usuario_nombre"] = data["nombre"]
                if "apellidos" in data:
                    update_data["usuario_apellidos"] = data["apellidos"]
                if "email" in data:
                    update_data["usuario_email"] = data["email"].lower()
                if "telefono" in data:
                    update_data["usuario_telefono"] = data["telefono"]
                if "rol" in data:
                    if data["rol"] not in ["1", "2", "3", "4"]:
                        return jsonify({"success": False, "message": "Rol no válido"}), 400
                    update_data["usuario_rol"] = data["rol"]
                if "status" in data:
                    update_data["usuario_status"] = int(data["status"])
                if "password" in data and data["password"]:
                    update_data["usuario_clave"] = data["password"]

                Usuario.update(empleado_id, update_data)
                return jsonify({"success": True, "message": "Empleado actualizado correctamente"})

            return render_template("admin/empleados/editar.html", empleado=emp_dict)

        except Exception as e:
            print(f"Error al editar empleado: {e}")
            return jsonify({"success": False, "message": "Error al editar empleado"}), 500

    # ==========================================
    # ESTADÍSTICAS DEL DASHBOARD (API)
    # ==========================================

    @staticmethod
    def get_dashboard_stats():
        """Estadísticas mixtas: usuarios desde PostgreSQL, operaciones desde MongoDB"""
        try:
            # Usuarios — PostgreSQL
            total_empleados = Usuario.query.filter(
                Usuario.usuario_rol.in_(["1", "2", "3", "4"])
            ).count()
            empleados_activos = Usuario.query.filter(
                Usuario.usuario_rol.in_(["1", "2", "3", "4"]),
                Usuario.usuario_status == 1,
            ).count()
            admin_count = Usuario.count_by_rol("1")
            meseros_count = Usuario.count_by_rol("2")
            cocina_count = Usuario.count_by_rol("3")
            inventario_count = Usuario.count_by_rol("4")

            # Operaciones — MongoDB (resto del sistema)
            mesas_ocupadas = 0
            comandas_activas = 0
            en_cocina = 0
            ventas_dia = 0
            cuentas_abiertas = 0
            platillos_disponibles = 0

            try:
                collections = mongo_db.list_collection_names()

                if "mesas" in collections:
                    mesas_ocupadas = mongo_db.mesas.count_documents({"estado": "ocupada"})

                if "comandas" in collections:
                    comandas_activas = mongo_db.comandas.count_documents(
                        {"estado": {"$in": ["nueva", "enviada", "preparacion"]}}
                    )
                    en_cocina = mongo_db.comandas.count_documents(
                        {"estado": {"$in": ["enviada", "preparacion"]}}
                    )

                if "ventas" in collections:
                    hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    resultado = list(mongo_db.ventas.aggregate([
                        {"$match": {"fecha": {"$gte": hoy_inicio}, "estado": {"$ne": "cancelada"}}},
                        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
                    ]))
                    if resultado:
                        ventas_dia = resultado[0].get("total", 0)

                if "cuentas" in collections:
                    cuentas_abiertas = mongo_db.cuentas.count_documents(
                        {"estado": {"$in": ["abierta", "activa"]}}
                    )

                if "platillos" in collections:
                    platillos_disponibles = mongo_db.platillos.count_documents({"disponible": True})

            except Exception:
                pass

            return jsonify({
                "success": True,
                "data": {
                    "total_empleados": total_empleados,
                    "empleados_activos": empleados_activos,
                    "admin_count": admin_count,
                    "meseros_count": meseros_count,
                    "cocina_count": cocina_count,
                    "inventario_count": inventario_count,
                    "mesas_ocupadas": mesas_ocupadas,
                    "comandas_activas": comandas_activas,
                    "en_cocina": en_cocina,
                    "ventas_dia": float(ventas_dia),
                    "cuentas_abiertas": cuentas_abiertas,
                    "platillos_disponibles": platillos_disponibles,
                    "timestamp": datetime.now().isoformat(),
                },
            })

        except Exception as e:
            print(f"Error en get_dashboard_stats: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @staticmethod
    def reportes():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "1":
            return redirect(url_for("routes.login"))
        return render_template("support/reportes/   index.html")

    @staticmethod
    def toggle_theme():
        try:
            current_theme = session.get("theme", "light")
            session["theme"] = "dark" if current_theme == "light" else "light"
        except Exception as e:
            print(f"Error al cambiar tema: {e}")
        return redirect(request.referrer or url_for("routes.login"))

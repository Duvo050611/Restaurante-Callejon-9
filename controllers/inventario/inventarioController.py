"""
Dashboard Controller - Inventario
Rol 4: Encargado de Inventario/Almacén
"""
from flask import request, session, redirect, url_for, render_template, jsonify
from models.inventario_model import (
    Insumo, MovimientoInventario, Proveedor, AlertaStock,
    TipoMovimiento, UnidadMedida, CategoriaInsumo
)
from bson.objectid import ObjectId
from datetime import datetime
from controllers.notificaciones.notificacion_controller import NotificacionSistemaController
import logging

logging.basicConfig(level=logging.INFO)


class InventarioController:

    # ==========================================
    # DASHBOARD
    # ==========================================
    @staticmethod
    def dashboard():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "4":
            return redirect(url_for("routes.login"))

        try:
            total_insumos = len(Insumo.obtener_todos())
            insumos_criticos = Insumo.obtener_stock_critico()
            alertas_activas = AlertaStock.obtener_alertas_activas()

            hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            movimientos_hoy = MovimientoInventario.obtener_historial(
                {"fecha": {"$gte": hoy_inicio}},
                limit=10
            )

            insumos = Insumo.obtener_todos()
            valor_total = sum(
                i.get("stock_actual", 0) * i.get("costo_unitario", 0)
                for i in insumos
            )

            stats = {
                "total_insumos": total_insumos,
                "stock_critico": len(insumos_criticos),
                "alertas_activas": len(alertas_activas),
                "valor_inventario": valor_total,
                "movimientos_hoy": len(movimientos_hoy)
            }

            return render_template(
                "inventario/dashboard.html",
                usuario=session.get("usuario_nombre"),
                stats=stats,
                alertas=alertas_activas[:5],
                movimientos_recientes=movimientos_hoy[:5]
            )

        except Exception as e:
            logging.error(f"Error en dashboard: {e}")
            return str(e), 500

    # ==========================================
    # INSUMOS
    # ==========================================
    @staticmethod
    def lista_insumos():
        if "usuario_rol" not in session or str(session["usuario_rol"]) not in ["1", "4"]:
            return redirect(url_for("routes.login"))

        try:
            categoria = request.args.get("categoria")
            filtros = {"activo": True}

            if categoria and categoria != "todas":
                filtros["categoria"] = categoria

            insumos = Insumo.obtener_todos(filtros)

            for insumo in insumos:
                stock = insumo.get("stock_actual", 0)
                minimo = insumo.get("stock_minimo", 0)

                if stock == 0:
                    insumo["estado_stock"] = "agotado"
                elif stock <= minimo:
                    insumo["estado_stock"] = "critico"
                elif stock <= minimo * 1.5:
                    insumo["estado_stock"] = "bajo"
                else:
                    insumo["estado_stock"] = "normal"

            categorias = [cat.value for cat in CategoriaInsumo]

            return render_template(
                "inventario/insumos/lista.html",
                insumos=insumos,
                categorias=categorias,
                categoria_seleccionada=categoria
            )

        except Exception as e:
            logging.error(f"Error insumos: {e}")
            return render_template("inventario/insumos/lista.html", error=str(e))

    # ==========================================
    # MOVIMIENTOS
    # ==========================================
    @staticmethod
    def registrar_entrada():
        if "usuario_rol" not in session or str(session["usuario_rol"]) not in ["1", "4"]:
            return redirect(url_for("routes.login"))

        if request.method == "POST":
            try:
                data = request.get_json()

                movimiento_data = {
                    "tipo": TipoMovimiento.ENTRADA,
                    "insumo_id": data["insumo_id"],
                    "cantidad": float(data["cantidad"]),
                    "costo_unitario": float(data["costo_unitario"]),
                    "usuario_id": session["usuario_id"]
                }

                resultado = MovimientoInventario.registrar_movimiento(movimiento_data)

                if resultado["success"]:
                    AlertaStock.generar_alertas_automaticas()

                    # Notificación
                    NotificacionSistemaController.notificar_movimiento_inventario(
                        usuario_id=session.get("usuario_id"),
                        tipo_movimiento="entrada",
                        nombre_insumo=data.get("nombre_insumo", "Insumo"),
                        cantidad=data["cantidad"]
                    )

                    return jsonify({"success": True})

                return jsonify({"success": False}), 400

            except Exception as e:
                logging.error(e)
                return jsonify({"success": False}), 500

        insumos = Insumo.obtener_todos()
        proveedores = Proveedor.obtener_todos()

        return render_template(
            "inventario/movimientos/entrada.html",
            insumos=insumos,
            proveedores=proveedores
        )

    @staticmethod
    def historial_movimientos():
        if "usuario_rol" not in session or str(session["usuario_rol"]) not in ["1", "4"]:
            return redirect(url_for("routes.login"))

        movimientos = MovimientoInventario.obtener_historial({}, limit=200)
        insumos = Insumo.obtener_todos()

        return render_template(
            "inventario/movimientos.html",
            movimientos=movimientos,
            insumos=insumos
        )

    # ==========================================
    # ALERTAS
    # ==========================================
    @staticmethod
    def alertas_stock():
        if "usuario_rol" not in session or str(session["usuario_rol"]) not in ["1", "4"]:
            return redirect(url_for("routes.login"))

        alertas = AlertaStock.obtener_alertas_activas()

        return render_template(
            "inventario/alertas.html",
            alertas=alertas
        )

    # ==========================================
    # PROVEEDORES
    # ==========================================
    @staticmethod
    def lista_proveedores():
        if "usuario_rol" not in session or str(session["usuario_rol"]) not in ["1", "4"]:
            return redirect(url_for("routes.login"))

        proveedores = Proveedor.obtener_todos()

        return render_template(
            "inventario/proveedores/lista.html",
            proveedores=proveedores
        )

    # ==========================================
    # REPORTES
    # ==========================================
    @staticmethod
    def reportes():
        if "usuario_rol" not in session or str(session["usuario_rol"]) not in ["1", "4", "3"]:
            return redirect(url_for("routes.login"))

        # 🔥 CORREGIDO
        return render_template("inventario/reportes.html")
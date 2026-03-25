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
from datetime import datetime, timedelta
from controllers.notificaciones.notificacion_controller import NotificacionSistemaController
import logging
import json

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

        try:
            # -- Datos base --
            insumos = Insumo.obtener_todos({"activo": True})
            criticos = Insumo.obtener_stock_critico()

            total_insumos = len(insumos)
            total_criticos = len(criticos)
            total_normales = total_insumos - total_criticos
            valor_total = round(sum(
                float(i.get("stock_actual", 0)) * float(i.get("costo_unitario", 0))
                for i in insumos
            ), 2)

            # -- Chart 1: Estado del stock (donut) --
            chart_estado = json.dumps({
                "labels": ["Normal", "Crítico"],
                "data": [total_normales, total_criticos],
                "colors": ["#22c55e", "#ef4444"]
            })

            # -- Chart 2: Insumos por categoría (barras) --
            categorias_count = {}
            for insumo in insumos:
                cat = insumo.get("categoria", "otros")
                categorias_count[cat] = categorias_count.get(cat, 0) + 1

            chart_categorias = json.dumps({
                "labels": list(categorias_count.keys()),
                "data": list(categorias_count.values())
            })

            # -- Chart 3: Movimientos últimos 30 días por tipo (barras) --
            fecha_inicio = datetime.now() - timedelta(days=30)
            movimientos = MovimientoInventario.obtener_historial(
                {"fecha_desde": fecha_inicio}, limit=500
            )
            tipos_count = {"entrada": 0, "salida": 0, "merma": 0, "ajuste": 0}
            for mov in movimientos:
                tipo = mov.get("tipo", "")
                if tipo in tipos_count:
                    tipos_count[tipo] += 1

            chart_movimientos = json.dumps({
                "labels": ["Entradas", "Salidas", "Mermas", "Ajustes"],
                "data": [tipos_count["entrada"], tipos_count["salida"],
                         tipos_count["merma"], tipos_count["ajuste"]],
                "colors": ["#3b82f6", "#f97316", "#ef4444", "#a855f7"]
            })

            # -- Chart 4: Top 5 insumos por valor en inventario (barras horizontales) --
            top5 = sorted(
                insumos,
                key=lambda x: float(x.get("stock_actual", 0)) * float(x.get("costo_unitario", 0)),
                reverse=True
            )[:5]
            chart_top_valor = json.dumps({
                "labels": [i.get("nombre", "") for i in top5],
                "data": [
                    round(float(i.get("stock_actual", 0)) * float(i.get("costo_unitario", 0)), 2)
                    for i in top5
                ]
            })

            return render_template(
                "inventario/reportes.html",
                total_insumos=total_insumos,
                total_criticos=total_criticos,
                total_normales=total_normales,
                valor_total=valor_total,
                chart_estado=chart_estado,
                chart_categorias=chart_categorias,
                chart_movimientos=chart_movimientos,
                chart_top_valor=chart_top_valor
            )

        except Exception as e:
            logging.error(f"Error en reportes: {e}")
            return render_template(
                "inventario/reportes.html",
                total_insumos=0, total_criticos=0,
                total_normales=0, valor_total=0,
                chart_estado=json.dumps({"labels": [], "data": [], "colors": []}),
                chart_categorias=json.dumps({"labels": [], "data": []}),
                chart_movimientos=json.dumps({"labels": [], "data": [], "colors": []}),
                chart_top_valor=json.dumps({"labels": [], "data": []})
            )
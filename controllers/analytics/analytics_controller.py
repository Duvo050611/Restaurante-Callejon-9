"""
Analytics Controller — PostgreSQL (SQLAlchemy) + MongoDB (mesas)
Métricas de negocio sobre la tabla 'ventas' de PostgreSQL.
"""
from flask import jsonify, render_template, session
from config.db import db as mongo_db
from models.sql.venta import Venta
from config.database import db
from sqlalchemy import func, cast, Date, extract
from datetime import datetime, timedelta
from controllers.auth.AuthController import login_required, rol_required
from collections import defaultdict


class AnalyticsController:

    # ==============================
    # VISTA PRINCIPAL
    # ==============================

    @staticmethod
    @login_required
    @rol_required(['1'])
    def index():
        usuario = {
            "nombre": session.get("usuario_nombre", "Admin"),
            "rol": session.get("usuario_rol"),
            "id": session.get("usuario_id")
        }
        return render_template("admin/analytics/analytics.html", usuario=usuario)

    # ==============================
    # KPIs GENERALES
    # ==============================

    @staticmethod
    def get_kpis():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            hoy   = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            semana = hoy - timedelta(days=7)
            mes    = hoy - timedelta(days=30)

            def _agg(desde):
                rows = db.session.query(
                    func.sum(Venta.total).label("total"),
                    func.count(Venta.id).label("count"),
                ).filter(
                    Venta.fecha_creacion >= desde,
                    Venta.estado != Venta.ESTADO_CANCELADA,
                ).first()
                return float(rows.total or 0), int(rows.count or 0)

            total_hoy,    count_hoy    = _agg(hoy)
            total_semana, _            = _agg(semana)
            total_mes,    count_mes    = _agg(mes)
            ticket_promedio = round(total_mes / count_mes, 2) if count_mes else 0

            propinas_mes = db.session.query(func.sum(Venta.propina)).filter(
                Venta.fecha_creacion >= mes,
                Venta.estado != Venta.ESTADO_CANCELADA,
            ).scalar() or 0

            mesas_ocupadas = 0
            total_mesas    = 0
            try:
                mesas_ocupadas = mongo_db.mesas.count_documents({"estado": "ocupada"})
                total_mesas    = mongo_db.mesas.count_documents({})
            except Exception:
                pass

            return jsonify({
                "ventas_hoy":        total_hoy,
                "transacciones_hoy": count_hoy,
                "ventas_semana":     total_semana,
                "ventas_mes":        total_mes,
                "transacciones_mes": count_mes,
                "ticket_promedio":   ticket_promedio,
                "propinas_mes":      round(float(propinas_mes), 2),
                "mesas_ocupadas":    mesas_ocupadas,
                "total_mesas":       total_mesas,
                "ocupacion_pct":     round((mesas_ocupadas / total_mesas * 100) if total_mesas else 0, 1),
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==============================
    # TOP PLATILLOS
    # ==============================

    @staticmethod
    def get_top_platillos():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            fecha_inicio = datetime.now() - timedelta(days=30)

            ventas = Venta.query.filter(
                Venta.fecha_creacion >= fecha_inicio,
                Venta.estado != Venta.ESTADO_CANCELADA,
            ).all()

            acum = defaultdict(lambda: {"total_ingreso": 0.0, "total_cantidad": 0, "num_ventas": 0, "precios": []})
            for v in ventas:
                for item in (v.items or []):
                    nombre = item.get("nombre") or item.get("platillo")
                    if not nombre:
                        continue
                    acum[nombre]["total_ingreso"]  += float(item.get("subtotal", 0))
                    acum[nombre]["total_cantidad"] += int(item.get("cantidad", 0))
                    acum[nombre]["num_ventas"]     += 1
                    acum[nombre]["precios"].append(float(item.get("precio", 0)))

            resultado = sorted([
                {
                    "platillo":              nombre,
                    "total_ingreso":         round(d["total_ingreso"], 2),
                    "total_cantidad":        d["total_cantidad"],
                    "num_ventas":            d["num_ventas"],
                    "precio_unitario_prom":  round(sum(d["precios"]) / len(d["precios"]), 2) if d["precios"] else 0,
                }
                for nombre, d in acum.items()
            ], key=lambda x: x["total_ingreso"], reverse=True)[:10]

            return jsonify({"data": resultado, "periodo_dias": 30})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==============================
    # VENTAS POR DÍA (últimos 30 días)
    # ==============================

    @staticmethod
    def get_ventas_por_dia():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            fecha_inicio = datetime.now() - timedelta(days=30)

            rows = db.session.query(
                cast(Venta.fecha_creacion, Date).label("fecha"),
                func.sum(Venta.total).label("total"),
                func.count(Venta.id).label("transacciones"),
            ).filter(
                Venta.fecha_creacion >= fecha_inicio,
                Venta.estado != Venta.ESTADO_CANCELADA,
            ).group_by(cast(Venta.fecha_creacion, Date)).order_by("fecha").all()

            resultado = [
                {
                    "fecha":         str(r.fecha),
                    "total":         round(float(r.total or 0), 2),
                    "transacciones": int(r.transacciones or 0),
                }
                for r in rows
            ]
            return jsonify({"data": resultado})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==============================
    # VENTAS POR MÉTODO DE PAGO
    # ==============================

    @staticmethod
    def get_ventas_por_metodo_pago():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            fecha_inicio = datetime.now() - timedelta(days=30)

            rows = db.session.query(
                Venta.metodo_pago,
                func.sum(Venta.total).label("total"),
                func.count(Venta.id).label("count"),
            ).filter(
                Venta.fecha_creacion >= fecha_inicio,
                Venta.estado != Venta.ESTADO_CANCELADA,
            ).group_by(Venta.metodo_pago).order_by(func.sum(Venta.total).desc()).all()

            resultado = [
                {
                    "metodo": r.metodo_pago,
                    "total":  round(float(r.total or 0), 2),
                    "count":  int(r.count or 0),
                }
                for r in rows
            ]
            return jsonify({"data": resultado})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==============================
    # HORAS PICO
    # ==============================

    @staticmethod
    def get_horas_pico():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            fecha_inicio = datetime.now() - timedelta(days=30)

            rows = db.session.query(
                extract("hour", Venta.fecha_creacion).label("hora"),
                func.sum(Venta.total).label("total"),
                func.count(Venta.id).label("count"),
            ).filter(
                Venta.fecha_creacion >= fecha_inicio,
                Venta.estado != Venta.ESTADO_CANCELADA,
            ).group_by(extract("hour", Venta.fecha_creacion)).order_by("hora").all()

            resultado = [
                {
                    "hora":  int(r.hora),
                    "total": round(float(r.total or 0), 2),
                    "count": int(r.count or 0),
                }
                for r in rows
            ]
            return jsonify({"data": resultado})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==============================
    # RENDIMIENTO POR MESERO
    # ==============================

    @staticmethod
    def get_rendimiento_meseros():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            fecha_inicio = datetime.now() - timedelta(days=30)

            rows = db.session.query(
                Venta.mesero_nombre,
                func.sum(Venta.total).label("total_ventas"),
                func.count(Venta.id).label("num_ventas"),
                func.sum(Venta.propina).label("propinas"),
            ).filter(
                Venta.fecha_creacion >= fecha_inicio,
                Venta.estado != Venta.ESTADO_CANCELADA,
                Venta.mesero_nombre != "",
            ).group_by(Venta.mesero_nombre).order_by(func.sum(Venta.total).desc()).limit(10).all()

            resultado = [
                {
                    "mesero":          r.mesero_nombre,
                    "total_ventas":    round(float(r.total_ventas or 0), 2),
                    "num_ventas":      int(r.num_ventas or 0),
                    "propinas":        round(float(r.propinas or 0), 2),
                    "ticket_promedio": round(float(r.total_ventas or 0) / int(r.num_ventas or 1), 2),
                    "comensales_atendidos": 0,
                }
                for r in rows
            ]
            return jsonify({"data": resultado})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ==============================
    # VENTAS POR MESA
    # ==============================

    @staticmethod
    def get_ventas_por_mesa():
        try:
            if session.get("usuario_rol") != "1":
                return jsonify({"error": "No autorizado"}), 403

            fecha_inicio = datetime.now() - timedelta(days=30)

            rows = db.session.query(
                Venta.mesa_nombre,
                func.sum(Venta.total).label("total_ventas"),
                func.count(Venta.id).label("num_visitas"),
                func.avg(Venta.total).label("ticket_promedio"),
            ).filter(
                Venta.fecha_creacion >= fecha_inicio,
                Venta.estado != Venta.ESTADO_CANCELADA,
            ).group_by(Venta.mesa_nombre).order_by(func.sum(Venta.total).desc()).limit(15).all()

            resultado = [
                {
                    "mesa":            r.mesa_nombre or "Sin mesa",
                    "total_ventas":    round(float(r.total_ventas or 0), 2),
                    "num_visitas":     int(r.num_visitas or 0),
                    "ticket_promedio": round(float(r.ticket_promedio or 0), 2),
                    "comensales_total": 0,
                }
                for r in rows
            ]
            return jsonify({"data": resultado})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

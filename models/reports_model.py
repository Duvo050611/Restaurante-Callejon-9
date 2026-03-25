"""
Modelo de Reportes — PostgreSQL (ventas) + MongoDB (inventario/movimientos)
"""
from config.db import db as mongo_db
from config.database import db
from models.sql.venta import Venta
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from collections import defaultdict


class ReportsModel:
    """Modelo principal para todos los reportes del sistema"""

    # MongoDB collections (inventario — no migrado)
    movimientos = mongo_db.movimientos_inventario
    insumos     = mongo_db.insumos

    # ==========================================
    # REPORTES FINANCIEROS  (PostgreSQL)
    # ==========================================

    @staticmethod
    def ventas_por_periodo(fecha_inicio, fecha_fin, granularidad="dia"):
        """Ventas agrupadas por día/semana/mes."""
        rows = db.session.query(
            cast(Venta.fecha_creacion, Date).label("fecha"),
            func.sum(Venta.total).label("total_ventas"),
            func.count(Venta.id).label("num_pedidos"),
            func.sum(Venta.propina).label("total_propinas"),
            func.avg(Venta.total).label("promedio_por_pedido"),
        ).filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).group_by(cast(Venta.fecha_creacion, Date)).order_by("fecha").all()

        return [
            {
                "_id":               str(r.fecha),
                "total_ventas":      round(float(r.total_ventas or 0), 2),
                "num_pedidos":       int(r.num_pedidos or 0),
                "total_propinas":    round(float(r.total_propinas or 0), 2),
                "promedio_por_pedido": round(float(r.promedio_por_pedido or 0), 2),
            }
            for r in rows
        ]

    @staticmethod
    def utilidad_bruta(fecha_inicio, fecha_fin):
        """Calcula la utilidad bruta (sin datos de costo de insumos por platillo)."""
        row = db.session.query(
            func.sum(Venta.total).label("total_ventas"),
        ).filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).first()

        total_ventas = float(row.total_ventas or 0) if row else 0
        return {
            "total_ventas":  total_ventas,
            "costo_insumos": 0,
            "utilidad_bruta": total_ventas,
            "margen_bruto":  100.0 if total_ventas > 0 else 0,
        }

    @staticmethod
    def margen_por_producto(fecha_inicio, fecha_fin):
        """Margen por platillo (basado en ventas, sin datos de costo)."""
        ventas = Venta.query.filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).all()

        acum = defaultdict(lambda: {"ventas_totales": 0.0, "cantidad_vendida": 0})
        for v in ventas:
            for item in (v.items or []):
                nombre = item.get("nombre") or item.get("platillo", "")
                if nombre:
                    acum[nombre]["ventas_totales"]  += float(item.get("subtotal", 0))
                    acum[nombre]["cantidad_vendida"] += int(item.get("cantidad", 0))

        return sorted([
            {
                "_id":             nombre,
                "nombre":          nombre,
                "ventas_totales":  round(d["ventas_totales"], 2),
                "cantidad_vendida": d["cantidad_vendida"],
                "costo_total":     0,
                "utilidad":        round(d["ventas_totales"], 2),
                "margen":          100.0,
            }
            for nombre, d in acum.items()
        ], key=lambda x: x["ventas_totales"], reverse=True)

    @staticmethod
    def ingresos_vs_gastos(fecha_inicio, fecha_fin):
        """Ingresos de ventas vs gastos de inventario (MongoDB)."""
        row = db.session.query(func.sum(Venta.total)).filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).scalar()
        total_ingresos = float(row or 0)

        try:
            res = list(ReportsModel.movimientos.aggregate([
                {"$match": {"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}, "tipo": "salida"}},
                {"$group": {"_id": None, "total_gastos": {"$sum": "$costo_total"}}}
            ]))
            total_gastos = float(res[0]["total_gastos"]) if res else 0
        except Exception:
            total_gastos = 0

        return {
            "ingresos":   total_ingresos,
            "gastos":     total_gastos,
            "diferencia": total_ingresos - total_gastos,
            "ratio":      round(total_ingresos / total_gastos, 2) if total_gastos else 0,
        }

    @staticmethod
    def flujo_caja(fecha_inicio, fecha_fin):
        """Flujo de caja diario desde ventas."""
        rows = db.session.query(
            cast(Venta.fecha_creacion, Date).label("fecha"),
            func.sum(Venta.total).label("entradas"),
        ).filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).group_by(cast(Venta.fecha_creacion, Date)).order_by("fecha").all()

        return [
            {"fecha": str(r.fecha), "entradas": float(r.entradas or 0), "salidas": 0, "flujo_neto": float(r.entradas or 0)}
            for r in rows
        ]

    # ==========================================
    # REPORTES DE INVENTARIO  (MongoDB)
    # ==========================================

    @staticmethod
    def consumo_por_periodo(fecha_inicio, fecha_fin):
        try:
            return list(ReportsModel.movimientos.aggregate([
                {"$match": {"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}, "tipo": "salida"}},
                {"$group": {"_id": "$insumo_id", "nombre": {"$first": "$insumo_nombre"},
                            "categoria": {"$first": "$categoria"}, "cantidad_total": {"$sum": "$cantidad"},
                            "costo_total": {"$sum": "$costo_total"}, "movimientos": {"$sum": 1}}},
                {"$sort": {"costo_total": -1}}
            ]))
        except Exception:
            return []

    @staticmethod
    def merma_acumulada(fecha_inicio, fecha_fin):
        try:
            return list(ReportsModel.movimientos.aggregate([
                {"$match": {"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}, "tipo": "merma"}},
                {"$group": {"_id": "$insumo_id", "nombre": {"$first": "$insumo_nombre"},
                            "categoria": {"$first": "$categoria"}, "cantidad_perdida": {"$sum": "$cantidad"},
                            "costo_perdido": {"$sum": "$costo_total"}, "num_movimientos": {"$sum": 1}}},
                {"$sort": {"costo_perdido": -1}}
            ]))
        except Exception:
            return []

    @staticmethod
    def rotacion_inventario(fecha_inicio, fecha_fin):
        try:
            return list(ReportsModel.movimientos.aggregate([
                {"$match": {"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}, "tipo": {"$in": ["salida", "venta"]}}},
                {"$group": {"_id": "$categoria", "costo_total_consumido": {"$sum": "$costo_total"},
                            "cantidad_total": {"$sum": "$cantidad"}}},
                {"$sort": {"costo_total_consumido": -1}}
            ]))
        except Exception:
            return []

    @staticmethod
    def insumos_mas_costosos(fecha_inicio, fecha_fin, limite=10):
        try:
            return list(ReportsModel.movimientos.aggregate([
                {"$match": {"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin},
                            "tipo": {"$in": ["salida", "entrada", "merma"]}}},
                {"$group": {"_id": "$insumo_id", "nombre": {"$first": "$insumo_nombre"},
                            "categoria": {"$first": "$categoria"}, "costo_total": {"$sum": "$costo_total"},
                            "cantidad_total": {"$sum": "$cantidad"}}},
                {"$sort": {"costo_total": -1}},
                {"$limit": limite}
            ]))
        except Exception:
            return []

    @staticmethod
    def stock_actual():
        try:
            return list(ReportsModel.insumos.aggregate([
                {"$match": {"activo": True}},
                {"$sort": {"categoria": 1, "nombre": 1}}
            ]))
        except Exception:
            return []

    # ==========================================
    # REPORTES OPERATIVOS  (PostgreSQL)
    # ==========================================

    @staticmethod
    def rendimiento_empleado(fecha_inicio, fecha_fin):
        rows = db.session.query(
            Venta.mesero_id,
            Venta.mesero_nombre,
            func.sum(Venta.total).label("total_ventas"),
            func.count(Venta.id).label("num_pedidos"),
            func.sum(Venta.propina).label("total_propinas"),
            func.avg(Venta.total).label("promedio_venta"),
        ).filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).group_by(Venta.mesero_id, Venta.mesero_nombre).order_by(func.sum(Venta.total).desc()).all()

        return [
            {
                "_id":            r.mesero_id,
                "nombre_mesero":  r.mesero_nombre,
                "total_ventas":   round(float(r.total_ventas or 0), 2),
                "num_pedidos":    int(r.num_pedidos or 0),
                "total_propinas": round(float(r.total_propinas or 0), 2),
                "promedio_venta": round(float(r.promedio_venta or 0), 2),
            }
            for r in rows
        ]

    @staticmethod
    def tiempo_promedio_servicio(fecha_inicio, fecha_fin):
        """No hay datos de tiempo de servicio en ventas — retorna vacío."""
        return []

    @staticmethod
    def platillos_mas_vendidos(fecha_inicio, fecha_fin, limite=10):
        ventas = Venta.query.filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).all()

        acum = defaultdict(lambda: {"cantidad_vendida": 0, "ventas_totales": 0.0, "categoria": ""})
        for v in ventas:
            for item in (v.items or []):
                nombre = item.get("nombre") or item.get("platillo", "")
                if nombre:
                    acum[nombre]["cantidad_vendida"] += int(item.get("cantidad", 0))
                    acum[nombre]["ventas_totales"]   += float(item.get("subtotal", 0))
                    acum[nombre]["categoria"]         = item.get("categoria", "")

        return sorted([
            {"_id": n, "nombre": n, "categoria": d["categoria"],
             "cantidad_vendida": d["cantidad_vendida"],
             "ventas_totales": round(d["ventas_totales"], 2)}
            for n, d in acum.items()
        ], key=lambda x: x["cantidad_vendida"], reverse=True)[:limite]

    @staticmethod
    def platillos_menos_rentables(fecha_inicio, fecha_fin, limite=10):
        """Platillos con menos ventas totales."""
        return sorted(
            ReportsModel.platillos_mas_vendidos(fecha_inicio, fecha_fin, limite=9999),
            key=lambda x: x["ventas_totales"]
        )[:limite]

    # ==========================================
    # DISTRIBUCIÓN MÉTODOS DE PAGO
    # ==========================================

    @staticmethod
    def distribucion_metodos_pago(fecha_inicio, fecha_fin):
        rows = db.session.query(
            Venta.metodo_pago,
            func.sum(Venta.total).label("total"),
            func.count(Venta.id).label("transacciones"),
        ).filter(
            Venta.fecha_creacion >= fecha_inicio,
            Venta.fecha_creacion <= fecha_fin,
            Venta.estado != Venta.ESTADO_CANCELADA,
        ).group_by(Venta.metodo_pago).order_by(func.sum(Venta.total).desc()).all()

        return [
            {"_id": r.metodo_pago, "total": round(float(r.total or 0), 2), "transacciones": int(r.transacciones or 0)}
            for r in rows
        ]

    # ==========================================
    # TENDENCIAS
    # ==========================================

    @staticmethod
    def tendencia_ingresos(fecha_inicio, fecha_fin):
        return ReportsModel.ventas_por_periodo(fecha_inicio, fecha_fin, "dia")

    # ==========================================
    # RESUMEN EJECUTIVO
    # ==========================================

    @staticmethod
    def resumen_ejecutivo(fecha_inicio, fecha_fin):
        return {
            "periodo":      {"inicio": fecha_inicio.isoformat(), "fin": fecha_fin.isoformat()},
            "financiero":   ReportsModel.utilidad_bruta(fecha_inicio, fecha_fin),
            "ventas":       ReportsModel.ventas_por_periodo(fecha_inicio, fecha_fin),
            "top_platillos": ReportsModel.platillos_mas_vendidos(fecha_inicio, fecha_fin, 5),
            "top_empleados": ReportsModel.rendimiento_empleado(fecha_inicio, fecha_fin)[:3],
            "metodos_pago": ReportsModel.distribucion_metodos_pago(fecha_inicio, fecha_fin),
            "mermas":       ReportsModel.merma_acumulada(fecha_inicio, fecha_fin),
        }

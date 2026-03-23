from flask import jsonify, session, request
from datetime import datetime, timedelta
from config.db import db
from bson import ObjectId

class PropinasController:

    @staticmethod
    def propinas_hoy():
        """Obtiene las propinas del mesero del día actual"""
        mesero_id = session.get("usuario_id")
        
        if not mesero_id:
            return jsonify({"success": False, "error": "Sesión no válida"}), 401
        
        try:
            mesero_oid = ObjectId(mesero_id)
            
            inicio_dia = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = inicio_dia + timedelta(days=1)
            
            print(f"\n{'='*60}")
            print(f"💵 PROPINAS DEL DÍA - DEBUG")
            print(f"{'='*60}")
            print(f"Mesero ID: {mesero_id}")
            print(f"Inicio día: {inicio_dia}")
            print(f"Fin día: {fin_dia}")
            
            propinas = list(db.propinas.find({
                "mesero_id": mesero_oid,
                "fecha": {
                    "$gte": inicio_dia,
                    "$lt": fin_dia
                }
            }).sort("fecha", -1))
            
            print(f"📊 Propinas encontradas: {len(propinas)}")
            
            total_propinas = sum(float(p.get("monto", 0)) for p in propinas)
            
            print(f"💰 Total de propinas: ${total_propinas:.2f}")
            
            propinas_formateadas = []
            for p in propinas:
                propinas_formateadas.append({
                    "id": str(p["_id"]),
                    "monto": float(p.get("monto", 0)),
                    "porcentaje": float(p.get("porcentaje", 0)),
                    "mesa": p.get("mesa_numero"),
                    "metodo_pago": p.get("metodo_pago", "efectivo"),
                    "fecha": p.get("fecha").isoformat() if p.get("fecha") else None
                })
                print(f"   ✅ Mesa {p.get('mesa_numero')}: ${p.get('monto', 0):.2f} ({p.get('metodo_pago', 'efectivo')})")
            
            print(f"{'='*60}\n")
            
            return jsonify({
                "success": True,
                "total": total_propinas,
                "propinas": propinas_formateadas,
                "count": len(propinas_formateadas)
            })
            
        except Exception as e:
            print(f"❌ Error al obtener propinas: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500

    @staticmethod
    def propinas_rango():
        """Devuelve propinas agrupadas por día para un rango: dia, semana, mes"""
        mesero_id = session.get("usuario_id")
        if not mesero_id:
            return jsonify({"success": False, "error": "Sesión no válida"}), 401

        try:
            mesero_oid = ObjectId(mesero_id)

            rango = request.args.get("rango", "semana")  # dia, semana, mes
            mes   = request.args.get("mes")              # formato: "2026-03"

            hoy = datetime.now()

            if rango == "dia":
                inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
                fin    = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

            elif rango == "semana":
                inicio = (hoy - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
                fin    = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

            elif rango == "mes" and mes:
                anio_num, mes_num = map(int, mes.split("-"))
                inicio = datetime(anio_num, mes_num, 1, 0, 0, 0)
                if mes_num == 12:
                    fin = datetime(anio_num + 1, 1, 1) - timedelta(seconds=1)
                else:
                    fin = datetime(anio_num, mes_num + 1, 1) - timedelta(seconds=1)

            else:
                # Mes actual por defecto
                inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                fin    = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)

            print(f"\n{'='*50}")
            print(f"📊 PROPINAS RANGO: {rango} | mes: {mes}")
            print(f"   Desde: {inicio} → Hasta: {fin}")

            propinas = list(db.propinas.find({
                "mesero_id": mesero_oid,
                "fecha": {"$gte": inicio, "$lte": fin}
            }))

            print(f"   Registros encontrados: {len(propinas)}")

            # Agrupar por día
            por_dia = {}
            for p in propinas:
                dia = p["fecha"].strftime("%Y-%m-%d")
                por_dia[dia] = round(por_dia.get(dia, 0) + float(p.get("monto", 0)), 2)

            # Generar lista completa de días del rango (incluyendo días sin propinas)
            dias = []
            current = inicio
            while current.date() <= fin.date():
                fecha_str = current.strftime("%Y-%m-%d")
                dias.append({
                    "fecha": fecha_str,
                    "total": por_dia.get(fecha_str, 0)
                })
                current += timedelta(days=1)

            total_periodo = round(sum(por_dia.values()), 2)
            print(f"   Total período: ${total_periodo}")
            print(f"{'='*50}\n")

            return jsonify({
                "success": True,
                "dias": dias,
                "total": total_periodo,
                "rango": rango
            })

        except Exception as e:
            print(f"❌ Error propinas_rango: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
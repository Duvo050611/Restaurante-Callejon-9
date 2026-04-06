"""
KMeans Controller - Mesero
Segmenta las mesas atendidas por el mesero usando K-Means (k=3)
sobre las dimensiones: visitas (frecuencia) y ticket promedio.

Clusters resultantes:
  • Mesas VIP       — alta frecuencia + alto ticket
  • Mesas Regulares — frecuencia/ticket medios
  • Mesas Ocasionales — baja frecuencia o ticket bajo
"""
from flask import jsonify, render_template, session
from config.db import db
from bson import ObjectId
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np


# Colores y etiquetas por rango de cluster (ordenados de mayor a menor score)
_CLUSTER_META = [
    {"label": "Mesas VIP",        "color": "#f59e0b", "bg": "#fef3c7", "icon": "bi-star-fill"},
    {"label": "Mesas Regulares",  "color": "#3b82f6", "bg": "#dbeafe", "icon": "bi-circle-fill"},
    {"label": "Mesas Ocasionales","color": "#94a3b8", "bg": "#f1f5f9", "icon": "bi-circle"},
]


class MeseroKMeansController:

    # -----------------------------------------------
    # VISTA HTML
    # -----------------------------------------------
    @staticmethod
    def vista():
        if "usuario_rol" not in session or str(session["usuario_rol"]) != "2":
            from flask import redirect, url_for
            return redirect(url_for("routes.login"))
        perfil = session.get("perfil_mesero", {})
        return render_template("mesero/mesero_kmeans.html", perfil=perfil)

    # -----------------------------------------------
    # API JSON  →  /api/mesero/kmeans
    # -----------------------------------------------
    @staticmethod
    def api_kmeans():
        mesero_id = session.get("usuario_id")
        if not mesero_id:
            return jsonify({"success": False, "error": "Sesión no válida"}), 401

        try:
            mesero_oid = ObjectId(mesero_id)
            hace_90_dias = datetime.now() - timedelta(days=90)

            # ── 1. Agregación MongoDB: una fila por mesa ──────────────────────
            pipeline = [
                {"$match": {
                    "mesero_id": mesero_oid,
                    "estado": {"$in": ["pagada", "cerrada"]},
                    "fecha_cierre": {"$gte": hace_90_dias}
                }},
                {"$group": {
                    "_id": "$mesa_numero",
                    "num_visitas":     {"$sum": 1},
                    "ticket_promedio": {"$avg": "$total"},
                    "propina_promedio":{"$avg": "$propina"},
                    "ingreso_total":   {"$sum": "$total"},
                }},
                {"$match": {"num_visitas": {"$gte": 1}}},
                {"$sort": {"ingreso_total": -1}},
            ]
            mesas_raw = list(db.comandas.aggregate(pipeline))

            if len(mesas_raw) < 3:
                # No hay suficientes mesas — devolver vacío con mensaje
                return jsonify({
                    "success": True,
                    "puntos": [],
                    "clusters": [],
                    "resumen": [],
                    "aviso": "Se necesitan al menos 3 mesas con historial para ejecutar K-Means."
                })

            # ── 2. Preparar matriz de features ───────────────────────────────
            nombres = [f"Mesa {m['_id']}" for m in mesas_raw]
            X_raw = np.array([
                [float(m["num_visitas"]), float(m["ticket_promedio"])]
                for m in mesas_raw
            ])

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_raw)

            # ── 3. K-Means k=3 ───────────────────────────────────────────────
            k = min(3, len(mesas_raw))
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(X_scaled)
            labels = km.labels_

            # ── 4. Ordenar clusters: el de mayor "score" = VIP ───────────────
            # score = media(ticket_promedio) + media(num_visitas) normalizados
            centroids_orig = scaler.inverse_transform(km.cluster_centers_)
            scores = centroids_orig[:, 0] + centroids_orig[:, 1]  # visitas + ticket
            orden = np.argsort(scores)[::-1]  # de mayor a menor
            remap = {old: new for new, old in enumerate(orden)}
            labels_remap = np.array([remap[l] for l in labels])

            # ── 5. Construir respuesta ────────────────────────────────────────
            puntos = []
            for i, m in enumerate(mesas_raw):
                cl = int(labels_remap[i])
                meta = _CLUSTER_META[cl] if cl < len(_CLUSTER_META) else _CLUSTER_META[-1]
                puntos.append({
                    "mesa":            nombres[i],
                    "mesa_numero":     m["_id"],
                    "x":               round(float(m["num_visitas"]), 2),
                    "y":               round(float(m["ticket_promedio"]), 2),
                    "ingreso_total":   round(float(m["ingreso_total"]), 2),
                    "propina_promedio":round(float(m["propina_promedio"]), 2),
                    "cluster":         cl,
                    "label":           meta["label"],
                    "color":           meta["color"],
                })

            # Resumen por cluster
            resumen = []
            for cl_idx, meta in enumerate(_CLUSTER_META[:k]):
                grupo = [p for p in puntos if p["cluster"] == cl_idx]
                if not grupo:
                    continue
                resumen.append({
                    "cluster":      cl_idx,
                    "label":        meta["label"],
                    "color":        meta["color"],
                    "bg":           meta["bg"],
                    "icon":         meta["icon"],
                    "num_mesas":    len(grupo),
                    "ticket_prom":  round(sum(p["y"] for p in grupo) / len(grupo), 2),
                    "visitas_prom": round(sum(p["x"] for p in grupo) / len(grupo), 1),
                    "mesas":        sorted([p["mesa"] for p in grupo]),
                })

            return jsonify({
                "success": True,
                "puntos": puntos,
                "resumen": resumen,
                "periodo_dias": 90,
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

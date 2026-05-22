from config.db import db
from bson import ObjectId
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np


_CLUSTER_META = [
    {"label": "Mesas VIP",         "color": "#f59e0b", "bg": "#fef3c7", "icon": "bi-star-fill"},
    {"label": "Mesas Regulares",   "color": "#3b82f6", "bg": "#dbeafe", "icon": "bi-circle-fill"},
    {"label": "Mesas Ocasionales", "color": "#94a3b8", "bg": "#f1f5f9", "icon": "bi-circle"},
]


class MeseroKMeansService:

    @staticmethod
    def segmentar_mesas(mesero_id: str, dias: int = 90) -> dict:
        mesero_oid = ObjectId(mesero_id)
        hace_n_dias = datetime.now() - timedelta(days=dias)

        pipeline = [
            {"$match": {
                "mesero_id": mesero_oid,
                "estado": {"$in": ["pagada", "cerrada"]},
                "fecha_cierre": {"$gte": hace_n_dias}
            }},
            {"$group": {
                "_id": "$mesa_numero",
                "num_visitas": {"$sum": 1},
                "ticket_promedio": {"$avg": "$total"},
                "propina_promedio": {"$avg": "$propina"},
                "ingreso_total": {"$sum": "$total"}
            }},
            {"$match": {"num_visitas": {"$gte": 1}}},
            {"$sort": {"ingreso_total": -1}}
        ]
        mesas_raw = list(db.comandas.aggregate(pipeline))

        if len(mesas_raw) < 3:
            return {
                "puntos": [], "clusters": [], "resumen": [],
                "aviso": "Se necesitan al menos 3 mesas con historial para ejecutar K-Means."
            }

        nombres = [f"Mesa {m['_id']}" for m in mesas_raw]
        X_raw = np.array([
            [float(m["num_visitas"]), float(m["ticket_promedio"])]
            for m in mesas_raw
        ])

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_raw)

        k = min(3, len(mesas_raw))
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)

        centroids_orig = scaler.inverse_transform(km.cluster_centers_)
        orden = np.argsort(centroids_orig[:, 0] + centroids_orig[:, 1])[::-1]
        remap = {old: new for new, old in enumerate(orden)}
        labels_remap = np.array([remap[l] for l in km.labels_])

        puntos = []
        for i, m in enumerate(mesas_raw):
            cl = int(labels_remap[i])
            meta = _CLUSTER_META[cl] if cl < len(_CLUSTER_META) else _CLUSTER_META[-1]
            puntos.append({
                "mesa": nombres[i],
                "mesa_numero": m["_id"],
                "x": round(float(m["num_visitas"]), 2),
                "y": round(float(m["ticket_promedio"]), 2),
                "ingreso_total": round(float(m["ingreso_total"]), 2),
                "propina_promedio": round(float(m["propina_promedio"]), 2),
                "cluster": cl,
                "label": meta["label"],
                "color": meta["color"]
            })

        resumen = []
        for cl_idx, meta in enumerate(_CLUSTER_META[:k]):
            grupo = [p for p in puntos if p["cluster"] == cl_idx]
            if not grupo:
                continue
            resumen.append({
                "cluster": cl_idx,
                "label": meta["label"],
                "color": meta["color"],
                "bg": meta["bg"],
                "icon": meta["icon"],
                "num_mesas": len(grupo),
                "ticket_prom": round(sum(p["y"] for p in grupo) / len(grupo), 2),
                "visitas_prom": round(sum(p["x"] for p in grupo) / len(grupo), 1),
                "mesas": sorted([p["mesa"] for p in grupo])
            })

        return {"puntos": puntos, "resumen": resumen, "periodo_dias": dias}

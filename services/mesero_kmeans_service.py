from config.db import db
from bson import ObjectId
from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import export_text
from sklearn.metrics import silhouette_score
import numpy as np


_CLUSTER_META = [
    {
        "label": "Mesas VIP",
        "color": "#f59e0b",
        "bg": "#fef3c7",
        "icon": "bi-star-fill",
        "recomendacion": "Son tus mesas más rentables. Asigna atención prioritaria y busca fidelizar a estos clientes con un servicio excepcional.",
    },
    {
        "label": "Mesas Regulares",
        "color": "#3b82f6",
        "bg": "#dbeafe",
        "icon": "bi-circle-fill",
        "recomendacion": "Buen potencial de crecimiento. Mantén consistencia en el servicio y considera pequeños incentivos para subir su ticket.",
    },
    {
        "label": "Mesas Ocasionales",
        "color": "#94a3b8",
        "bg": "#f1f5f9",
        "icon": "bi-circle",
        "recomendacion": "Baja frecuencia de uso. Evalúa promociones o menú especial para atraerlos con más regularidad.",
    },
]

_FEATURE_LABELS = ["Frecuencia", "Ticket Promedio", "Variabilidad"]


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
                "num_visitas":    {"$sum": 1},
                "ticket_promedio": {"$avg": "$total"},
                "ticket_std":     {"$stdDevPop": "$total"},
                "propina_promedio": {"$avg": "$propina"},
                "ingreso_total":  {"$sum": "$total"}
            }},
            {"$match": {"num_visitas": {"$gte": 1}}},
            {"$sort": {"ingreso_total": -1}}
        ]
        mesas_raw = list(db.comandas.aggregate(pipeline))

        if len(mesas_raw) < 3:
            return {
                "puntos": [], "resumen": [],
                "aviso": "Se necesitan al menos 3 mesas con historial para ejecutar K-Means."
            }

        nombres = [f"Mesa {m['_id']}" for m in mesas_raw]

        # K-Means usa 2 features (espacio 2D): frecuencia + ticket promedio
        X_kmeans = np.array([
            [float(m["num_visitas"]), float(m["ticket_promedio"])]
            for m in mesas_raw
        ])
        # El árbol de decisión usa las 3 features para reconstruir los clusters
        X_arbol = np.array([
            [
                float(m["num_visitas"]),
                float(m["ticket_promedio"]),
                float(m.get("ticket_std") or 0),
            ]
            for m in mesas_raw
        ])

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_kmeans)

        k = min(3, len(mesas_raw))
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)

        sil_score = None
        if k >= 2 and len(mesas_raw) > k:
            sil_score = round(float(silhouette_score(X_scaled, km.labels_)), 4)

        centroids_orig = scaler.inverse_transform(km.cluster_centers_)
        orden = np.argsort(centroids_orig[:, 0] + centroids_orig[:, 1])[::-1]
        remap = {old: new for new, old in enumerate(orden)}
        labels_remap = np.array([remap[l] for l in km.labels_])

        puntos = []
        for i, m in enumerate(mesas_raw):
            cl = int(labels_remap[i])
            meta = _CLUSTER_META[cl] if cl < len(_CLUSTER_META) else _CLUSTER_META[-1]
            puntos.append({
                "mesa":           nombres[i],
                "mesa_numero":    m["_id"],
                "x":              round(float(m["num_visitas"]), 2),
                "y":              round(float(m["ticket_promedio"]), 2),
                "ticket_std":     round(float(m.get("ticket_std") or 0), 2),
                "ingreso_total":  round(float(m["ingreso_total"]), 2),
                "propina_promedio": round(float(m["propina_promedio"]), 2),
                "cluster":        cl,
                "label":          meta["label"],
                "color":          meta["color"],
            })

        resumen = []
        for cl_idx, meta in enumerate(_CLUSTER_META[:k]):
            grupo = [p for p in puntos if p["cluster"] == cl_idx]
            if not grupo:
                continue
            resumen.append({
                "cluster":       cl_idx,
                "label":         meta["label"],
                "color":         meta["color"],
                "bg":            meta["bg"],
                "icon":          meta["icon"],
                "recomendacion": meta["recomendacion"],
                "num_mesas":     len(grupo),
                "ticket_prom":   round(sum(p["y"] for p in grupo) / len(grupo), 2),
                "visitas_prom":  round(sum(p["x"] for p in grupo) / len(grupo), 1),
                "mesas":         sorted([p["mesa"] for p in grupo]),
            })

        # Elbow method: inertia para k=1..min(5, n_mesas-1)
        elbow = []
        for ki in range(1, min(6, len(mesas_raw))):
            ki_km = KMeans(n_clusters=ki, random_state=42, n_init=10)
            ki_km.fit(X_scaled)
            elbow.append({"k": ki, "inertia": round(float(ki_km.inertia_), 4)})

        arbol = MeseroKMeansService._entrenar_arbol(X_arbol, labels_remap, k)

        return {
            "puntos":      puntos,
            "resumen":     resumen,
            "periodo_dias": dias,
            "evaluacion": {
                "silhouette_score": sil_score,
                "inertia":          round(float(km.inertia_), 4),
                "n_mesas":          len(mesas_raw),
                "n_clusters":       k,
                "elbow":            elbow,
            },
            "arbol": arbol,
        }

    @staticmethod
    def _entrenar_arbol(X_raw: np.ndarray, labels: np.ndarray, k: int) -> dict:
        nombres_clase = [_CLUSTER_META[i]["label"] for i in range(k)]

        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=3,
            random_state=42,
            oob_score=True,
        )
        rf.fit(X_raw, labels)

        # Importancia promedio ± desviación entre árboles
        imp_mean = rf.feature_importances_
        imp_std  = np.std([t.feature_importances_ for t in rf.estimators_], axis=0)

        importancias = sorted(
            [
                {
                    "feature":     _FEATURE_LABELS[i],
                    "importancia": round(float(imp_mean[i]), 4),
                    "std":         round(float(imp_std[i]),  4),
                }
                for i in range(len(_FEATURE_LABELS))
            ],
            key=lambda x: x["importancia"],
            reverse=True,
        )

        # Árbol representativo: el más cercano al promedio de importancias
        diffs = [
            float(np.sum((t.feature_importances_ - imp_mean) ** 2))
            for t in rf.estimators_
        ]
        arbol_rep = rf.estimators_[int(np.argmin(diffs))]
        reglas = export_text(arbol_rep, feature_names=_FEATURE_LABELS)

        return {
            "reglas":              reglas,
            "feature_importances": importancias,
            "clases":              nombres_clase,
            "n_estimators":        rf.n_estimators,
            "oob_score":           round(float(rf.oob_score_), 4),
        }

    @staticmethod
    def diagnostico_datos(mesero_id: str, dias: int = 90) -> dict:
        mesero_oid = ObjectId(mesero_id)
        hace_n_dias = datetime.now() - timedelta(days=dias)

        match = {
            "mesero_id": mesero_oid,
            "estado":    {"$in": ["pagada", "cerrada"]},
            "fecha_cierre": {"$gte": hace_n_dias},
        }

        global_agg = list(db.comandas.aggregate([
            {"$match": match},
            {"$group": {
                "_id":               None,
                "total":             {"$sum": 1},
                "fecha_min":         {"$min": "$fecha_cierre"},
                "fecha_max":         {"$max": "$fecha_cierre"},
                "ticket_global_avg": {"$avg": "$total"},
                "ticket_global_std": {"$stdDevPop": "$total"},
            }}
        ]))

        if not global_agg:
            return {"error": "Sin datos en el periodo", "total_comandas": 0}

        g = global_agg[0]

        por_mesa = list(db.comandas.aggregate([
            {"$match": match},
            {"$group": {
                "_id":           "$mesa_numero",
                "n":             {"$sum": 1},
                "ticket_min":    {"$min": "$total"},
                "ticket_max":    {"$max": "$total"},
                "ticket_avg":    {"$avg": "$total"},
                "ticket_std":    {"$stdDevPop": "$total"},
                "propina_pct_avg": {"$avg": "$porcentaje_propina"},
                "comensales_avg": {"$avg": "$num_comensales"},
            }},
            {"$sort": {"_id": 1}},
        ]))

        metodos = list(db.comandas.aggregate([
            {"$match": match},
            {"$group": {"_id": "$metodo_pago", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]))

        return {
            "total_comandas":    int(g["total"]),
            "fecha_inicio":      g["fecha_min"].strftime("%d/%m/%Y") if g.get("fecha_min") else None,
            "fecha_fin":         g["fecha_max"].strftime("%d/%m/%Y") if g.get("fecha_max") else None,
            "ticket_global_avg": round(float(g["ticket_global_avg"]), 2),
            "ticket_global_std": round(float(g["ticket_global_std"]), 2),
            "por_mesa": [
                {
                    "mesa":          m["_id"],
                    "registros":     m["n"],
                    "ticket_min":    round(float(m["ticket_min"]), 2),
                    "ticket_max":    round(float(m["ticket_max"]), 2),
                    "ticket_avg":    round(float(m["ticket_avg"]), 2),
                    "ticket_std":    round(float(m.get("ticket_std") or 0), 2),
                    "propina_pct_avg": round(float(m.get("propina_pct_avg") or 0), 1),
                    "comensales_avg": round(float(m.get("comensales_avg") or 0), 1),
                }
                for m in por_mesa
            ],
            "metodos_pago": [{"metodo": m["_id"], "count": m["count"]} for m in metodos],
            "periodo_dias": dias,
        }

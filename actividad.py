from pymongo import MongoClient
# Conexión a MongoDB
uri = "mongodb+srv://ludg:garcia16@cluster81.tlydlr0.mongodb.net/callejon9?retryWrites=true&w=majority"
client = MongoClient(uri)
pipeline = [
    {
        "$group": {
            "_id": "$platillo",   # ← cambia producto por platillo
            "total_cantidad": {"$sum": "$cantidad"},
            "promedio_precio": {"$avg": "$precio"},
            "precio_min": {"$min": "$precio"},
            "precio_max": {"$max": "$precio"},
            "ventas_registradas": {"$sum": 1},
            "total_ingresos": {
                "$sum": {"$multiply": ["$precio", "$cantidad"]}
            },
            "detalle_ventas": {
                "$push": {
                    "cantidad": "$cantidad",
                    "precio": "$precio",
                    "fecha": "$fecha"
                }
            }
        }
    }
]
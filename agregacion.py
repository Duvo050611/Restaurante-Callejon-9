from pymongo import MongoClient

uri = "mongodb+srv://ludg:garcia16@cluster81.tlydlr0.mongodb.net/callejon9_prueba?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["callejon9_prueba"]
coleccion = db["ventas"]

#consultar analisis de platillos
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
resultado = coleccion.aggregate(pipeline)    
for doc in resultado:
    print(doc)
from pymongo import MongoClient

pipeline = [
    {

        "$group": {
            "_id": "producto",
            "total": {"$sum": "$cantidad"},
            "promedio_precio": {"$avg": "$precio"},
            "ventas_registradas": {"$sum": 1}
            #total = sumatoria (precio por cantidad)

            #total_ingresos {
            #    "$sum": {
            #        "$multiply": ["$precio", "$cantidad"]}
        }
    }
]

"""
Modelo de Mesas - Estado y Asignacion
"""
from config.db import db

class Mesa:
    collection = db["mesas"]
    
    # Estados de mesa
    ESTADO_DISPONIBLE = "disponible"
    ESTADO_OCUPADA = "ocupada"
    ESTADO_RESERVADA = "reservada"
    ESTADO_LIMPIEZA = "limpieza"
    
    @classmethod
    def find_all(cls):
        """Obtiene todas las mesas"""
        return list(cls.collection.find())
    
    @classmethod
    def find_by_id(cls, id):
        """Obtiene una mesa por ID"""
        from bson.objectid import ObjectId
        return cls.collection.find_one({"_id": ObjectId(id)})
    
    @classmethod
    def find_by_estado(cls, estado):
        """Obtiene mesas por estado"""
        return list(cls.collection.find({"estado": estado}))
    
    @classmethod
    def find_disponibles(cls):
        """Obtiene mesas disponibles"""
        return list(cls.collection.find({"estado": cls.ESTADO_DISPONIBLE}))
    
    @classmethod
    def create(cls, data):
        """Crea una nueva mesa"""
        from datetime import datetime
        mesa = {
            "numero": data.get("numero"),
            "capacidad": data.get("capacidad", 4),
            "estado": cls.ESTADO_DISPONIBLE,
            "ubicacion": data.get("ubicacion", ""),
            "notas": data.get("notas", ""),
            "fecha_creacion": datetime.utcnow()
        }
        result = cls.collection.insert_one(mesa)
        return str(result.inserted_id)
    
    @classmethod
    def update(cls, id, data):
        """Actualiza una mesa"""
        from datetime import datetime
        from bson.objectid import ObjectId
        
        update_data = {
            "fecha_actualizacion": datetime.utcnow()
        }
        
        campos = ["numero", "capacidad", "estado", "ubicacion", "notas"]
        for campo in campos:
            if campo in data:
                update_data[campo] = data[campo]
        
        result = cls.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, id):
        """Elimina una mesa"""
        from bson.objectid import ObjectId
        result = cls.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0
    
    @classmethod
    def cambiar_estado(cls, id, nuevo_estado):
        """Cambia el estado de una mesa"""
        from datetime import datetime
        from bson.objectid import ObjectId
        
        result = cls.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"estado": nuevo_estado, "fecha_actualizacion": datetime.utcnow()}}
        )
        return result.modified_count > 0

"""
Script para generar datos de prueba en la colección 'ventas'
Ejecutar con: python scripts/generate_test_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.db import db
from datetime import datetime, timedelta
import random

# Datos de platillos del menú
PLATILLOS = [
    # Entradas
    {"nombre": "Nachos con Guacamole", "categoria": "entrada", "precio": 65},
    {"nombre": "Quesadillas Rancheras", "categoria": "entrada", "precio": 55},
    {"nombre": "Sopa de Tortilla", "categoria": "entrada", "precio": 45},
    {"nombre": "Guacamole con Totopos", "categoria": "entrada", "precio": 70},
    {"nombre": "Enchiladas de Mole", "categoria": "entrada", "precio": 60},
    
    # Platos Fuertes
    {"nombre": "Enchiladas Suizas", "categoria": "plato_fuerte", "precio": 125},
    {"nombre": "Milanesa de Res", "categoria": "plato_fuerte", "precio": 145},
    {"nombre": "Tacos al Pastor", "categoria": "plato_fuerte", "precio": 95},
    {"nombre": "Burrito Especial", "categoria": "plato_fuerte", "precio": 110},
    {"nombre": "Chiles Rellenos", "categoria": "plato_fuerte", "precio": 130},
    {"nombre": "Filete de Pescado", "categoria": "plato_fuerte", "precio": 165},
    {"nombre": "Parrillada para 2", "categoria": "plato_fuerte", "precio": 320},
    {"nombre": "Hamburguesa Clásica", "categoria": "plato_fuerte", "precio": 95},
    {"nombre": "Pasta Bolognesa", "categoria": "plato_fuerte", "precio": 105},
    
    # Bebidas
    {"nombre": "Agua Mineral", "categoria": "bebida", "precio": 25},
    {"nombre": "Refresco", "categoria": "bebida", "precio": 30},
    {"nombre": "Cerveza Nacional", "categoria": "bebida", "precio": 45},
    {"nombre": "Cerveza Importada", "categoria": "bebida", "precio": 65},
    {"nombre": "Margarita", "categoria": "bebida", "precio": 85},
    {"nombre": "Limonada Natural", "categoria": "bebida", "precio": 35},
    {"nombre": "Café Capuccino", "categoria": "bebida", "precio": 40},
    
    # Postres
    {"nombre": "Flan Napolitano", "categoria": "postre", "precio": 45},
    {"nombre": "Pastel de Chocolate", "categoria": "postre", "precio": 55},
    {"nombre": "Crepas con Nutella", "categoria": "postre", "precio": 65},
    {"nombre": "Helado de Vainilla", "categoria": "postre", "precio": 35},
    {"nombre": "Churros con Chocolate", "categoria": "postre", "precio": 50},
]

# Meseros
MESEROS = [
    {"id": "697d82ff2a0a1055937a2250", "nombre": "Juan Pérez"},
    {"id": "697d82ff2a0a1055937a2251", "nombre": "María García"},
    {"id": "697d82ff2a0a1055937a2252", "nombre": "Carlos López"},
    {"id": "697d82ff2a0a1055937a2253", "nombre": "Ana Martínez"},
    {"id": "697d82ff2a0a1055937a2254", "nombre": "Pedro Sánchez"},
]

# Métodos de pago
METODOS_PAGO = ["efectivo", "tarjeta", "transferencia", "mixto"]

def generar_venta(numero_venta, fecha):
    """Genera un documento de venta aleatorio"""
    
    # Seleccionar mesero aleatorio
    mesero = random.choice(MESEROS)
    
    # Seleccionar número de mesa (1-15)
    mesa = random.randint(1, 15)
    
    # Seleccionar número de comensales (1-8)
    comensales = random.randint(1, 8)
    
    # Generar 1-5 platillos por venta
    num_platillos = random.randint(1, 5)
    platillos_seleccionados = random.sample(PLATILLOS, num_platillos)
    
    platillos = []
    subtotal = 0
    
    for p in platillos_seleccionados:
        cantidad = random.randint(1, 3)
        precio_unitario = p["precio"]
        # Variación de precio ±10%
        precio_unitario = round(precio_unitario * random.uniform(0.9, 1.1), 2)
        item_subtotal = precio_unitario * cantidad
        
        platillos.append({
            "nombre": p["nombre"],
            "categoria": p["categoria"],
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            "subtotal": item_subtotal
        })
        subtotal += item_subtotal
    
    # Calcular totales
    # Suponiendo 16% de impuesto
    impuesto = round(subtotal * 0.16, 2)
    total = subtotal + impuesto
    
    # Propina (10-20% del subtotal)
    porcentaje_propina = random.uniform(0.10, 0.20)
    propina = round(subtotal * porcentaje_propina, 2)
    
    # Método de pago
    metodo_pago = random.choice(METODOS_PAGO)
    
    # Crear el documento
    venta = {
        "numero_venta": numero_venta,
        "mesa_numero": mesa,
        "mesero_id": {"$oid": mesero["id"]},
        "mesero_nombre": mesero["nombre"],
        "comensales": comensales,
        "platillos": platillos,
        "subtotal": round(subtotal, 2),
        "impuesto": impuesto,
        "propina": propina,
        "total": round(total, 2),
        "metodo_pago": metodo_pago,
        "fecha": fecha,
        "created_at": fecha
    }
    
    return venta


def populate_ventas(dias_atras=60, ventas_por_dia=8):
    """
    Genera datos de prueba para la colección 'ventas'
    
    Args:
        dias_atras: Cuántos días hacia atrás generar datos
        ventas_por_dia: Número promedio de ventas por día
    """
    print("[1] Limpiando coleccion 'ventas'...")
    db.ventas.delete_many({})
    
    fecha_actual = datetime.now()
    fecha_inicio = fecha_actual - timedelta(days=dias_atras)
    
    ventas = []
    numero_venta = 500  # Empezar desde 500
    
    print(f"[2] Generando datos de prueba ({dias_atras} dias, ~{ventas_por_dia} ventas/dia)...")
    
    dias_generados = 0
    while fecha_inicio <= fecha_actual:
        # Variar numero de ventas por dia (5-12)
        num_ventas_hoy = random.randint(5, 12)
        
        for _ in range(num_ventas_hoy):
            # Hora aleatoria entre 11:00 y 22:00
            hora = random.randint(11, 22)
            minuto = random.randint(0, 59)
            segundo = random.randint(0, 59)
            
            fecha_venta = fecha_inicio.replace(
                hour=hora,
                minute=minuto,
                second=segundo,
                microsecond=0
            )
            
            venta = generar_venta(numero_venta, fecha_venta)
            ventas.append(venta)
            
            numero_venta += 1
        
        dias_generados += 1
        fecha_inicio += timedelta(days=1)
        
        if dias_generados % 10 == 0:
            print(f"   -> Dia {dias_generados}... ({len(ventas)} ventas generadas)")
    
    # Insertar en MongoDB (en batches de 1000)
    print(f"[3] Insertando {len(ventas)} documentos en MongoDB...")
    
    batch_size = 1000
    for i in range(0, len(ventas), batch_size):
        batch = ventas[i:i+batch_size]
        db.ventas.insert_many(batch)
        print(f"   -> Insertados {min(i+batch_size, len(ventas))}/{len(ventas)}")
    
    print(f"[OK] Listo! Se generaron {len(ventas)} ventas de prueba.")
    print(f"   Rango: #{ventas[0]['numero_venta']} a #{ventas[-1]['numero_venta']}")
    print(f"   Periodo: {ventas[0]['fecha'].strftime('%Y-%m-%d')} a {ventas[-1]['fecha'].strftime('%Y-%m-%d')}")
    
    return len(ventas)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generar datos de prueba para analytics")
    parser.add_argument("--dias", type=int, default=60, help="Días hacia atrás a generar")
    parser.add_argument("--ventas-dia", type=int, default=8, help="Ventas promedio por día")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print(" GENERADOR DE DATOS DE PRUEBA - RESTAURANTE")
    print("=" * 50)
    
    populate_ventas(dias_atras=args.dias, ventas_por_dia=args.ventas_dia)

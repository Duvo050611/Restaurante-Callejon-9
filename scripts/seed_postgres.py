"""
Seed completo de PostgreSQL — Restaurante Callejón 9
Pobla: usuarios (todos los roles), categorías, platillos y ventas históricas

Uso:
    python scripts/seed_postgres.py
    python scripts/seed_postgres.py --reset   # limpia y re-siembra todo
"""
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from config.database import db, init_db
from models.sql.usuario import Usuario
from models.sql.menu import Categoria, Platillo
from models.sql.venta import Venta, CorteCaja


def crear_app():
    app = Flask(__name__)
    init_db(app)
    with app.app_context():
        db.create_all()  # crea ventas, cuentas, cortes_caja si no existen
    return app


# ===========================================================
# DATOS
# ===========================================================

USUARIOS = [
    # ---- ADMIN ----
    {
        "usuario_nombre":    "Carlos",
        "usuario_apellidos": "Mendoza Rivera",
        "usuario_email":     "admin@callejon9.com",
        "usuario_clave":     "admin123",
        "usuario_rol":       "1",
        "usuario_telefono":  "5512345678",
        "usuario_status":    1,
        "perfil_extra":      {},
    },
    # ---- MESEROS ----
    {
        "usuario_nombre":    "Valeria",
        "usuario_apellidos": "Torres Gómez",
        "usuario_email":     "valeria.mesero@callejon9.com",
        "usuario_clave":     "mesero123",
        "usuario_rol":       "2",
        "usuario_telefono":  "5523456789",
        "usuario_status":    1,
        "perfil_extra": {
            "mesero_numero":                   "M-001",
            "mesero_turno":                    "matutino",
            "mesero_mesas":                    [1, 2, 3, 4],
            "mesero_puede_cerrar_cuenta":      True,
            "mesero_puede_aplicar_descuento":  False,
            "mesero_propina_sugerida":         10,
            "mesero_propina_acumulada_dia":    0,
            "mesero_ventas_promedio_dia":      0,
            "mesero_calificacion_cliente":     0,
        },
    },
    {
        "usuario_nombre":    "Regina",
        "usuario_apellidos": "Salinas Pérez",
        "usuario_email":     "regina.mesero@callejon9.com",
        "usuario_clave":     "mesero123",
        "usuario_rol":       "2",
        "usuario_telefono":  "5534567890",
        "usuario_status":    1,
        "perfil_extra": {
            "mesero_numero":                   "M-002",
            "mesero_turno":                    "vespertino",
            "mesero_mesas":                    [5, 6, 7, 8],
            "mesero_puede_cerrar_cuenta":      True,
            "mesero_puede_aplicar_descuento":  True,
            "mesero_propina_sugerida":         10,
            "mesero_propina_acumulada_dia":    0,
            "mesero_ventas_promedio_dia":      0,
            "mesero_calificacion_cliente":     0,
        },
    },
    {
        "usuario_nombre":    "Octavio",
        "usuario_apellidos": "Ramírez Luna",
        "usuario_email":     "octavio.mesero@callejon9.com",
        "usuario_clave":     "mesero123",
        "usuario_rol":       "2",
        "usuario_telefono":  "5545678901",
        "usuario_status":    1,
        "perfil_extra": {
            "mesero_numero":                   "M-003",
            "mesero_turno":                    "nocturno",
            "mesero_mesas":                    [9, 10, 11, 12],
            "mesero_puede_cerrar_cuenta":      True,
            "mesero_puede_aplicar_descuento":  False,
            "mesero_propina_sugerida":         15,
            "mesero_propina_acumulada_dia":    0,
            "mesero_ventas_promedio_dia":      0,
            "mesero_calificacion_cliente":     0,
        },
    },
    # ---- COCINA ----
    {
        "usuario_nombre":    "Miguel",
        "usuario_apellidos": "Hernández Cruz",
        "usuario_email":     "miguel.cocina@callejon9.com",
        "usuario_clave":     "cocina123",
        "usuario_rol":       "3",
        "usuario_telefono":  "5556789012",
        "usuario_status":    1,
        "perfil_extra": {
            "cocina_numero":                     "C-001",
            "cocina_puesto":                     "Chef",
            "cocina_area":                       "caliente",
            "cocina_turno":                      "matutino",
            "cocina_especialidad":               ["carnes", "platos_fuertes"],
            "cocina_puede_modificar_menu":       True,
            "cocina_puede_ver_recetas_completas": True,
            "cocina_certificaciones":            ["HACCP"],
        },
    },
    {
        "usuario_nombre":    "Sofía",
        "usuario_apellidos": "Guerrero Vega",
        "usuario_email":     "sofia.cocina@callejon9.com",
        "usuario_clave":     "cocina123",
        "usuario_rol":       "3",
        "usuario_telefono":  "5567890123",
        "usuario_status":    1,
        "perfil_extra": {
            "cocina_numero":                     "C-002",
            "cocina_puesto":                     "Sous Chef",
            "cocina_area":                       "fria",
            "cocina_turno":                      "vespertino",
            "cocina_especialidad":               ["entradas", "postres"],
            "cocina_puede_modificar_menu":       False,
            "cocina_puede_ver_recetas_completas": True,
            "cocina_certificaciones":            [],
        },
    },
    # ---- INVENTARIO ----
    {
        "usuario_nombre":    "Luis",
        "usuario_apellidos": "Morales Castillo",
        "usuario_email":     "luis.inventario@callejon9.com",
        "usuario_clave":     "inventario123",
        "usuario_rol":       "4",
        "usuario_telefono":  "5578901234",
        "usuario_status":    1,
        "perfil_extra": {
            "inventario_numero":                      "I-001",
            "inventario_area":                        "almacen",
            "inventario_turno":                       "matutino",
            "inventario_puede_gestionar_proveedores": True,
            "inventario_puede_realizar_auditorias":   True,
        },
    },
]

PLATILLOS = [
    # ---- ENTRADAS ----
    {
        "nombre":             "Guacamole con Totopos",
        "descripcion":        "Aguacate fresco con jitomate, cebolla, cilantro y chile serrano. Acompañado de totopos artesanales.",
        "categoria":          "entrada",
        "precio":             89.0,
        "disponible":         True,
        "tiempo_preparacion": 10,
        "nivel_picante":      1,
        "alergenos":          [],
        "notas":              "Pedir sin chile para versión sin picante",
    },
    {
        "nombre":             "Elotes Callejeros",
        "descripcion":        "Elotes tiernos rostizados con mayonesa, queso cotija, chile en polvo y limón.",
        "categoria":          "entrada",
        "precio":             65.0,
        "disponible":         True,
        "tiempo_preparacion": 8,
        "nivel_picante":      2,
        "alergenos":          ["lacteos"],
        "notas":              "",
    },
    {
        "nombre":             "Quesadillas de Flor de Calabaza",
        "descripcion":        "Tortillas de maíz rellenas de flor de calabaza y queso Oaxaca, con crema y salsa verde.",
        "categoria":          "entrada",
        "precio":             95.0,
        "disponible":         True,
        "tiempo_preparacion": 12,
        "nivel_picante":      0,
        "alergenos":          ["lacteos", "gluten"],
        "notas":              "",
    },
    {
        "nombre":             "Sopa de Lima",
        "descripcion":        "Caldo de pollo con tiras de tortilla frita, pollo deshebrado, chile habanero y lima.",
        "categoria":          "entrada",
        "precio":             75.0,
        "disponible":         True,
        "tiempo_preparacion": 10,
        "nivel_picante":      2,
        "alergenos":          ["gluten"],
        "notas":              "Especialidad yucateca",
    },
    # ---- PLATOS FUERTES ----
    {
        "nombre":             "Arrachera a la Parrilla",
        "descripcion":        "300g de arrachera marinada a las brasas, acompañada de frijoles, guacamole, tortillas y chiles toreados.",
        "categoria":          "plato_fuerte",
        "precio":             249.0,
        "disponible":         True,
        "tiempo_preparacion": 20,
        "nivel_picante":      1,
        "alergenos":          [],
        "notas":              "Término de cocción a elección del cliente",
    },
    {
        "nombre":             "Tacos de Birria",
        "descripcion":        "3 tacos de birria de res en tortilla de maíz, bañados en consomé, cebolla, cilantro y limón.",
        "categoria":          "plato_fuerte",
        "precio":             185.0,
        "disponible":         True,
        "tiempo_preparacion": 15,
        "nivel_picante":      2,
        "alergenos":          ["gluten"],
        "notas":              "",
    },
    {
        "nombre":             "Enchiladas Verdes",
        "descripcion":        "4 enchiladas de pollo en salsa verde, crema, queso fresco y cebolla. Con arroz y frijoles.",
        "categoria":          "plato_fuerte",
        "precio":             155.0,
        "disponible":         True,
        "tiempo_preparacion": 15,
        "nivel_picante":      1,
        "alergenos":          ["lacteos", "gluten"],
        "notas":              "",
    },
    {
        "nombre":             "Chile Relleno de Queso",
        "descripcion":        "Chile poblano relleno de queso manchego, capeado y en caldillo de jitomate. Con arroz y frijoles.",
        "categoria":          "plato_fuerte",
        "precio":             165.0,
        "disponible":         True,
        "tiempo_preparacion": 18,
        "nivel_picante":      1,
        "alergenos":          ["lacteos", "huevo", "gluten"],
        "notas":              "",
    },
    {
        "nombre":             "Filete de Huachinango",
        "descripcion":        "Filete de huachinango a la veracruzana con aceitunas, alcaparras y chiles güeros. Con arroz blanco.",
        "categoria":          "plato_fuerte",
        "precio":             275.0,
        "disponible":         True,
        "tiempo_preparacion": 22,
        "nivel_picante":      0,
        "alergenos":          ["pescado"],
        "notas":              "Disponible solo fines de semana",
    },
    {
        "nombre":             "Pozole Rojo",
        "descripcion":        "Caldo de maíz cacahuazintle con carne de cerdo, chile guajillo y ancho. Con tostadas, lechuga, orégano y limón.",
        "categoria":          "plato_fuerte",
        "precio":             145.0,
        "disponible":         True,
        "tiempo_preparacion": 12,
        "nivel_picante":      2,
        "alergenos":          ["gluten"],
        "notas":              "",
    },
    # ---- BEBIDAS ----
    {
        "nombre":             "Agua de Jamaica",
        "descripcion":        "Agua fresca de flor de jamaica natural, sin azúcar o endulzada. 500ml.",
        "categoria":          "bebida",
        "precio":             35.0,
        "disponible":         True,
        "tiempo_preparacion": 2,
        "nivel_picante":      0,
        "alergenos":          [],
        "notas":              "",
    },
    {
        "nombre":             "Michelada Clásica",
        "descripcion":        "Cerveza fría con clamato, limón, salsa inglesa, salsa picante y sal en el vaso.",
        "categoria":          "bebida",
        "precio":             85.0,
        "disponible":         True,
        "tiempo_preparacion": 5,
        "nivel_picante":      2,
        "alergenos":          ["gluten"],
        "notas":              "Elige tu cerveza: Clara o Oscura",
    },
    {
        "nombre":             "Horchata",
        "descripcion":        "Bebida tradicional de arroz con canela y vainilla. 500ml.",
        "categoria":          "bebida",
        "precio":             35.0,
        "disponible":         True,
        "tiempo_preparacion": 2,
        "nivel_picante":      0,
        "alergenos":          [],
        "notas":              "",
    },
    {
        "nombre":             "Margarita de Tamarindo",
        "descripcion":        "Tequila blanco, triple sec, jugo de tamarindo natural y limón. Con borde de chile y sal.",
        "categoria":          "bebida",
        "precio":             125.0,
        "disponible":         True,
        "tiempo_preparacion": 5,
        "nivel_picante":      1,
        "alergenos":          [],
        "notas":              "También disponible sin alcohol",
    },
    {
        "nombre":             "Café de Olla",
        "descripcion":        "Café negro preparado en olla de barro con canela y piloncillo. 250ml.",
        "categoria":          "bebida",
        "precio":             45.0,
        "disponible":         True,
        "tiempo_preparacion": 5,
        "nivel_picante":      0,
        "alergenos":          [],
        "notas":              "",
    },
    # ---- POSTRES ----
    {
        "nombre":             "Pastel de Tres Leches",
        "descripcion":        "Bizcocho esponjoso bañado en tres tipos de leche, crema batida y canela.",
        "categoria":          "postre",
        "precio":             85.0,
        "disponible":         True,
        "tiempo_preparacion": 5,
        "nivel_picante":      0,
        "alergenos":          ["lacteos", "huevo", "gluten"],
        "notas":              "",
    },
    {
        "nombre":             "Churros con Chocolate",
        "descripcion":        "4 churros crujientes espolvoreados con azúcar y canela, con dip de chocolate caliente.",
        "categoria":          "postre",
        "precio":             75.0,
        "disponible":         True,
        "tiempo_preparacion": 10,
        "nivel_picante":      0,
        "alergenos":          ["gluten", "lacteos"],
        "notas":              "",
    },
    {
        "nombre":             "Flan Napolitano",
        "descripcion":        "Flan cremoso de vainilla con caramelo, crema y un toque de queso crema.",
        "categoria":          "postre",
        "precio":             70.0,
        "disponible":         True,
        "tiempo_preparacion": 3,
        "nivel_picante":      0,
        "alergenos":          ["lacteos", "huevo"],
        "notas":              "",
    },
    # ---- ESPECIALES ----
    {
        "nombre":             "Mole Negro con Pollo",
        "descripcion":        "Muslo y pierna de pollo en mole negro oaxaqueño con más de 30 ingredientes. Con arroz y tortillas.",
        "categoria":          "especial",
        "precio":             195.0,
        "disponible":         True,
        "tiempo_preparacion": 20,
        "nivel_picante":      1,
        "alergenos":          ["nueces", "gluten"],
        "notas":              "Platillo de la casa — receta de la abuela",
    },
    {
        "nombre":             "Cochinita Pibil",
        "descripcion":        "Cerdo marinado en achiote y naranja agria, cocido lentamente. Con cebolla morada encurtida y habanero.",
        "categoria":          "especial",
        "precio":             175.0,
        "disponible":         True,
        "tiempo_preparacion": 15,
        "nivel_picante":      3,
        "alergenos":          [],
        "notas":              "Solo disponibles jueves, viernes y fines de semana",
    },
]


# ===========================================================
# FUNCIONES DE SEED
# ===========================================================

def reset_tablas(app):
    """Limpia y resetea todas las tablas (solo para desarrollo)."""
    with app.app_context():
        from sqlalchemy import text
        for tabla in ("cortes_caja", "cuentas", "ventas", "platillos", "categorias_menu", "usuarios"):
            db.session.execute(text(f'TRUNCATE TABLE {tabla} RESTART IDENTITY CASCADE'))
        db.session.commit()
        print("[Seed] Tablas limpiadas.")


def seed_usuarios(app):
    with app.app_context():
        creados = 0
        omitidos = 0
        for data in USUARIOS:
            if Usuario.find_by_email(data["usuario_email"]):
                omitidos += 1
                continue
            Usuario.create(data)
            creados += 1

        print(f"[Seed] Usuarios: {creados} creados, {omitidos} ya existían.")
        print()
        print("  Credenciales de acceso:")
        print("  " + "-" * 65)
        for u in USUARIOS:
            rol_nombre = {"1": "Admin", "2": "Mesero", "3": "Cocina", "4": "Inventario"}[u["usuario_rol"]]
            print(f"  {rol_nombre:<12} {u['usuario_email']:<40} {u['usuario_clave']}")
        print("  " + "-" * 65)


def seed_categorias(app):
    categorias = [
        {"nombre": "Entrada",      "slug": "entrada",      "descripcion": "Entradas y aperitivos"},
        {"nombre": "Plato Fuerte", "slug": "plato_fuerte", "descripcion": "Platos principales"},
        {"nombre": "Bebida",       "slug": "bebida",       "descripcion": "Bebidas y refrescos"},
        {"nombre": "Postre",       "slug": "postre",       "descripcion": "Postres y dulces"},
        {"nombre": "Especial",     "slug": "especial",     "descripcion": "Platillos especiales del dia"},
    ]
    with app.app_context():
        creadas = 0
        for cat in categorias:
            if not Categoria.find_by_slug(cat["slug"]):
                Categoria.create(cat)
                creadas += 1
        print(f"[Seed] Categorias: {creadas} creadas ({len(categorias) - creadas} ya existian).")


def seed_platillos(app):
    with app.app_context():
        creados = 0
        for data in PLATILLOS:
            Platillo.create(data)
            creados += 1
        print(f"[Seed] Platillos: {creados} creados.")


MESEROS = [
    {"id": None, "nombre": "Valeria Torres"},
    {"id": None, "nombre": "Rodrigo Sánchez"},
    {"id": None, "nombre": "Ana Morales"},
]

METODOS_PAGO = ["efectivo", "tarjeta", "transferencia"]
MESAS        = ["Mesa 1", "Mesa 2", "Mesa 3", "Mesa 4", "Mesa 5", "Mesa 6", "Mesa 7", "Mesa 8"]


def seed_ventas(app, dias=30, ventas_por_dia=8):
    """Genera ventas de prueba para los últimos `dias` días."""
    with app.app_context():
        # Verificar si ya hay ventas
        if Venta.query.count() > 0:
            print("[Seed] Ventas: ya existen registros, se omite.")
            return

        # Obtener platillos disponibles
        platillos = Platillo.query.filter_by(disponible=True).all()
        if not platillos:
            print("[Seed] Ventas: no hay platillos disponibles, se omite.")
            return

        ahora = datetime.now()
        creadas = 0

        for dia_offset in range(dias, 0, -1):
            fecha_base = ahora - timedelta(days=dia_offset)
            # Más ventas en fin de semana
            num_ventas = ventas_por_dia if fecha_base.weekday() < 5 else int(ventas_por_dia * 1.5)

            for _ in range(num_ventas):
                mesero = random.choice(MESEROS)
                mesa   = random.choice(MESAS)
                hora   = random.randint(12, 22)
                minuto = random.randint(0, 59)
                fecha  = fecha_base.replace(hour=hora, minute=minuto, second=0, microsecond=0)

                # Elegir entre 1 y 4 platillos
                seleccion = random.sample(platillos, min(random.randint(1, 4), len(platillos)))
                items = []
                for p in seleccion:
                    cantidad = random.randint(1, 3)
                    precio   = float(p.precio)
                    items.append({
                        "nombre":    p.nombre,
                        "cantidad":  cantidad,
                        "precio":    precio,
                        "subtotal":  round(precio * cantidad, 2),
                        "categoria": p.categoria,
                    })

                subtotal  = round(sum(i["subtotal"] for i in items), 2)
                impuesto  = round(subtotal * 0.16, 2)
                propina   = round(subtotal * random.choice([0, 0.1, 0.15]), 2)
                descuento = round(subtotal * random.choice([0, 0, 0, 0.05]), 2)
                total     = round(subtotal + impuesto + propina - descuento, 2)

                v = Venta(
                    mesa_nombre   = mesa,
                    mesero_nombre = mesero["nombre"],
                    items         = items,
                    subtotal      = subtotal,
                    impuesto      = impuesto,
                    propina       = propina,
                    descuento     = descuento,
                    total         = total,
                    metodo_pago   = random.choice(METODOS_PAGO),
                    estado        = Venta.ESTADO_COMPLETADA,
                    fecha_creacion    = fecha,
                    fecha_completada  = fecha,
                    fecha_actualizacion = fecha,
                )
                db.session.add(v)
                creadas += 1

        db.session.commit()
        print(f"[Seed] Ventas: {creadas} ventas históricas creadas ({dias} días).")


def mostrar_resumen(app):
    with app.app_context():
        from sqlalchemy import text
        print()
        print("[Seed] Resumen final en PostgreSQL:")
        for tabla in ("usuarios", "categorias_menu", "platillos", "ventas"):
            count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            print(f"  {tabla:<20} {count} registros")


# ===========================================================
# MAIN
# ===========================================================

if __name__ == "__main__":
    reset = "--reset" in sys.argv

    app = crear_app()

    if reset:
        print("[Seed] Modo --reset: limpiando tablas...")
        reset_tablas(app)

    seed_categorias(app)
    seed_usuarios(app)
    seed_platillos(app)
    seed_ventas(app, dias=30, ventas_por_dia=8)
    mostrar_resumen(app)
    print()
    print("[Seed] Completado.")

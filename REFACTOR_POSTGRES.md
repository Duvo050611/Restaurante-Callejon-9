# Refactor: Módulo Admin — MongoDB → PostgreSQL

**Proyecto:** Restaurante Callejón 9
**Rama:** `sql-migration`
**Alcance:** Solo el módulo de administración (auth, empleados, menú). El resto del sistema (mesero, cocina, inventario, comandas, mesas, ventas) permanece en MongoDB.

---

## Contexto y motivación

El sistema originalmente usaba **MongoDB** para todo: usuarios, platillos, pedidos, inventario, etc. La decisión de migrar a PostgreSQL surgió por varias razones:

- MongoDB es flexible pero no impone esquemas, lo que llevó a datos inconsistentes en la colección de usuarios (campos faltantes, tipos mezclados).
- El módulo admin maneja datos relacionales por naturaleza: empleados con roles definidos, menú con categorías FK, estadísticas numéricas agregadas.
- Se quería explorar una migración **incremental** sin romper el trabajo de otros integrantes del equipo que aún dependen de MongoDB.

La estrategia fue: **migrar solo Admin primero**, dejando el resto del sistema intacto.

---

## Qué se migró

| Área | Antes (MongoDB) | Después (PostgreSQL) |
|---|---|---|
| Autenticación (login/logout) | `db.usuarios.find_one({"email": ...})` | `Usuario.find_by_email(email)` con SQLAlchemy |
| CRUD de empleados | Colección `usuarios` en Mongo | Tabla `usuarios` en Postgres |
| Dashboard admin (stats) | Conteos con `count_documents()` | `Usuario.count_by_rol()` con ORM |
| Gestión de menú | Colecciones `platillos` y `categorias` | Tablas `platillos` y `categorias_menu` |
| Stats operacionales | Todo en Mongo | **Mixto**: usuarios en Postgres, mesas/comandas/ventas siguen en Mongo |

---

## Arquitectura de la solución

### 1. Configuración compartida — `config/database.py`

Se creó una instancia única de `SQLAlchemy` que se registra en la app Flask:

```python
db = SQLAlchemy()

def init_db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    db.init_app(app)
```

El punto clave fue usar `pg8000` como driver en lugar de `psycopg2`, porque es puro Python y evita problemas de compilación en Windows.

### 2. Modelos SQL — `models/sql/`

Se crearon tres modelos SQLAlchemy:

- **`Usuario`** (`models/sql/usuario.py`): tabla `usuarios`, incluye columna `perfil_extra` de tipo `JSON` para almacenar datos específicos por rol (mesero, cocina, inventario) sin necesidad de tablas adicionales.
- **`Platillo`** (`models/sql/menu.py`): tabla `platillos`, con FK a `categorias_menu`.
- **`Categoria`** (`models/sql/menu.py`): tabla `categorias_menu`.

### 3. Coexistencia Postgres + MongoDB en el mismo controlador

El dashboard admin necesitaba estadísticas de ambas bases. La solución fue separar claramente las dos fuentes:

```python
# Usuarios — PostgreSQL
total_empleados = Usuario.query.filter(...).count()

# Operaciones — MongoDB (resto del sistema)
mesas_ocupadas = mongo_db.mesas.count_documents({"estado": "ocupada"})
```

Si MongoDB falla (por ejemplo, colección inexistente), las stats operacionales simplemente muestran 0 — nunca rompen la vista del admin.

---

## Obstáculos encontrados

### Obstáculo 1: Driver de PostgreSQL en Windows

**Problema:** `psycopg2` requiere compilar extensiones C. En Windows sin Visual Studio instalado, falla la instalación.

**Solución:** Se usó `pg8000`, un driver 100% Python. Requirió normalizar el prefijo de la URL de conexión:

```python
# SQLAlchemy no acepta "postgresql://" con pg8000
database_url = database_url.replace("postgresql://", "postgresql+pg8000://", 1)
```

---

### Obstáculo 2: Datos de perfil variables por rol

**Problema:** En MongoDB, cada usuario tenía campos distintos según su rol (un mesero tenía `mesas_asignadas`, un cocinero tenía `area` y `especialidad`). Modelar esto en SQL puro requería múltiples tablas con JOINs o una tabla genérica de atributos, ambas opciones complejas.

**Solución:** Se usó una columna `perfil_extra` de tipo `JSON` en la tabla `usuarios`. PostgreSQL soporta JSON nativo y permite consultas sobre él. Esto mantuvo la flexibilidad de Mongo sin perder el esquema fijo para los campos comunes.

```python
perfil_extra = db.Column(db.JSON, default=dict)
```

---

### Obstáculo 3: Compatibilidad de IDs (ObjectId vs Integer)

**Problema:** MongoDB usa `ObjectId` (string de 24 chars hexadecimales). El resto del sistema — templates, sesiones, otros controladores — asumía que `usuario["_id"]` era un ObjectId o string de ese formato. Al cambiar a PostgreSQL, el ID es un `Integer` autoincremental.

**Solución:** El método `to_dict()` del modelo retorna el ID bajo **ambas claves** para no romper código existente:

```python
def to_dict(self):
    return {
        "_id": str(self.id),   # compatibilidad con código Mongo legacy
        "id": str(self.id),    # nuevo estándar
        ...
    }
```

---

### Obstáculo 4: Inicialización de tablas vs arranque de la app

**Problema:** SQLAlchemy necesita el contexto de aplicación Flask para crear tablas. Ejecutar `db.create_all()` directamente en el módulo fallaba con `RuntimeError: No application found`.

**Solución:** Se creó un script dedicado `scripts/init_postgres.py` que instancia la app manualmente, registra todos los modelos, y luego llama `db.create_all()` dentro del contexto:

```python
with app.app_context():
    db.create_all()
    # seed del usuario admin inicial
```

---

### Obstáculo 5: La sesión Flask guardaba datos del perfil en formato Mongo

**Problema:** Al hacer login, el código guardaba en `session["perfil_mesero"]` y `session["perfil_cocina"]` datos que antes venían del documento Mongo. Esos datos tenían claves en formato Mongo (ej. `mesero_mesas`, `mesero_propina_sugerida`).

**Solución:** Se agregaron métodos estáticos `get_perfil_mesero()` y `get_perfil_cocina()` en el modelo `Usuario` que leen el `perfil_extra` JSON y devuelven la misma estructura que esperaban los templates, sin cambiar nada en las vistas ni en el resto del sistema.

---

## Archivos nuevos creados

```
config/database.py          — instancia SQLAlchemy + init_db()
models/sql/__init__.py      — paquete
models/sql/usuario.py       — modelo Usuario
models/sql/menu.py          — modelos Platillo + Categoria
scripts/init_postgres.py    — crea tablas y seed admin inicial
```

## Archivos modificados

```
app.py                                      — agrega init_db(app)
requirements.txt                            — agrega flask-sqlalchemy, pg8000
controllers/auth/AuthController.py          — usa models.sql.usuario
controllers/dashboard/dashboard_controller.py — stats mixtas Postgres/Mongo
controllers/menu/menuController.py          — usa models.sql.menu
models/Pedido.py                            — usa instancia db de config/database.py
models/DetallePedido.py                     — idem
```

---

## Cómo inicializar la base de datos

1. Crear la base de datos en PostgreSQL:
   ```sql
   CREATE DATABASE callejon9;
   ```

2. Configurar `.env`:
   ```
   DATABASE_URL=postgresql+pg8000://postgres:TU_PASSWORD@localhost:5432/callejon9
   ```

3. Ejecutar el script de inicialización:
   ```bash
   python scripts/init_postgres.py
   ```

   Esto crea las tablas e inserta un usuario administrador por defecto.

---

## Estado actual y próximos pasos

El módulo Admin está completamente operativo en PostgreSQL. Los módulos de mesero, cocina, inventario, comandas, mesas y ventas siguen usando MongoDB sin cambios.

Los siguientes módulos en cola para migrar serían **inventario** y **comandas/mesas**, que son los que tienen más datos relacionales y se beneficiarían de integridad referencial.

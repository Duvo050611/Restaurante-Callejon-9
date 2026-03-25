"""
Backup/Restore de PostgreSQL para Restaurante Callejón 9
Exporta TODOS los datos a JSON y los restaura exactamente igual.

Uso:
    python scripts/backup_restore.py export [archivo.json]
    python scripts/backup_restore.py restore <archivo.json>
    python scripts/backup_restore.py test          # ciclo completo export→drop→restore
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from decimal import Decimal
from flask import Flask
from config.database import db, init_db

# Importar modelos para que db.create_all() los conozca
from models.sql.usuario import Usuario          # noqa: F401
from models.sql.menu import Categoria, Platillo # noqa: F401
from models.sql.venta import Venta, Cuenta, CorteCaja  # noqa: F401

# Orden respetando FK: platillos → categorias_menu
TABLAS = ["usuarios", "categorias_menu", "platillos", "cuentas", "ventas", "cortes_caja"]


def crear_app():
    app = Flask(__name__)
    init_db(app)
    return app


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def exportar(app, destino=None):
    """Exporta todas las tablas PostgreSQL a un archivo JSON."""
    from sqlalchemy import text as sql
    from datetime import datetime

    if destino is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "static", "backup", f"backup_{ts}.json"
        )

    os.makedirs(os.path.dirname(destino), exist_ok=True)

    backup = {
        "_meta": {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "tablas": TABLAS,
        }
    }

    with app.app_context():
        for tabla in TABLAS:
            filas = db.session.execute(sql(f'SELECT * FROM "{tabla}"')).mappings().all()
            registros = []
            for fila in filas:
                registro = {}
                for col, val in fila.items():
                    if isinstance(val, datetime):
                        registro[col] = val.isoformat()
                    elif isinstance(val, Decimal):
                        registro[col] = float(val)
                    else:
                        registro[col] = val
                registros.append(registro)
            backup[tabla] = registros
            print(f"  {tabla:<20} {len(registros)} registros")

    with open(destino, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(destino) / 1024
    print(f"\nBackup guardado: {destino}  ({size_kb:.1f} KB)")
    return destino


# ─────────────────────────────────────────────
# RESTORE
# ─────────────────────────────────────────────

def restaurar(app, origen):
    """Lee un JSON de backup y restaura todas las tablas en PostgreSQL."""
    from sqlalchemy import text as sql

    if not os.path.exists(origen):
        print(f"ERROR: No existe el archivo '{origen}'")
        sys.exit(1)

    with open(origen, "r", encoding="utf-8") as f:
        backup = json.load(f)

    meta   = backup.get("_meta", {})
    tablas = meta.get("tablas") or [k for k in backup if not k.startswith("_")]
    orden  = [t for t in TABLAS if t in tablas]  # respetar orden FK

    print(f"Restaurando desde: {origen}")
    print(f"Tablas a restaurar: {orden}")
    print()

    with app.app_context():
        # 1. Crear schema si no existe (caso drop total de BD)
        db.create_all()
        print("  Schema verificado/creado.")

        # 2. Desactivar FK checks para truncar en cualquier orden
        db.session.execute(sql("SET session_replication_role = 'replica'"))
        db.session.flush()

        # 3. Truncar todas las tablas de una vez (en orden inverso de FK)
        for tabla in reversed(orden):
            db.session.execute(sql(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE'))
        db.session.flush()
        print("  Tablas truncadas.")

        # 4. Insertar los datos
        for tabla in orden:
            filas = backup.get(tabla, [])
            if not filas:
                print(f"  {tabla:<20} (sin registros, se omite)")
                continue

            for fila in filas:
                serializada = {}
                for k, v in fila.items():
                    if isinstance(v, (list, dict)):
                        serializada[k] = json.dumps(v, ensure_ascii=False)
                    elif isinstance(v, float) and v == int(v):
                        serializada[k] = int(v)
                    else:
                        serializada[k] = v
                cols  = ", ".join(f'"{c}"' for c in serializada)
                holds = ", ".join(f":{c}" for c in serializada)
                db.session.execute(
                    sql(f'INSERT INTO "{tabla}" ({cols}) VALUES ({holds})'),
                    serializada
                )

            # Resetear secuencia al MAX(id) para que los próximos inserts no colisionen
            db.session.execute(sql(
                f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM \"{tabla}\"), 1))"
            ))
            print(f"  {tabla:<20} {len(filas)} registros restaurados")

        # 5. Reactivar FK checks
        db.session.execute(sql("SET session_replication_role = 'origin'"))
        db.session.commit()

    print("\nRestore completado.")


# ─────────────────────────────────────────────
# TEST: ciclo completo
# ─────────────────────────────────────────────

def test_ciclo(app):
    from sqlalchemy import text as sql

    print("=" * 55)
    print("PASO 1 — Exportar")
    print("=" * 55)
    archivo = exportar(app)

    print()
    print("=" * 55)
    print("PASO 2 — DROP de todas las tablas")
    print("=" * 55)
    with app.app_context():
        db.session.execute(sql("SET session_replication_role = 'replica'"))
        for tabla in reversed(TABLAS):
            db.session.execute(sql(f'DROP TABLE IF EXISTS "{tabla}" CASCADE'))
        db.session.execute(sql("SET session_replication_role = 'origin'"))
        db.session.commit()
    print("  Todas las tablas eliminadas.")

    print()
    print("=" * 55)
    print("PASO 3 — Restaurar desde el backup")
    print("=" * 55)
    restaurar(app, archivo)

    print()
    print("=" * 55)
    print("PASO 4 — Verificar integridad")
    print("=" * 55)
    with app.app_context():
        from sqlalchemy import inspect
        tablas_bd = inspect(db.engine).get_table_names()
        print(f"  Tablas en BD: {tablas_bd}")
        for tabla in TABLAS:
            n = db.session.execute(sql(f'SELECT COUNT(*) FROM "{tabla}"')).scalar()
            # Verificar secuencia
            seq_ok = True
            try:
                max_id = db.session.execute(sql(f'SELECT MAX(id) FROM "{tabla}"')).scalar() or 0
                nxt    = db.session.execute(sql(
                    f"SELECT nextval(pg_get_serial_sequence('{tabla}', 'id'))"
                )).scalar()
                db.session.execute(sql(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), {max(max_id, nxt)})"
                ))
                seq_ok = nxt > max_id
            except Exception:
                pass
            print(f"  {tabla:<20} {n:>4} registros  secuencia_ok={seq_ok}")

    os.remove(archivo)
    print()
    print("=" * 55)
    print("CICLO COMPLETO EXITOSO")
    print("=" * 55)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("export", "restore", "test"):
        print(__doc__)
        sys.exit(1)

    app = crear_app()
    cmd = sys.argv[1]

    if cmd == "export":
        destino = sys.argv[2] if len(sys.argv) > 2 else None
        print("Exportando base de datos PostgreSQL...")
        exportar(app, destino)

    elif cmd == "restore":
        if len(sys.argv) < 3:
            print("Uso: python scripts/backup_restore.py restore <archivo.json>")
            sys.exit(1)
        restaurar(app, sys.argv[2])

    elif cmd == "test":
        test_ciclo(app)

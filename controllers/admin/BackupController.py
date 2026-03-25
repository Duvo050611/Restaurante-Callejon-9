"""
BackupController — PostgreSQL only
Tablas: usuarios, categorias_menu, platillos, ventas, cuentas, cortes_caja
"""
import os
import json
import zipfile
import threading
import schedule
import time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session
from config.database import db as pg_db
from controllers.notificaciones.notificacion_controller import NotificacionSistemaController
from sqlalchemy import text

# Orden de restauración respetando FK:
# platillos → categorias_menu  (FK en slug)
# el resto no tiene dependencias entre sí
PG_TABLES_RESTORE_ORDER = [
    "usuarios",
    "categorias_menu",
    "platillos",
    "cuentas",
    "ventas",
    "cortes_caja",
]

# Archivo de configuración de auto-backup (sin MongoDB)
_AUTO_BACKUP_CONFIG_PATH = os.path.join("static", "backup", ".auto_backup_config.json")


def _load_auto_backup_config():
    try:
        if os.path.exists(_AUTO_BACKUP_CONFIG_PATH):
            with open(_AUTO_BACKUP_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_auto_backup_config(cfg):
    os.makedirs(os.path.dirname(_AUTO_BACKUP_CONFIG_PATH), exist_ok=True)
    with open(_AUTO_BACKUP_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class BackupController:

    _backup_thread = None
    _backup_running = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_admin_password(password):
        admin_password = os.environ.get("ADMIN_RESTORE_PASSWORD")
        if not admin_password:
            return True
        return password == admin_password

    @staticmethod
    def _export_pg_tables(tables=None):
        """Exporta las tablas PostgreSQL indicadas como lista de dicts serializables."""
        tables = tables or PG_TABLES_RESTORE_ORDER
        data = {}
        for table in tables:
            try:
                rows = pg_db.session.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
                serialized = []
                for row in rows:
                    record = {}
                    for k, v in row.items():
                        if isinstance(v, datetime):
                            record[k] = v.isoformat()
                        elif hasattr(v, "__class__") and v.__class__.__name__ == "Decimal":
                            record[k] = float(v)
                        else:
                            record[k] = v
                    serialized.append(record)
                data[table] = serialized
            except Exception as e:
                print(f"Error exportando tabla {table}: {e}")
                data[table] = []
        return data

    @staticmethod
    def _ensure_database_exists():
        """Si la base de datos no existe, la crea conectándose a 'postgres'."""
        import re
        db_url = os.environ.get("DATABASE_URL", "")
        match = re.match(r"postgresql://([^:]+):([^@]+)@([^:/]+):?(\d*)/(.+)", db_url)
        if not match:
            return
        user, password, host, port, dbname = match.groups()
        port = int(port) if port else 5432
        try:
            import pg8000.dbapi as pg
            conn = pg.connect(host=host, port=port, user=user, password=password, database="postgres")
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{dbname}"')
                print(f"Base de datos '{dbname}' creada.")
            conn.close()
        except Exception as e:
            print(f"Advertencia al verificar/crear BD: {e}")

    @staticmethod
    def _restore_pg_tables(data):
        """
        Restaura tablas PostgreSQL desde un dict.
        - Crea la BD si no existe (caso drop completo de BD).
        - Crea tablas si no existen.
        - Orden respeta FK (platillos → categorias_menu).
        - Trunca con CASCADE y resetea secuencias tras insertar.
        """
        # Garantizar que la base de datos existe
        BackupController._ensure_database_exists()
        # Garantizar que el schema existe antes de intentar truncar/insertar
        pg_db.create_all()

        restored = 0
        order = [t for t in PG_TABLES_RESTORE_ORDER if t in data]

        # Deshabilitar FK checks durante la restauración
        try:
            pg_db.session.execute(text("SET session_replication_role = 'replica'"))
        except Exception:
            pass

        for table in order:
            rows = data.get(table) or []
            try:
                pg_db.session.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))
                pg_db.session.flush()

                for record in rows:
                    serialized = {}
                    for k, v in record.items():
                        if isinstance(v, (list, dict)):
                            serialized[k] = json.dumps(v, ensure_ascii=False)
                        elif isinstance(v, float) and v == int(v):
                            # Backups viejos guardan enteros como 1.0 — revertir a int
                            serialized[k] = int(v)
                        else:
                            serialized[k] = v
                    cols         = ", ".join(f'"{c}"' for c in serialized.keys())
                    placeholders = ", ".join(f":{c}" for c in serialized.keys())
                    pg_db.session.execute(
                        text(f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders})'),
                        serialized
                    )

                # Resetear secuencia al MAX(id) restaurado para que los próximos inserts no colisionen
                pg_db.session.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM \"{table}\"), 1))"
                ))
                restored += 1
            except Exception as e:
                pg_db.session.rollback()
                try:
                    pg_db.session.execute(text("SET session_replication_role = 'origin'"))
                except Exception:
                    pass
                raise RuntimeError(f"Error restaurando tabla '{table}': {e}") from e

        try:
            pg_db.session.execute(text("SET session_replication_role = 'origin'"))
        except Exception:
            pass

        pg_db.session.commit()
        return restored

    # ------------------------------------------------------------------
    # Vista principal
    # ------------------------------------------------------------------

    @staticmethod
    def index():
        backup_dir = os.path.join("static", "backup")
        os.makedirs(backup_dir, exist_ok=True)

        all_files = []
        try:
            all_files = sorted(
                [f for f in os.listdir(backup_dir)
                 if os.path.isfile(os.path.join(backup_dir, f)) and not f.startswith(".")],
                key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)),
                reverse=True,
            )
        except Exception as e:
            print(f"Error al listar archivos: {e}")

        page     = request.args.get("page", 1, type=int)
        per_page = 10
        total_files  = len(all_files)
        total_pages  = max(1, (total_files + per_page - 1) // per_page)
        files    = all_files[(page - 1) * per_page: page * per_page]

        auto_backup_config = _load_auto_backup_config()

        if auto_backup_config.get("enabled"):
            BackupController._schedule_auto_backups(
                auto_backup_config.get("frequency", "daily"),
                auto_backup_config.get("hour", "02:00"),
            )

        return render_template(
            "admin/admin/backup.html",
            files=files,
            pg_tables=PG_TABLES_RESTORE_ORDER,
            page=page,
            total_pages=total_pages,
            total_files=total_files,
            auto_backup_config=auto_backup_config,
        )

    # ------------------------------------------------------------------
    # Crear backup
    # ------------------------------------------------------------------

    @staticmethod
    def create():
        admin_password = request.form.get("admin_password")
        if not admin_password:
            flash("Se requiere contraseña de administrador para crear un respaldo", "error")
            return redirect(url_for("routes.admin_backup_view"))

        if not BackupController._validate_admin_password(admin_password):
            flash("Contraseña de administrador incorrecta", "error")
            return redirect(url_for("routes.admin_backup_view"))

        backup_dir = os.path.join("static", "backup")
        os.makedirs(backup_dir, exist_ok=True)

        selected_tables = request.form.getlist("pg_tables")
        file_format     = request.form.get("format", "json")
        custom_name     = request.form.get("backup_name", "respaldo").strip() or "respaldo"

        if not selected_tables:
            flash("Debes seleccionar al menos una tabla para respaldar", "error")
            return redirect(url_for("routes.admin_backup_view"))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"{custom_name}_{timestamp}.{file_format}"
        full_path = os.path.join(backup_dir, filename)

        try:
            pg_export = BackupController._export_pg_tables(selected_tables)

            backup_data = {
                "_meta": {
                    "created_at":      datetime.utcnow().isoformat(),
                    "source":          "callejon9",
                    "postgres_tables": selected_tables,
                    "version":         "2.0",
                },
            }
            backup_data.update(pg_export)

            if file_format == "zip":
                temp_json = full_path.replace(".zip", ".json")
                with open(temp_json, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=4)
                with zipfile.ZipFile(full_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(temp_json, os.path.basename(temp_json))
                os.remove(temp_json)
            else:
                with open(full_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=4)

            flash(f"Respaldo '{filename}' generado. {len(selected_tables)} tabla(s) incluidas.", "success")

            try:
                NotificacionSistemaController.notificar_backup_creado(
                    usuario_id=session.get("usuario_id"),
                    nombre_archivo=filename,
                )
            except Exception:
                pass

        except Exception as e:
            print(f"Error al generar respaldo: {e}")
            flash(f"Error al generar respaldo: {str(e)}", "error")

        return redirect(url_for("routes.admin_backup_view"))

    # ------------------------------------------------------------------
    # Eliminar
    # ------------------------------------------------------------------

    @staticmethod
    def delete_file(filename):
        try:
            file_path = os.path.join("static", "backup", filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                flash(f"Archivo '{filename}' eliminado correctamente.", "success")
            else:
                flash("El archivo no existe.", "error")
        except Exception as e:
            flash(f"Error al eliminar: {str(e)}", "error")
        return redirect(url_for("routes.admin_backup_view"))

    @staticmethod
    def delete_file_with_auth():
        filename = request.view_args.get("filename", "")
        try:
            data = request.get_json()
            admin_password = data.get("admin_password") if data else None
        except Exception:
            admin_password = None

        if not admin_password:
            return jsonify({"success": False, "message": "Se requiere contraseña de administrador"})
        if not BackupController._validate_admin_password(admin_password):
            return jsonify({"success": False, "message": "Contraseña de administrador incorrecta"})

        file_path = os.path.join("static", "backup", filename)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "message": "El archivo no existe"})

        try:
            os.remove(file_path)
            return jsonify({"success": True, "message": f"Archivo '{filename}' eliminado correctamente"})
        except Exception as e:
            return jsonify({"success": False, "message": f"Error al eliminar: {str(e)}"})

    # ------------------------------------------------------------------
    # Descarga con auth
    # ------------------------------------------------------------------

    @staticmethod
    def download_with_auth():
        filename = request.view_args.get("filename", "")
        try:
            data = request.get_json()
            admin_password = data.get("admin_password") if data else None
        except Exception:
            admin_password = None

        if not admin_password:
            return jsonify({"success": False, "message": "Se requiere contraseña de administrador"})
        if not BackupController._validate_admin_password(admin_password):
            return jsonify({"success": False, "message": "Contraseña de administrador incorrecta"})

        file_path = os.path.join("static", "backup", filename)
        if not os.path.exists(file_path):
            return jsonify({"success": False, "message": "El archivo no existe"})

        return jsonify({"success": True, "message": "Descarga autorizada"})

    # ------------------------------------------------------------------
    # Restaurar
    # ------------------------------------------------------------------

    @staticmethod
    def restore():
        admin_password = request.form.get("admin_password")
        if not admin_password:
            flash("Se requiere contraseña de administrador para restaurar", "error")
            return redirect(url_for("routes.admin_backup_view"))

        if not BackupController._validate_admin_password(admin_password):
            flash("Contraseña de administrador incorrecta", "error")
            return redirect(url_for("routes.admin_backup_view"))

        try:
            data = BackupController._read_backup_file()
        except Exception as e:
            flash(f"Error al leer el archivo de respaldo: {str(e)}", "error")
            return redirect(url_for("routes.admin_backup_view"))

        meta       = data.pop("_meta", {})
        pg_tables  = meta.get("postgres_tables") or [k for k in data if k in PG_TABLES_RESTORE_ORDER]

        pg_data = {t: data[t] for t in pg_tables if t in data}
        if not pg_data:
            flash("El archivo de respaldo no contiene datos de PostgreSQL.", "error")
            return redirect(url_for("routes.admin_backup_view"))

        try:
            restored = BackupController._restore_pg_tables(pg_data)
            flash(f"Base de datos restaurada correctamente: {restored} tabla(s) PostgreSQL.", "success")
        except Exception as e:
            flash(f"Error restaurando PostgreSQL: {str(e)}", "error")

        return redirect(url_for("routes.admin_backup_view"))

    @staticmethod
    def _read_backup_file():
        server_file = request.form.get("server_file")

        if server_file:
            file_path = os.path.join("static", "backup", server_file)
            if server_file.endswith(".zip"):
                return BackupController._extract_json_from_zip(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)

        if "backup_file" in request.files:
            file = request.files["backup_file"]
            if not file.filename:
                raise ValueError("No se seleccionó ningún archivo")
            if file.filename.endswith(".zip"):
                import tempfile, shutil
                tmp = tempfile.mkdtemp()
                zip_path = os.path.join(tmp, file.filename)
                file.save(zip_path)
                data = BackupController._extract_json_from_zip(zip_path)
                shutil.rmtree(tmp)
                return data
            return json.loads(file.read().decode("utf-8"))

        raise ValueError("No hay origen de datos para restaurar")

    @staticmethod
    def _extract_json_from_zip(zip_path):
        import tempfile, shutil
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        json_files = [f for f in os.listdir(tmp) if f.endswith(".json")]
        if not json_files:
            shutil.rmtree(tmp)
            raise ValueError("No se encontró JSON dentro del ZIP")
        with open(os.path.join(tmp, json_files[0]), "r", encoding="utf-8") as f:
            data = json.load(f)
        shutil.rmtree(tmp)
        return data

    # ------------------------------------------------------------------
    # Auto-backup
    # ------------------------------------------------------------------

    @staticmethod
    def configure_auto_backup():
        try:
            payload        = request.json
            enabled        = payload.get("enabled", False)
            frequency      = payload.get("frequency", "daily")
            hour           = payload.get("hour", "02:00")
            retention_days = int(payload.get("retention_days", 30))

            cfg = {
                "enabled":        enabled,
                "frequency":      frequency,
                "hour":           hour,
                "retention_days": retention_days,
                "updated_at":     datetime.utcnow().isoformat(),
            }
            _save_auto_backup_config(cfg)

            if enabled:
                BackupController._schedule_auto_backups(frequency, hour)
                message = "Respaldos automáticos activados"
            else:
                BackupController._backup_running = False
                message = "Respaldos automáticos desactivados"

            return jsonify({"success": True, "message": message})

        except Exception as e:
            return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

    @staticmethod
    def _schedule_auto_backups(frequency, hour):
        if BackupController._backup_running:
            return

        BackupController._backup_running = True

        def run_scheduler():
            schedule.clear()
            if frequency == "daily":
                schedule.every().day.at(hour).do(BackupController._ejecutar_respaldo_automatico)
            elif frequency == "weekly":
                schedule.every().monday.at(hour).do(BackupController._ejecutar_respaldo_automatico)
            elif frequency == "monthly":
                schedule.every(30).days.at(hour).do(BackupController._ejecutar_respaldo_automatico)

            print(f"Auto-backup programado: {frequency} a las {hour}")
            while BackupController._backup_running:
                schedule.run_pending()
                time.sleep(60)

        if BackupController._backup_thread is None or not BackupController._backup_thread.is_alive():
            BackupController._backup_thread = threading.Thread(target=run_scheduler, daemon=True)
            BackupController._backup_thread.start()

    @staticmethod
    def _ejecutar_respaldo_automatico():
        try:
            print("Ejecutando respaldo automático...")
            backup_dir = os.path.join("static", "backup")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"auto_backup_{timestamp}.json"
            full_path = os.path.join(backup_dir, filename)

            pg_export = BackupController._export_pg_tables()
            backup_data = {
                "_meta": {
                    "created_at":      datetime.utcnow().isoformat(),
                    "source":          "callejon9_auto",
                    "postgres_tables": PG_TABLES_RESTORE_ORDER,
                    "version":         "2.0",
                },
            }
            backup_data.update(pg_export)

            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)

            print(f"Respaldo automático creado: {filename}")
            BackupController._limpiar_respaldos_antiguos()

        except Exception as e:
            print(f"Error en respaldo automático: {e}")

    @staticmethod
    def _limpiar_respaldos_antiguos():
        try:
            cfg = _load_auto_backup_config()
            retention_days = int(cfg.get("retention_days", 30))
            backup_dir = os.path.join("static", "backup")
            if not os.path.exists(backup_dir):
                return
            now     = datetime.now()
            deleted = 0
            for fname in os.listdir(backup_dir):
                if fname.startswith("auto_backup_"):
                    fpath = os.path.join(backup_dir, fname)
                    if (now - datetime.fromtimestamp(os.path.getmtime(fpath))).days > retention_days:
                        os.remove(fpath)
                        deleted += 1
            if deleted:
                print(f"Eliminados {deleted} respaldos antiguos")
        except Exception as e:
            print(f"Error al limpiar respaldos: {e}")

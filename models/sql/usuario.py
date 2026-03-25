"""
Modelo Usuario - PostgreSQL (SQLAlchemy)
Roles: 1=Admin, 2=Mesero, 3=Cocina, 4=Inventario
"""
from datetime import datetime
from config.database import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    usuario_nombre = db.Column(db.String(100), nullable=False)
    usuario_apellidos = db.Column(db.String(100), nullable=False)
    usuario_email = db.Column(db.String(150), unique=True, nullable=False)
    usuario_clave = db.Column(db.String(255), nullable=False)
    usuario_rol = db.Column(db.String(2), nullable=False)   # "1"|"2"|"3"|"4"
    usuario_telefono = db.Column(db.String(20), nullable=True)
    usuario_foto = db.Column(db.String(255), nullable=True)
    usuario_status = db.Column(db.Integer, default=1)       # 1=activo, 0=inactivo
    usuario_tokensession = db.Column(db.String(255), nullable=True)

    # 2FA (deshabilitado en esta versión, campos por compatibilidad)
    twofa_enabled = db.Column(db.Boolean, default=False)
    twofa_tipo = db.Column(db.String(20), nullable=True)
    twofa_secret = db.Column(db.String(100), nullable=True)
    twofa_telefono = db.Column(db.String(20), nullable=True)

    # Datos específicos del rol (JSONB para flexibilidad)
    perfil_extra = db.Column(db.JSON, default=dict)

    fecha_conexion = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ------------------------------------------------------------------
    # Métodos de consulta
    # ------------------------------------------------------------------

    @classmethod
    def find_by_email(cls, email):
        return cls.query.filter_by(usuario_email=email.lower()).first()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.get(int(id))

    @classmethod
    def find_by_rol(cls, rol):
        return cls.query.filter_by(usuario_rol=str(rol)).all()

    @classmethod
    def find_activos(cls):
        return cls.query.filter_by(usuario_status=1).all()

    @classmethod
    def find_all(cls):
        return cls.query.filter(cls.usuario_rol.in_(["1", "2", "3", "4"])).all()

    # ------------------------------------------------------------------
    # Conteos para dashboard
    # ------------------------------------------------------------------

    @classmethod
    def count_activos(cls):
        return cls.query.filter_by(usuario_status=1).count()

    @classmethod
    def count_by_rol(cls, rol):
        return cls.query.filter_by(usuario_rol=str(rol)).count()

    # ------------------------------------------------------------------
    # Métodos de comando
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, data):
        usuario = cls(
            usuario_nombre=data["usuario_nombre"],
            usuario_apellidos=data["usuario_apellidos"],
            usuario_email=data["usuario_email"].lower(),
            usuario_clave=data["usuario_clave"],
            usuario_rol=str(data["usuario_rol"]),
            usuario_telefono=data.get("usuario_telefono", ""),
            usuario_foto=data.get("usuario_foto"),
            usuario_status=data.get("usuario_status", 1),
            twofa_enabled=data.get("twofa_enabled", False),
            perfil_extra=data.get("perfil_extra", {}),
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario

    @classmethod
    def update(cls, id, data):
        usuario = cls.find_by_id(id)
        if not usuario:
            return None
        for key, value in data.items():
            if hasattr(usuario, key):
                setattr(usuario, key, value)
        usuario.updated_at = datetime.utcnow()
        db.session.commit()
        return usuario

    @classmethod
    def update_session_token(cls, user_id, token, status):
        usuario = cls.find_by_id(user_id)
        if not usuario:
            return
        usuario.usuario_tokensession = token
        usuario.usuario_status = status
        usuario.updated_at = datetime.utcnow()
        if status == 1:
            usuario.fecha_conexion = datetime.utcnow()
        elif status == 0:
            usuario.fecha_conexion = None
        db.session.commit()

    @classmethod
    def update_2fa_status(cls, user_id, is_enabled, tipo=None, secret=None, telefono=None):
        usuario = cls.find_by_id(user_id)
        if not usuario:
            return None
        usuario.twofa_enabled = is_enabled
        usuario.twofa_tipo = tipo
        usuario.twofa_secret = secret
        usuario.twofa_telefono = telefono
        usuario.updated_at = datetime.utcnow()
        db.session.commit()
        return usuario

    @classmethod
    def soft_delete(cls, id):
        """Desactiva un usuario (status=0)"""
        usuario = cls.find_by_id(id)
        if not usuario:
            return False
        usuario.usuario_status = 0
        usuario.updated_at = datetime.utcnow()
        db.session.commit()
        return True

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def to_dict(self):
        return {
            "_id": str(self.id),
            "id": str(self.id),
            "usuario_nombre": self.usuario_nombre,
            "usuario_apellidos": self.usuario_apellidos,
            "usuario_email": self.usuario_email,
            "usuario_rol": self.usuario_rol,
            "usuario_telefono": self.usuario_telefono,
            "usuario_foto": self.usuario_foto,
            "usuario_status": self.usuario_status,
            "twofa_enabled": self.twofa_enabled,
            "perfil_extra": self.perfil_extra or {},
            "fecha_conexion": self.fecha_conexion.isoformat() if self.fecha_conexion else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    # ------------------------------------------------------------------
    # Helpers de perfil por rol (compatibilidad con el resto del sistema)
    # ------------------------------------------------------------------

    @staticmethod
    def get_perfil_mesero(usuario_obj):
        if not usuario_obj or str(usuario_obj.usuario_rol) != "2":
            return None
        extra = usuario_obj.perfil_extra or {}
        return {
            "numero_empleado": extra.get("mesero_numero"),
            "turno": extra.get("mesero_turno"),
            "mesas_asignadas": extra.get("mesero_mesas", []),
            "puede_cerrar_cuenta": extra.get("mesero_puede_cerrar_cuenta", False),
            "puede_aplicar_descuento": extra.get("mesero_puede_aplicar_descuento", False),
            "propinas": {
                "sugerida": extra.get("mesero_propina_sugerida", 10),
                "acumulada_dia": extra.get("mesero_propina_acumulada_dia", 0),
            },
            "rendimiento": {
                "ventas_promedio_dia": extra.get("mesero_ventas_promedio_dia", 0),
                "calificacion_cliente": extra.get("mesero_calificacion_cliente", 0),
            },
        }

    @staticmethod
    def get_perfil_cocina(usuario_obj):
        if not usuario_obj or str(usuario_obj.usuario_rol) != "3":
            return None
        extra = usuario_obj.perfil_extra or {}
        return {
            "numero_empleado": extra.get("cocina_numero"),
            "puesto": extra.get("cocina_puesto"),
            "area": extra.get("cocina_area"),
            "turno": extra.get("cocina_turno"),
            "especialidad": extra.get("cocina_especialidad", []),
            "puede_modificar_menu": extra.get("cocina_puede_modificar_menu", False),
            "puede_ver_recetas_completas": extra.get("cocina_puede_ver_recetas_completas", False),
            "certificaciones": extra.get("cocina_certificaciones", []),
        }

    def __repr__(self):
        return f"<Usuario {self.usuario_email} rol={self.usuario_rol}>"

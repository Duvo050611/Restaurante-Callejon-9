"""
Modelos de Ventas — PostgreSQL (SQLAlchemy)
Tablas: ventas, cuentas, cortes_caja
"""
from datetime import datetime, timedelta
from config.database import db
from sqlalchemy import func, text


class Venta(db.Model):
    __tablename__ = "ventas"

    ESTADO_PENDIENTE  = "pendiente"
    ESTADO_COMPLETADA = "completada"
    ESTADO_CANCELADA  = "cancelada"

    id                  = db.Column(db.Integer, primary_key=True)
    mesa_id             = db.Column(db.String(50),  nullable=True)
    mesa_nombre         = db.Column(db.String(50),  default="")
    mesero_id           = db.Column(db.String(20),  nullable=True)   # str(usuario.id)
    mesero_nombre       = db.Column(db.String(150), default="")
    cliente_nombre      = db.Column(db.String(150), default="")
    items               = db.Column(db.JSON,        default=list)    # [{nombre, cantidad, precio, subtotal}]
    subtotal            = db.Column(db.Numeric(10, 2), default=0)
    impuesto            = db.Column(db.Numeric(10, 2), default=0)
    descuento           = db.Column(db.Numeric(10, 2), default=0)
    propina             = db.Column(db.Numeric(10, 2), default=0)
    total               = db.Column(db.Numeric(10, 2), default=0)
    metodo_pago         = db.Column(db.String(20),  default="efectivo")
    estado              = db.Column(db.String(20),  default="pendiente")
    notas               = db.Column(db.Text,        default="")
    motivo_cancelacion  = db.Column(db.Text,        nullable=True)
    fecha_completada    = db.Column(db.DateTime,    nullable=True)
    fecha_cancelada     = db.Column(db.DateTime,    nullable=True)
    fecha_creacion      = db.Column(db.DateTime,    default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @classmethod
    def find_all(cls, filtro=None):
        q = cls.query
        if filtro:
            if "estado" in filtro:
                q = q.filter_by(estado=filtro["estado"])
        return [v.to_dict() for v in q.order_by(cls.fecha_creacion.desc()).all()]

    @classmethod
    def find_by_id(cls, id):
        v = cls.query.get(int(id))
        return v.to_dict() if v else None

    @classmethod
    def find_by_mesa(cls, mesa_id):
        return [v.to_dict() for v in
                cls.query.filter_by(mesa_id=str(mesa_id))
                         .order_by(cls.fecha_creacion.desc()).all()]

    @classmethod
    def find_by_mesero(cls, mesero_id):
        return [v.to_dict() for v in
                cls.query.filter_by(mesero_id=str(mesero_id))
                         .order_by(cls.fecha_creacion.desc()).all()]

    @classmethod
    def find_by_fecha(cls, fecha_inicio, fecha_fin):
        return [v.to_dict() for v in
                cls.query.filter(
                    cls.fecha_creacion >= fecha_inicio,
                    cls.fecha_creacion <= fecha_fin
                ).order_by(cls.fecha_creacion.desc()).all()]

    @classmethod
    def find_hoy(cls):
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return cls.find_by_fecha(hoy, hoy + timedelta(days=1))

    @classmethod
    def get_estadisticas_hoy(cls):
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ventas = cls.query.filter(cls.fecha_creacion >= hoy).all()
        total_ventas      = sum(float(v.total or 0) for v in ventas)
        num_transacciones = len(ventas)
        ticket_promedio   = total_ventas / num_transacciones if num_transacciones else 0
        cuentas_pendientes = sum(1 for v in ventas if v.estado == cls.ESTADO_PENDIENTE)
        return {
            "total_ventas":        total_ventas,
            "num_transacciones":   num_transacciones,
            "ticket_promedio":     round(ticket_promedio, 2),
            "cuentas_pendientes":  cuentas_pendientes,
        }

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, data):
        v = cls(
            mesa_id        = str(data.get("mesa_id", "") or ""),
            mesa_nombre    = data.get("mesa_nombre", ""),
            mesero_id      = str(data.get("mesero_id", "") or ""),
            mesero_nombre  = data.get("mesero_nombre", ""),
            cliente_nombre = data.get("cliente_nombre", ""),
            items          = data.get("items", []),
            subtotal       = float(data.get("subtotal", 0)),
            impuesto       = float(data.get("impuesto", 0)),
            descuento      = float(data.get("descuento", 0)),
            propina        = float(data.get("propina", 0)),
            total          = float(data.get("total", 0)),
            metodo_pago    = data.get("metodo_pago", "efectivo"),
            estado         = data.get("estado", cls.ESTADO_PENDIENTE),
            notas          = data.get("notas", ""),
        )
        db.session.add(v)
        db.session.commit()
        return str(v.id)

    @classmethod
    def update(cls, id, data):
        v = cls.query.get(int(id))
        if not v:
            return False
        campos = ["mesa_id","mesa_nombre","mesero_id","mesero_nombre",
                  "cliente_nombre","items","subtotal","impuesto",
                  "descuento","propina","total","metodo_pago","estado","notas"]
        for campo in campos:
            if campo in data:
                setattr(v, campo, data[campo])
        v.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        return True

    @classmethod
    def completar(cls, id, metodo_pago=None):
        v = cls.query.get(int(id))
        if not v:
            return False
        v.estado           = cls.ESTADO_COMPLETADA
        v.fecha_completada = datetime.utcnow()
        if metodo_pago:
            v.metodo_pago = metodo_pago
        db.session.commit()
        return True

    @classmethod
    def cancelar(cls, id, motivo=None):
        v = cls.query.get(int(id))
        if not v:
            return False
        v.estado              = cls.ESTADO_CANCELADA
        v.motivo_cancelacion  = motivo or "Sin motivo"
        v.fecha_cancelada     = datetime.utcnow()
        db.session.commit()
        return True

    @classmethod
    def delete(cls, id):
        v = cls.query.get(int(id))
        if not v:
            return False
        db.session.delete(v)
        db.session.commit()
        return True

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def to_dict(self):
        return {
            "_id":               str(self.id),
            "id":                str(self.id),
            "mesa_id":           self.mesa_id,
            "mesa_nombre":       self.mesa_nombre,
            "mesero_id":         self.mesero_id,
            "mesero_nombre":     self.mesero_nombre,
            "cliente_nombre":    self.cliente_nombre,
            "items":             self.items or [],
            "subtotal":          float(self.subtotal or 0),
            "impuesto":          float(self.impuesto or 0),
            "descuento":         float(self.descuento or 0),
            "propina":           float(self.propina or 0),
            "total":             float(self.total or 0),
            "metodo_pago":       self.metodo_pago,
            "estado":            self.estado,
            "notas":             self.notas,
            "fecha_creacion":    self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_completada":  self.fecha_completada.isoformat() if self.fecha_completada else None,
        }


class Cuenta(db.Model):
    __tablename__ = "cuentas"

    id                  = db.Column(db.Integer,     primary_key=True)
    mesa_id             = db.Column(db.String(50),  nullable=True)
    mesa_nombre         = db.Column(db.String(50),  default="")
    mesero_id           = db.Column(db.String(20),  nullable=True)
    mesero_nombre       = db.Column(db.String(150), default="")
    cliente_nombre      = db.Column(db.String(150), default="")
    num_personas        = db.Column(db.Integer,     default=1)
    estado              = db.Column(db.String(20),  default="abierta")
    metodo_pago         = db.Column(db.String(20),  nullable=True)
    total               = db.Column(db.Numeric(10, 2), default=0)
    propina             = db.Column(db.Numeric(10, 2), default=0)
    fecha_cierre        = db.Column(db.DateTime,    nullable=True)
    fecha_creacion      = db.Column(db.DateTime,    default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def find_abiertas(cls):
        return [c.to_dict() for c in
                cls.query.filter_by(estado="abierta")
                         .order_by(cls.fecha_creacion.desc()).all()]

    @classmethod
    def find_by_id(cls, id):
        c = cls.query.get(int(id))
        return c.to_dict() if c else None

    @classmethod
    def create(cls, data):
        c = cls(
            mesa_id       = str(data.get("mesa_id", "") or ""),
            mesa_nombre   = data.get("mesa_nombre", ""),
            mesero_id     = str(data.get("mesero_id", "") or ""),
            mesero_nombre = data.get("mesero_nombre", ""),
            cliente_nombre= data.get("cliente_nombre", ""),
            num_personas  = int(data.get("num_personas", 1)),
            estado        = "abierta",
        )
        db.session.add(c)
        db.session.commit()
        return str(c.id)

    @classmethod
    def cerrar(cls, id, datos_pago):
        c = cls.query.get(int(id))
        if not c:
            return False
        c.estado      = "cerrada"
        c.metodo_pago = datos_pago.get("metodo_pago")
        c.total       = float(datos_pago.get("total", 0))
        c.propina     = float(datos_pago.get("propina", 0))
        c.fecha_cierre= datetime.utcnow()
        db.session.commit()
        return True

    def to_dict(self):
        return {
            "_id":           str(self.id),
            "id":            str(self.id),
            "mesa_id":       self.mesa_id,
            "mesa_nombre":   self.mesa_nombre,
            "mesero_id":     self.mesero_id,
            "mesero_nombre": self.mesero_nombre,
            "cliente_nombre":self.cliente_nombre,
            "num_personas":  self.num_personas,
            "estado":        self.estado,
            "metodo_pago":   self.metodo_pago,
            "total":         float(self.total or 0),
            "propina":       float(self.propina or 0),
            "fecha_creacion":self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            "fecha_cierre":  self.fecha_cierre.isoformat() if self.fecha_cierre else None,
        }


class CorteCaja(db.Model):
    __tablename__ = "cortes_caja"

    id                  = db.Column(db.Integer,     primary_key=True)
    usuario_id          = db.Column(db.String(20),  nullable=True)
    usuario_nombre      = db.Column(db.String(150), default="")
    fecha_inicio        = db.Column(db.DateTime,    nullable=True)
    fecha_fin           = db.Column(db.DateTime,    nullable=True)
    total_ventas        = db.Column(db.Numeric(10, 2), default=0)
    total_efectivo      = db.Column(db.Numeric(10, 2), default=0)
    total_tarjeta       = db.Column(db.Numeric(10, 2), default=0)
    total_transferencia = db.Column(db.Numeric(10, 2), default=0)
    total_propinas      = db.Column(db.Numeric(10, 2), default=0)
    num_transacciones   = db.Column(db.Integer,     default=0)
    notas               = db.Column(db.Text,        default="")
    fecha_creacion      = db.Column(db.DateTime,    default=datetime.utcnow)

    @classmethod
    def find_all(cls):
        return [c.to_dict() for c in
                cls.query.order_by(cls.fecha_creacion.desc()).all()]

    @classmethod
    def find_by_id(cls, id):
        c = cls.query.get(int(id))
        return c.to_dict() if c else None

    @classmethod
    def create(cls, data):
        c = cls(
            usuario_id          = str(data.get("usuario_id", "") or ""),
            usuario_nombre      = data.get("usuario_nombre", ""),
            fecha_inicio        = data.get("fecha_inicio"),
            fecha_fin           = data.get("fecha_fin"),
            total_ventas        = float(data.get("total_ventas", 0)),
            total_efectivo      = float(data.get("total_efectivo", 0)),
            total_tarjeta       = float(data.get("total_tarjeta", 0)),
            total_transferencia = float(data.get("total_transferencia", 0)),
            total_propinas      = float(data.get("total_propinas", 0)),
            num_transacciones   = int(data.get("num_transacciones", 0)),
            notas               = data.get("notas", ""),
        )
        db.session.add(c)
        db.session.commit()
        return str(c.id)

    def to_dict(self):
        return {
            "_id":               str(self.id),
            "id":                str(self.id),
            "usuario_id":        self.usuario_id,
            "usuario_nombre":    self.usuario_nombre,
            "total_ventas":      float(self.total_ventas or 0),
            "total_efectivo":    float(self.total_efectivo or 0),
            "total_tarjeta":     float(self.total_tarjeta or 0),
            "total_transferencia": float(self.total_transferencia or 0),
            "total_propinas":    float(self.total_propinas or 0),
            "num_transacciones": self.num_transacciones,
            "notas":             self.notas,
            "fecha_inicio":      self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            "fecha_fin":         self.fecha_fin.isoformat() if self.fecha_fin else None,
            "fecha_creacion":    self.fecha_creacion.isoformat() if self.fecha_creacion else None,
        }

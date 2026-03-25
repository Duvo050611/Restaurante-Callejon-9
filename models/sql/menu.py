"""
Modelos de Menú - PostgreSQL (SQLAlchemy)
Platillos, Categorías
"""
from datetime import datetime
from config.database import db


class Categoria(db.Model):
    __tablename__ = "categorias_menu"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    platillos = db.relationship("Platillo", backref="categoria_rel", lazy=True)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @classmethod
    def find_all(cls):
        return cls.query.order_by(cls.nombre).all()

    @classmethod
    def find_by_id(cls, id):
        return cls.query.get(int(id))

    @classmethod
    def find_by_slug(cls, slug):
        return cls.query.filter_by(slug=slug).first()

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, data):
        categoria = cls(
            nombre=data["nombre"],
            slug=data["slug"],
            descripcion=data.get("descripcion", ""),
            activo=data.get("activo", True),
        )
        db.session.add(categoria)
        db.session.commit()
        return categoria

    @classmethod
    def update(cls, id, data):
        categoria = cls.find_by_id(id)
        if not categoria:
            return None
        for key in ("nombre", "slug", "descripcion", "activo"):
            if key in data:
                setattr(categoria, key, data[key])
        categoria.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        return categoria

    @classmethod
    def delete(cls, id):
        categoria = cls.find_by_id(id)
        if not categoria:
            return False
        db.session.delete(categoria)
        db.session.commit()
        return True

    def to_dict(self):
        return {
            "_id": str(self.id),
            "id": str(self.id),
            "nombre": self.nombre,
            "slug": self.slug,
            "descripcion": self.descripcion,
            "activo": self.activo,
        }

    def __repr__(self):
        return f"<Categoria {self.slug}>"


class Platillo(db.Model):
    __tablename__ = "platillos"

    NOMBRE_CATEGORIAS = {
        "entrada": "Entrada",
        "plato_fuerte": "Plato Fuerte",
        "bebida": "Bebida",
        "postre": "Postre",
        "especial": "Especial",
    }

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, default="")
    categoria = db.Column(db.String(50), db.ForeignKey("categorias_menu.slug"), nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    imagen = db.Column(db.String(255), nullable=True)
    disponible = db.Column(db.Boolean, default=True)
    tiempo_preparacion = db.Column(db.Integer, default=15)
    nivel_picante = db.Column(db.Integer, default=0)
    alergenos = db.Column(db.JSON, default=list)
    notas = db.Column(db.Text, default="")
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @classmethod
    def find_all(cls, filtro=None):
        query = cls.query
        if filtro:
            if "disponible" in filtro:
                query = query.filter_by(disponible=filtro["disponible"])
            if "categoria" in filtro:
                query = query.filter_by(categoria=filtro["categoria"])
        platillos = query.order_by(cls.nombre).all()
        return [p._with_categoria_nombre() for p in platillos]

    @classmethod
    def find_by_id(cls, id):
        p = cls.query.get(int(id))
        return p._with_categoria_nombre() if p else None

    @classmethod
    def find_by_categoria(cls, categoria):
        platillos = cls.query.filter_by(categoria=categoria).order_by(cls.nombre).all()
        return [p._with_categoria_nombre() for p in platillos]

    @classmethod
    def find_disponibles(cls):
        platillos = cls.query.filter_by(disponible=True).order_by(cls.nombre).all()
        return [p._with_categoria_nombre() for p in platillos]

    @classmethod
    def buscar(cls, termino):
        platillos = cls.query.filter(
            db.or_(
                cls.nombre.ilike(f"%{termino}%"),
                cls.descripcion.ilike(f"%{termino}%"),
            )
        ).order_by(cls.nombre).all()
        return [p._with_categoria_nombre() for p in platillos]

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, data):
        platillo = cls(
            nombre=data["nombre"],
            descripcion=data.get("descripcion", ""),
            categoria=data.get("categoria", "plato_fuerte"),
            precio=float(data.get("precio", 0)),
            imagen=data.get("imagen", data.get("imagen_url", "")),
            disponible=data.get("disponible", True),
            tiempo_preparacion=int(data.get("tiempo_preparacion", 15)),
            nivel_picante=int(data.get("nivel_picante", 0)),
            alergenos=data.get("alergenos", []),
            notas=data.get("notas", ""),
        )
        db.session.add(platillo)
        db.session.commit()
        return str(platillo.id)

    @classmethod
    def update(cls, id, data):
        platillo = cls.query.get(int(id))
        if not platillo:
            return False
        campos = (
            "nombre", "descripcion", "categoria", "disponible",
            "tiempo_preparacion", "nivel_picante", "alergenos", "notas",
        )
        for campo in campos:
            if campo in data:
                setattr(platillo, campo, data[campo])
        if "precio" in data:
            platillo.precio = float(data["precio"])
        if "imagen" in data:
            platillo.imagen = data["imagen"]
        if "imagen_url" in data:
            platillo.imagen = data["imagen_url"]
        platillo.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        return True

    @classmethod
    def delete(cls, id):
        platillo = cls.query.get(int(id))
        if not platillo:
            return False
        db.session.delete(platillo)
        db.session.commit()
        return True

    @classmethod
    def toggle_disponible(cls, id):
        platillo = cls.query.get(int(id))
        if not platillo:
            return False
        platillo.disponible = not platillo.disponible
        platillo.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _with_categoria_nombre(self):
        """Devuelve un dict con categoria_nombre incluido (compatible con templates)"""
        d = {
            "_id": str(self.id),
            "id": str(self.id),
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "categoria": self.categoria,
            "categoria_nombre": self.NOMBRE_CATEGORIAS.get(self.categoria, self.categoria),
            "precio": float(self.precio),
            "imagen": self.imagen,
            "disponible": self.disponible,
            "tiempo_preparacion": self.tiempo_preparacion,
            "nivel_picante": self.nivel_picante,
            "alergenos": self.alergenos or [],
            "notas": self.notas,
        }
        return d

    def __repr__(self):
        return f"<Platillo {self.nombre}>"

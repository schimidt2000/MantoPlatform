from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager
from datetime import datetime, date

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
)

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True),
)

class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    permissions = db.relationship(
        "Permission",
        secondary=role_permissions,
        backref=db.backref("roles", lazy="dynamic"),
        lazy="joined",
    )

class Permission(db.Model):
    __tablename__ = "permissions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(120), unique=True, nullable=False)  # ex: "user.manage"


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)

    roles = db.relationship(
        "Role",
        secondary=user_roles,
        backref=db.backref("users", lazy="dynamic"),
        lazy="joined",
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_permission(self, code: str) -> bool:
        # SUPERADMIN pode tudo
        if any(r.name == "SUPERADMIN" for r in self.roles):
            return True

        # Caso contrário, verifica permissões normais
        return any(
            code == p.code
            for r in self.roles
            for p in r.permissions
        )


class Talent(db.Model):
    __tablename__ = "talents"

    id = db.Column(db.Integer, primary_key=True)

    # básicos
    full_name = db.Column(db.String(160), nullable=False)
    artistic_name = db.Column(db.String(160), nullable=True)

    phone = db.Column(db.String(30), nullable=True)
    email_contact = db.Column(db.String(160), nullable=True)

    birth_date = db.Column(db.Date, nullable=True)
    languages = db.Column(db.String(300), nullable=True)
    race = db.Column(db.String(60), nullable=True)

    # controle do fluxo A + C
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending | active
    source = db.Column(db.String(30), default="google_form", nullable=False)
    source_row = db.Column(db.Integer, nullable=True)  # linha da planilha (auditoria)

    # tags/skills
    tags = db.Column(db.String(300), nullable=True)  # "talento,coordenador,cantor"
    skills = db.Column(db.Text, nullable=True)

    # infos gerais
    height_cm = db.Column(db.Integer, nullable=True)
    clothing_size_top = db.Column(db.String(20), nullable=True)
    clothing_size_bottom = db.Column(db.String(20), nullable=True)
    shoe_size = db.Column(db.String(10), nullable=True)

    # visto/passaporte (como texto, porque no form vem "Possui Passaporte e visto americano?")
    passport_visa_text = db.Column(db.String(120), nullable=True)
    has_visa = db.Column(db.Boolean, nullable=True)

    # sensíveis (depois controlamos por permissão)
    rg = db.Column(db.String(30), nullable=True)
    cpf = db.Column(db.String(20), unique=True, nullable=False)
    pix_key = db.Column(db.String(120), nullable=True)
    pix_key_secondary = db.Column(db.String(120), nullable=True)

    # fotos / arquivos (links do Drive ou caminhos locais)
    photo_face_path = db.Column(db.String(300), nullable=True)
    photo_full_path = db.Column(db.String(300), nullable=True)

    cnh_file_path = db.Column(db.String(300), nullable=True)
    cnh_expiration = db.Column(db.Date, nullable=True)

    # carro
    car_model = db.Column(db.String(80), nullable=True)
    car_brand = db.Column(db.String(80), nullable=True)
    car_year = db.Column(db.String(10), nullable=True)
    car_plate = db.Column(db.String(20), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class ImportState(db.Model):
    __tablename__ = "import_state"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)  # ex: "talents_form"
    last_row = db.Column(db.Integer, default=1, nullable=False)  # começa 1 (header)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

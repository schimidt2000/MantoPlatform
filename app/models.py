from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import re as _re
from . import db, login_manager
from datetime import datetime, date
from .constants import RoleName

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
    birth_date = db.Column(db.Date, nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)

    roles = db.relationship(
        "Role",
        secondary=user_roles,
        backref=db.backref("users", lazy="dynamic"),
        lazy="joined",
    )
    salary_histories = db.relationship(
        "SalaryHistory",
        backref=db.backref("user", lazy=True),
        lazy="dynamic",
        order_by="SalaryHistory.start_date.desc()",
    )

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def has_permission(self, code: str) -> bool:
        # SUPERADMIN pode tudo
        if any(r.name == RoleName.SUPERADMIN for r in self.roles):
            return True

        # Caso contrário, verifica permissões normais
        return any(
            code == p.code
            for r in self.roles
            for p in r.permissions
        )


class Talent(db.Model):
    __tablename__ = "talents"
    __table_args__ = (
        db.Index("ix_talents_status", "status"),
    )

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

    # campos extras do forms
    gender = db.Column(db.String(30), nullable=True)
    doc_photo_path = db.Column(db.String(300), nullable=True)
    pix_key_type = db.Column(db.String(60), nullable=True)
    worked_before = db.Column(db.Boolean, nullable=True)
    how_found_us = db.Column(db.String(300), nullable=True)

    # portal do talento
    password_hash = db.Column(db.String(255), nullable=True)
    must_change_password = db.Column(db.Boolean, default=True, nullable=True)
    password_reset_token = db.Column(db.String(100), nullable=True, unique=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    terms_accepted_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    media_items = db.relationship("TalentMedia", back_populates="talent",
                                  cascade="all, delete-orphan", lazy=True,
                                  order_by="TalentMedia.created_at")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def phone_digits(self) -> str:
        """Retorna só os dígitos do telefone (para link WhatsApp)."""
        return _re.sub(r"\D", "", self.phone or "")


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"
    __table_args__ = (
        db.Index("ix_calendar_events_start_at",  "start_at"),
        db.Index("ix_calendar_events_seller_id", "seller_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    google_event_id = db.Column(db.String(128), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)
    event_type = db.Column(db.String(30), nullable=True)  # 'SHOW', 'CORP', 'R&I', 'ENSAIO', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # financeiro
    sale_value = db.Column(db.Integer, nullable=True)
    with_invoice = db.Column(db.Boolean, default=False, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    commission_rate = db.Column(db.Float, nullable=True)  # null = usa SiteSetting.default_commission_rate

    # ensaios / origem
    parent_event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)
    needs_rehearsal = db.Column(db.Boolean, default=False, nullable=False)
    source = db.Column(db.String(20), nullable=False, default="google_calendar", server_default="google_calendar")
    # source: 'google_calendar' | 'platform'

    # logística
    makeup_time = db.Column(db.String(5), nullable=True)       # "HH:MM"
    makeup_location = db.Column(db.String(200), nullable=True) # "manto" | "local" | endereço livre
    departure_time = db.Column(db.String(5), nullable=True)    # "HH:MM"
    travel_time_minutes  = db.Column(db.Integer, nullable=True)   # cache da estimativa Google Maps
    travel_distance_km   = db.Column(db.Float,   nullable=True)   # km de ida (rota mais curta)

    roles = db.relationship("EventRole", backref="event", lazy=True, cascade="all, delete-orphan")
    seller = db.relationship("User", lazy=True, foreign_keys=[seller_id])
    parent = db.relationship(
        "CalendarEvent",
        remote_side="CalendarEvent.id",
        backref=db.backref("ensaios", lazy=True),
        foreign_keys=[parent_event_id],
    )
    ensaio_materials = db.relationship(
        "EnsaioMaterial",
        back_populates="cal_event",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="EnsaioMaterial.created_at.asc()",
    )


class FigurinoSheet(db.Model):
    __tablename__ = "figurino_sheets"

    id = db.Column(db.Integer, primary_key=True)
    character_name = db.Column(db.String(200), nullable=False)
    character_name_norm = db.Column(db.String(200), nullable=True)  # lowercase sem acentos

    # Native fields (created inside the platform)
    photo_filename = db.Column(db.String(300), nullable=True)
    pieces = db.Column(db.Text, nullable=True)       # JSON: ["Blazer azul", "Calça preta"]
    notes = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)

    # Drive sync fields (kept for backward compat)
    drive_file_id = db.Column(db.String(200), nullable=True, unique=True)
    drive_url = db.Column(db.String(500), nullable=True)
    thumbnail_url = db.Column(db.String(500), nullable=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def pieces_list(self):
        """Returns list of dicts: [{"name": str, "qty": int}].
        Handles both legacy string format and current dict format."""
        import json as _json
        if not self.pieces:
            return []
        try:
            data = _json.loads(self.pieces)
            result = []
            for item in data:
                if isinstance(item, str):
                    result.append({"name": item, "qty": 1})
                elif isinstance(item, dict):
                    result.append({
                        "name": item.get("name", ""),
                        "qty": int(item.get("qty", 1) or 1),
                    })
            return result
        except Exception:
            return []

    @property
    def pieces_count(self):
        return len(self.pieces_list)

    @property
    def photo_url(self):
        if self.photo_filename:
            # Novo formato: URL completa (local ou S3)
            if self.photo_filename.startswith(("/", "http://", "https://")):
                return self.photo_filename
            # Legado: só o nome do arquivo
            return f"/uploads/figurino_photos/{self.photo_filename}"
        return self.thumbnail_url  # Drive sync fallback


class EventRole(db.Model):
    __tablename__ = "event_roles"
    __table_args__ = (
        db.Index("ix_event_roles_event_id",  "event_id"),
        db.Index("ix_event_roles_talent_id", "talent_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    character_name = db.Column(db.String(120), nullable=False)
    role_type = db.Column(db.String(20), nullable=False, default="character", server_default="character")
    # role_type: 'character' (personagens do evento) | 'extra' (transporte, maquiador, etc.)
    talent_id = db.Column(db.Integer, db.ForeignKey("talents.id"), nullable=True)
    cache_value = db.Column(db.Integer, nullable=True)
    travel_cache = db.Column(db.Integer, nullable=True)  # adicional fora de SP
    assigned_at = db.Column(db.DateTime, nullable=True)
    figurino_done_at = db.Column(db.DateTime, nullable=True)
    figurino_sheet_id = db.Column(db.Integer, db.ForeignKey("figurino_sheets.id"), nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default="nao_pago", server_default="nao_pago")
    invite_status = db.Column(db.String(20), nullable=True)
    # invite_status: None (não enviado) | 'pending' (enviado) | 'accepted' | 'rejected'
    event_changed_at = db.Column(db.DateTime, nullable=True)
    # set when event date/location changes after talent accepted; cleared when talent clicks "Ciente"

    talent = db.relationship("Talent", lazy=True)
    figurino_sheet = db.relationship("FigurinoSheet", lazy=True)


class EventLog(db.Model):
    __tablename__ = "event_logs"
    __table_args__ = (
        db.Index("ix_event_logs_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    actor_name = db.Column(db.String(120), nullable=False)
    actor_role = db.Column(db.String(60), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("CalendarEvent", lazy=True)


class AuditLog(db.Model):
    """Log geral de ações do sistema (não vinculadas a um evento específico)."""
    __tablename__ = "audit_logs"
    __table_args__ = (
        db.Index("ix_audit_logs_entity",     "entity_type", "entity_id"),
        db.Index("ix_audit_logs_created_at", "created_at"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    actor_name  = db.Column(db.String(120), nullable=False)
    actor_role  = db.Column(db.String(60), nullable=True)
    entity_type = db.Column(db.String(30), nullable=True)   # "talent","user","figurino","payment","settings"
    entity_id   = db.Column(db.Integer, nullable=True)
    entity_name = db.Column(db.String(200), nullable=True)  # nome legível do objeto
    action      = db.Column(db.String(60), nullable=False)  # "create","edit","delete","approve","payment"
    detail      = db.Column(db.Text, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class EventContract(db.Model):
    __tablename__ = "event_contracts"
    __table_args__ = (
        db.Index("ix_event_contracts_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("CalendarEvent", lazy=True)


class EventPayment(db.Model):
    __tablename__ = "event_payments"
    __table_args__ = (
        db.Index("ix_event_payments_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("CalendarEvent", lazy=True)


class TalentMedia(db.Model):
    """Foto de atuação ou link de apresentação do talento (até 3 fotos + links ilimitados)."""
    __tablename__ = "talent_media"
    __table_args__ = (
        db.Index("ix_talent_media_talent_id", "talent_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    talent_id    = db.Column(db.Integer, db.ForeignKey("talents.id"), nullable=False)
    media_type   = db.Column(db.String(10), nullable=False)  # 'photo' | 'link'
    label        = db.Column(db.String(200), nullable=True)
    file_path    = db.Column(db.String(500), nullable=True)   # relativo a UPLOAD_FOLDER
    url          = db.Column(db.String(500), nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    talent = db.relationship("Talent", back_populates="media_items", lazy=True)


class EnsaioMaterial(db.Model):
    """Arquivo ou link de referência para ensaio de um evento."""
    __tablename__ = "ensaio_materials"
    __table_args__ = (
        db.Index("ix_ensaio_materials_event_id", "event_id"),
    )

    id            = db.Column(db.Integer, primary_key=True)
    event_id      = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    material_type = db.Column(db.String(10), nullable=False)  # 'file' | 'link'
    label         = db.Column(db.String(200), nullable=True)  # nome legível
    file_path     = db.Column(db.String(500), nullable=True)  # relativo a UPLOAD_FOLDER
    url           = db.Column(db.String(500), nullable=True)  # link Google Drive / YouTube
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user  = db.relationship("User", lazy=True)
    cal_event = db.relationship("CalendarEvent", back_populates="ensaio_materials", lazy=True)


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    logo_path = db.Column(db.String(300), nullable=True)
    primary_color = db.Column(db.String(20), nullable=True)
    secondary_color = db.Column(db.String(20), nullable=True)
    accent_color = db.Column(db.String(20), nullable=True)
    default_commission_rate = db.Column(db.Float, nullable=True)  # % padrão de comissão (default 2.0)
    manto_address = db.Column(db.String(300), nullable=True)       # endereço base para cálculo de rota
    departure_margin_minutes = db.Column(db.Integer, nullable=True)  # margem de antecedência (default 60)
    google_maps_api_key = db.Column(db.String(100), nullable=True)   # API key para Distance Matrix
    # ClickSign
    clicksign_token   = db.Column(db.String(100), nullable=True)
    clicksign_sandbox = db.Column(db.Boolean, default=False, nullable=False)
    # Notificações por email (desligar durante testes)
    email_notifications_enabled = db.Column(db.Boolean, default=False, nullable=False)
    # Data de início do sistema (eventos anteriores são ignorados nas tasks)
    release_date = db.Column(db.Date, nullable=True)
    # Token OAuth do Google Calendar — persistido no banco para sobreviver a redeploys
    google_token = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SalaryHistory(db.Model):
    __tablename__ = "salary_history"
    __table_args__ = (
        db.Index("ix_salary_history_user_id", "user_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    salary = db.Column(db.Integer, nullable=False)       # valor em reais
    payment_type = db.Column(db.String(20), nullable=False)  # "semanal" | "quinzenal" | "comissao"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)          # null = vigente atualmente
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class ImportState(db.Model):
    __tablename__ = "import_state"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)  # ex: "talents_form"
    last_row = db.Column(db.Integer, default=1, nullable=False)  # começa 1 (header)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ══════════════════════════════════════════════════════════════════
#  CRM
# ══════════════════════════════════════════════════════════════════

class CRMStage(db.Model):
    """Etapa do pipeline — customizável pelo admin."""
    __tablename__ = "crm_stages"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(80), nullable=False)
    color      = db.Column(db.String(20), nullable=False, default="#6b6b6b")
    position   = db.Column(db.Integer, nullable=False, default=0)
    is_won     = db.Column(db.Boolean, default=False, nullable=False)
    is_lost    = db.Column(db.Boolean, default=False, nullable=False)

    deals = db.relationship("CRMDeal", backref="stage", lazy=True)


class CRMOrganization(db.Model):
    """Organizadora ou empresa contratante recorrente."""
    __tablename__ = "crm_organizations"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    cnpj       = db.Column(db.String(20), nullable=True)
    phone      = db.Column(db.String(30), nullable=True)
    email      = db.Column(db.String(120), nullable=True)
    notes      = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contacts = db.relationship("CRMContact", backref="organization", lazy=True)
    deals    = db.relationship("CRMDeal", backref="organization", lazy=True)

    @property
    def total_deals(self) -> int:
        return len(self.deals)

    @property
    def won_deals(self) -> int:
        return sum(1 for d in self.deals if d.stage and d.stage.is_won)

    @property
    def total_value(self) -> int:
        return sum(d.value or 0 for d in self.deals if d.stage and d.stage.is_won)


class CRMContact(db.Model):
    """Pessoa física — pode ou não pertencer a uma organização."""
    __tablename__ = "crm_contacts"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    cpf             = db.Column(db.String(20), nullable=True)
    phone           = db.Column(db.String(30), nullable=True)
    email           = db.Column(db.String(120), nullable=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("crm_organizations.id"), nullable=True)
    notes           = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deals = db.relationship("CRMDeal", backref="contact", lazy=True)


class CRMDeal(db.Model):
    """Negócio / lead — cada festa ou contratação."""
    __tablename__ = "crm_deals"
    __table_args__ = (
        db.Index("ix_crm_deals_stage_id",    "stage_id"),
        db.Index("ix_crm_deals_assigned_to", "assigned_to"),
    )

    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(200), nullable=False)

    # relacionamentos
    contact_id      = db.Column(db.Integer, db.ForeignKey("crm_contacts.id"), nullable=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("crm_organizations.id"), nullable=True)
    stage_id        = db.Column(db.Integer, db.ForeignKey("crm_stages.id"), nullable=True)
    assigned_to     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    seller          = db.relationship("User", foreign_keys=[assigned_to], lazy=True)

    # origem e status
    source          = db.Column(db.String(30), nullable=True)  # 'whatsapp'|'instagram'|'indicacao'|'outro'
    lost_reason     = db.Column(db.String(200), nullable=True)
    value           = db.Column(db.Integer, nullable=True)     # valor estimado em reais

    # campos do precontrato (preenchidos ao longo da negociação)
    contractor_name      = db.Column(db.String(200), nullable=True)
    contractor_cpf       = db.Column(db.String(20),  nullable=True)
    contractor_email     = db.Column(db.String(120), nullable=True)
    contractor_whatsapp  = db.Column(db.String(30),  nullable=True)
    contractor_address   = db.Column(db.String(300), nullable=True)
    birthday_person      = db.Column(db.String(200), nullable=True)
    birthday_age         = db.Column(db.String(10),  nullable=True)
    service_type         = db.Column(db.String(60),  nullable=True)
    character_count      = db.Column(db.String(20),  nullable=True)
    characters           = db.Column(db.Text,        nullable=True)
    event_theme          = db.Column(db.String(200), nullable=True)
    event_date           = db.Column(db.DateTime,    nullable=True)
    service_period       = db.Column(db.String(100), nullable=True)
    venue_type           = db.Column(db.String(60),  nullable=True)
    venue_cep            = db.Column(db.String(10),  nullable=True)
    venue_street         = db.Column(db.String(200), nullable=True)
    venue_number         = db.Column(db.String(20),  nullable=True)
    venue_complement     = db.Column(db.String(100), nullable=True)
    venue_neighborhood   = db.Column(db.String(100), nullable=True)
    venue_city           = db.Column(db.String(100), nullable=True)
    venue_state          = db.Column(db.String(50),  nullable=True)
    payment_method       = db.Column(db.String(60),  nullable=True)
    payment_notes        = db.Column(db.Text,        nullable=True)
    contractual_notes    = db.Column(db.Text,        nullable=True)

    # ClickSign
    clicksign_envelope_key = db.Column(db.String(100), nullable=True)
    contract_sent_at       = db.Column(db.DateTime, nullable=True)
    contract_signed_at     = db.Column(db.DateTime, nullable=True)
    payment_proof_path     = db.Column(db.String(300), nullable=True)
    payment_proof_at       = db.Column(db.DateTime, nullable=True)
    calendar_event_id      = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)
    calendar_event         = db.relationship("CalendarEvent", lazy=True, foreign_keys=[calendar_event_id])

    # datas de controle
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    closed_at   = db.Column(db.DateTime, nullable=True)

    notes     = db.relationship("CRMNote",     backref="deal", lazy=True, cascade="all, delete-orphan")
    reminders = db.relationship("CRMReminder", backref="deal", lazy=True, cascade="all, delete-orphan")

    @property
    def venue_full_address(self) -> str:
        parts = filter(None, [
            self.venue_street, self.venue_number, self.venue_complement,
            self.venue_neighborhood, self.venue_city, self.venue_state,
        ])
        return ", ".join(parts)


class CRMNote(db.Model):
    """Anotação / atividade registrada em um negócio."""
    __tablename__ = "crm_notes"
    __table_args__ = (
        db.Index("ix_crm_notes_deal_id", "deal_id"),
    )

    id         = db.Column(db.Integer, primary_key=True)
    deal_id    = db.Column(db.Integer, db.ForeignKey("crm_deals.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    content    = db.Column(db.Text, nullable=False)
    note_type  = db.Column(db.String(20), nullable=False, default="note")
    # note_type: 'note'|'call'|'whatsapp'|'email'|'internal'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    author = db.relationship("User", lazy=True)


class CRMReminder(db.Model):
    """Lembrete / follow-up agendado."""
    __tablename__ = "crm_reminders"
    __table_args__ = (
        db.Index("ix_crm_reminders_deal_id", "deal_id"),
    )

    id         = db.Column(db.Integer, primary_key=True)
    deal_id    = db.Column(db.Integer, db.ForeignKey("crm_deals.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    message    = db.Column(db.String(300), nullable=False)
    due_at     = db.Column(db.DateTime, nullable=False)
    done_at    = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    owner = db.relationship("User", lazy=True)

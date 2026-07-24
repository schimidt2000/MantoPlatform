from flask_login import UserMixin
import logging

logger = logging.getLogger(__name__)
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
    # email/senha são nulos para pessoas "apenas pagamento" (has_access=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    has_access = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    is_active = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)
    birth_date = db.Column(db.Date, nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)
    receives_commission = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    pix_key = db.Column(db.String(120), nullable=True)
    pix_key_type = db.Column(db.String(30), nullable=True)

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
        if not self.password_hash:
            return False
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

    # passaporte/visto: 'visa' = passaporte+visto EUA | 'passport' = só passaporte | 'none' = nenhum | None = não informado
    passport_status = db.Column(db.String(20), nullable=True)
    passport_visa_text = db.Column(db.String(120), nullable=True)  # resposta bruta do formulário (mantido para histórico)
    has_visa = db.Column(db.Boolean, nullable=True)  # deprecated — usar passport_status

    # sensíveis (depois controlamos por permissão)
    rg = db.Column(db.String(30), nullable=True)
    # CPF é único, mas opcional: talentos estrangeiros não têm CPF (feature 092).
    # No Postgres, múltiplos NULL não violam UNIQUE — por isso estrangeiro grava cpf=None (nunca "").
    cpf = db.Column(db.String(20), unique=True, nullable=True)
    is_foreigner = db.Column(db.Boolean, default=False, nullable=False, server_default="0")
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

    # anotações internas + nível de alerta (uso interno; nunca exibir no portal do talento)
    notes = db.Column(db.Text, nullable=True)
    warning_level = db.Column(db.String(20), nullable=True)  # None/"" | leve | moderado | grave

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

    @property
    def whatsapp_number(self) -> str:
        """Número para links wa.me: dígitos **com** código de país, sem o ``+``.

        A partir da feature 092 os telefones são gravados com DDI (ex.: ``+55 ...``), então os dígitos já
        incluem o código do país. Para registros antigos/editados que ainda venham só com DDD (sem ``+`` e
        com até 11 dígitos), assume Brasil (prefixa ``55``) — assim o link não fica sem país.
        """
        digits = self.phone_digits
        if not digits:
            return ""
        if not (self.phone or "").strip().startswith("+") and len(digits) <= 11:
            return "55" + digits
        return digits


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"
    __table_args__ = (
        db.Index("ix_calendar_events_start_at",  "start_at"),
        db.Index("ix_calendar_events_seller_id", "seller_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    google_event_id = db.Column(db.String(128), unique=True, nullable=False)
    # Link direto do evento no site do Google Calendar (feature 117) — vem pronto em todo
    # payload da API ("htmlLink"), capturado na sincronização; usado só pelo botão
    # "Editar no Google Agenda" (nenhuma escrita do Manto pro Google).
    google_html_link = db.Column(db.String(500), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(200), nullable=True)
    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)
    event_type = db.Column(db.String(30), nullable=True)  # 'SHOW', 'CORP', 'R&I', 'ENSAIO', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # financeiro
    sale_value = db.Column(db.Numeric(12, 2), nullable=True)
    # valor antes do desconto (preço cheio); desconto = sale_value_gross - sale_value
    sale_value_gross = db.Column(db.Numeric(12, 2), nullable=True)
    sale_date = db.Column(db.Date, nullable=True)  # data em que a venda foi fechada
    with_invoice = db.Column(db.Boolean, default=False, nullable=False)  # exige nota fiscal ("Emitir Nota")
    # Cortesia/permuta: venda tratada como 0 e cachê dos talentos vira "Custo de Marketing"
    is_cortesia_permuta = db.Column(db.Boolean, default=False, nullable=False, server_default="0")
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    commission_rate = db.Column(db.Float, nullable=True)  # null = usa SiteSetting.default_commission_rate

    # cliente associado (feature 094) — opcional; eventos passados podem ficar sem cliente.
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)

    # Confirmação do evento (feature 116): registro simples de quem confirmou e quando —
    # independente da mensagem de WhatsApp copiada pelo botão "Confirmar dados do evento".
    confirmed_at = db.Column(db.DateTime, nullable=True)
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Link público de avaliação da cliente (feature 130): token aleatório, gerado só na
    # primeira vez que alguém pede o link — nunca o id sequencial, para não ser adivinhável.
    feedback_token = db.Column(db.String(43), unique=True, nullable=True)

    # ensaios / origem
    parent_event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)
    needs_rehearsal = db.Column(db.Boolean, default=False, nullable=False)
    source = db.Column(db.String(20), nullable=False, default="google_calendar", server_default="google_calendar")
    # source: 'google_calendar' | 'platform'

    # agrupamento comercial: evento satélite aponta para o evento principal do grupo.
    # Distinto de parent_event_id (vínculo de Ensaios) — não reutilizar.
    group_leader_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)
    # nome do grupo comercial, preenchido apenas no evento principal (feature 055).
    group_name = db.Column(db.String(200), nullable=True)

    # logística
    makeup_time = db.Column(db.String(5), nullable=True)       # "HH:MM"
    makeup_location = db.Column(db.String(200), nullable=True) # "manto" | "local" | endereço livre
    departure_time = db.Column(db.String(5), nullable=True)    # "HH:MM"
    departure_location = db.Column(db.String(300), nullable=True)  # local de saída (padrão exibido: "Manto Produções")
    travel_time_minutes  = db.Column(db.Integer, nullable=True)   # cache da estimativa Google Maps
    travel_distance_km   = db.Column(db.Float,   nullable=True)   # km de ida (rota mais curta)
    is_outside_sp        = db.Column(db.Boolean, nullable=True)   # True=fora de SP | False=dentro | None=desconhecido

    # pagamento
    payment_method       = db.Column(db.String(30), nullable=True)   # 'avista'|'pix_parcelado'|'faturado'|'cartao'
    payment_installments = db.Column(db.Integer, nullable=True)       # parcelas (pix_parcelado)
    payment_due_date     = db.Column(db.Date, nullable=True)          # data de vencimento (faturado)
    transport_value      = db.Column(db.Numeric(12, 2), nullable=True)  # valor transporte separado (R$)
    acrescimo_value      = db.Column(db.Numeric(12, 2), nullable=True)  # acréscimo separado (R$)
    orcamento_history_id = db.Column(db.Integer, db.ForeignKey("orcamento_history.id"), nullable=True)
    invoice_file         = db.Column(db.String(255), nullable=True)   # filename em uploads/invoices/
    invoice_due_date     = db.Column(db.Date, nullable=True)          # data prevista de emissão da NF (feature 065)

    roles = db.relationship("EventRole", backref="event", lazy=True, cascade="all, delete-orphan")
    installments = db.relationship(
        "EventInstallment", backref="event", lazy=True,
        cascade="all, delete-orphan", order_by="EventInstallment.due_date",
    )
    invoices = db.relationship(
        "EventInvoice", backref="event", lazy=True,
        cascade="all, delete-orphan", order_by="EventInvoice.issue_date",
    )
    observations = db.relationship("EventObservation", backref="event", lazy=True,
                                   cascade="all, delete-orphan",
                                   order_by="EventObservation.created_at")
    seller = db.relationship("User", lazy=True, foreign_keys=[seller_id])
    confirmer = db.relationship("User", lazy=True, foreign_keys=[confirmed_by_id])
    client = db.relationship("Client", back_populates="events", lazy=True, foreign_keys=[client_id])
    acrescimos = db.relationship(
        "EventAcrescimo", backref="event", lazy=True,
        cascade="all, delete-orphan", order_by="EventAcrescimo.id",
    )
    # Feature 100: múltiplos clientes por evento, cada um com um tipo de relação.
    event_clients = db.relationship(
        "EventClient", backref="event", lazy=True,
        cascade="all, delete-orphan", order_by="EventClient.id",
    )
    parent = db.relationship(
        "CalendarEvent",
        remote_side="CalendarEvent.id",
        backref=db.backref("ensaios", lazy=True, cascade="all, delete-orphan"),
        foreign_keys=[parent_event_id],
    )
    ensaio_materials = db.relationship(
        "EnsaioMaterial",
        back_populates="cal_event",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="EnsaioMaterial.created_at.asc()",
    )
    group_leader = db.relationship(
        "CalendarEvent",
        remote_side="CalendarEvent.id",
        backref=db.backref("satellites", lazy=True),
        foreign_keys=[group_leader_id],
    )

    @property
    def is_educamanto(self) -> bool:
        """True se o evento é EducaManto (feature 109): título começa com "(EDU".

        Cobre "(EDU)" e "(EDUCAMANTO)", sem diferenciar maiúsculas. Equivalente SQL:
        ``CalendarEvent.title.ilike("(EDU%")``.
        """
        from app.constants import EDUCAMANTO_TITLE_PREFIX
        return bool(self.title) and self.title.upper().startswith(EDUCAMANTO_TITLE_PREFIX)

    @property
    def is_satellite(self) -> bool:
        """True se este evento é satélite de um grupo (campos comerciais herdados do principal)."""
        return self.group_leader_id is not None

    @property
    def is_group_leader(self) -> bool:
        """True se este evento é principal de pelo menos um evento satélite."""
        return len(self.satellites) > 0

    @property
    def group_display_name(self) -> str:
        """Rótulo do grupo para exibição: o nome do grupo, ou o título do evento (fallback)."""
        return self.group_name or self.title


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
        except Exception as exc:  # noqa: BLE001 — JSON de peças corrompido não pode quebrar a tela
            logger.warning("pieces JSON inválido na FigurinoSheet %s: %s", self.id, exc)
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
    cache_value = db.Column(db.Numeric(10, 2), nullable=True)
    cache_cap   = db.Column(db.Numeric(10, 2), nullable=True)   # valor máximo pré-calculado (do orçamento)
    travel_cache = db.Column(db.Numeric(10, 2), nullable=True)  # adicional fora de SP
    assigned_at = db.Column(db.DateTime, nullable=True)
    figurino_done_at = db.Column(db.DateTime, nullable=True)
    figurino_sheet_id = db.Column(db.Integer, db.ForeignKey("figurino_sheets.id"), nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default="nao_pago", server_default="nao_pago")
    invite_status = db.Column(db.String(20), nullable=True)
    # invite_status: None (não enviado) | 'pending' (enviado) | 'accepted' | 'rejected'
    event_changed_at    = db.Column(db.DateTime, nullable=True)
    change_description  = db.Column(db.Text, nullable=True)
    # event_changed_at/change_description: set when event changes after acceptance; cleared on "Ciente"

    needs_makeup  = db.Column(db.Boolean, nullable=True)  # pré-preenchido do orçamento
    is_singer     = db.Column(db.Boolean, nullable=True)  # pré-preenchido do orçamento

    # Dispensa de tarefa de casting obsoleta (feature 108): o cargo continua existindo (por
    # isso a sincronização com o Google Agenda não o recria) mas para de contar como pendente.
    dismissed_at = db.Column(db.DateTime, nullable=True)
    dismissed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    talent = db.relationship("Talent", lazy=True)
    figurino_sheet = db.relationship("FigurinoSheet", lazy=True)
    dismisser = db.relationship("User", lazy=True, foreign_keys=[dismissed_by])


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

    is_signed = db.Column(db.Boolean, default=False, nullable=False)

    event = db.relationship("CalendarEvent", lazy=True)


class EventPayment(db.Model):
    __tablename__ = "event_payments"
    __table_args__ = (
        db.Index("ix_event_payments_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=True)  # aceita centavos
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("CalendarEvent", lazy=True)


class EventReimbursement(db.Model):
    """Valor que a Manto adiantou num evento (bagagem, alimentação etc.) e precisa cobrar
    de volta da cliente — separado do valor de venda e de EventPayment (feature 136).
    """
    __tablename__ = "event_reimbursements"
    __table_args__ = (
        db.Index("ix_event_reimbursements_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # valor a cobrar da cliente
    invoice_file_path = db.Column(db.String(300), nullable=True)  # nota fiscal do gasto original
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Preenchidos só quando cobrado (feature 136) — collected_at nulo = pendente.
    collected_at = db.Column(db.DateTime, nullable=True)
    collected_amount = db.Column(db.Numeric(12, 2), nullable=True)
    receipt_file_path = db.Column(db.String(300), nullable=True)  # comprovante do reembolso recebido
    collected_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    event = db.relationship("CalendarEvent", lazy=True)
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy=True)
    collected_by = db.relationship("User", foreign_keys=[collected_by_id], lazy=True)

    @property
    def is_collected(self) -> bool:
        return self.collected_at is not None


class EventInstallment(db.Model):
    """Parcela de recebimento planejada de um evento (cronograma data + valor) — feature 065.

    Distinta de EventPayment (comprovante de prova): aqui é o recebimento previsto, com data de
    vencimento, valor e marcação de recebida (para a visão de fluxo de caixa do painel).
    """
    __tablename__ = "event_installments"
    __table_args__ = (
        db.Index("ix_event_installments_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=True)
    received = db.Column(db.Boolean, default=False, nullable=False, server_default="0")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class EventInvoice(db.Model):
    """Nota fiscal de um evento (feature 069).

    Um evento "com nota" pode ter várias notas, cada uma com valor e data próprios. Notas em
    ``status='a_emitir'`` viram tarefa de emissão para o super admin; subir o arquivo e marcar
    emitida conclui a tarefa. O custo de nota (``tax_rate``%) é reconhecido pelo mês de ``issue_date``.
    """
    __tablename__ = "event_invoices"
    __table_args__ = (
        db.Index("ix_event_invoices_event_id", "event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=True)        # valor da nota
    issue_date = db.Column(db.Date, nullable=True)             # data de emissão (prevista/real)
    status = db.Column(db.String(12), nullable=False, default="a_emitir", server_default="a_emitir")
    file = db.Column(db.String(300), nullable=True)           # arquivo da nota
    issued_at = db.Column(db.DateTime, nullable=True)        # quando marcada emitida
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class EventObservation(db.Model):
    """Observação do evento — texto, link ou imagem enviada pela vendedora."""
    __tablename__ = "event_observations"
    __table_args__ = (
        db.Index("ix_event_observations_event_id", "event_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    event_id     = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    obs_type     = db.Column(db.String(10), nullable=False)   # 'text' | 'link' | 'image'
    content      = db.Column(db.Text, nullable=True)          # texto ou URL
    file_path    = db.Column(db.String(500), nullable=True)   # relativo a UPLOAD_FOLDER
    label        = db.Column(db.String(200), nullable=True)   # descrição opcional
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


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
    default_commission_rate = db.Column(db.Float, nullable=True)  # % padrão de comissão (default 2.5)
    # Responsável EducaManto (feature 109): beneficiário das comissões de eventos "(EDU…".
    # NULL = sem responsável (a comissão EDU segue a regra comum, do vendedor).
    educamanto_seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    tax_rate = db.Column(db.Float, nullable=True)            # % provisionamento de imposto (default 16.0)
    fator_r_threshold = db.Column(db.Float, nullable=True)   # % corte do Fator R (default 28.0)
    manto_address = db.Column(db.String(300), nullable=True)       # endereço base para cálculo de rota
    departure_margin_minutes = db.Column(db.Integer, nullable=True)  # margem de antecedência (default 60)
    google_maps_api_key = db.Column(db.String(100), nullable=True)   # API key para Distance Matrix
    # ClickSign
    clicksign_token   = db.Column(db.String(100), nullable=True)
    clicksign_sandbox = db.Column(db.Boolean, default=False, nullable=False)
    # Notificações por email (desligar durante testes)
    email_notifications_enabled = db.Column(db.Boolean, default=True, nullable=False)
    # Modo anônimo total das avaliações: quando True, a autoria fica oculta até para o
    # super admin na página /talents/avaliacoes (feature 056).
    ratings_fully_anonymous = db.Column(db.Boolean, default=False, nullable=False, server_default="0")
    # Data de início do sistema (eventos anteriores são ignorados nas tasks)
    release_date = db.Column(db.Date, nullable=True)
    # Token OAuth do Google Calendar — persistido no banco para sobreviver a redeploys
    google_token = db.Column(db.Text, nullable=True)
    # Pricing config for the quote calculator (JSON)
    pricing_config = db.Column(db.Text, nullable=True)
    # TTL cache: {ym: iso_datetime} — last successful sync per month
    calendar_sync_cache = db.Column(db.Text, nullable=True)
    # Marcador da última sincronização automática da agenda (cron interno).
    # Serve de "lock" de execução única entre workers e de visibilidade do último ciclo.
    calendar_auto_sync_at = db.Column(db.DateTime, nullable=True)
    # Número WhatsApp (só dígitos, com DDI) que recebe as respostas dos formulários de
    # pré-contrato (feature 118). NULL = usa o padrão em app/formularios/routes.py.
    whatsapp_form_number = db.Column(db.String(20), nullable=True)
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


class CommissionPayment(db.Model):
    """Rastreamento individual de comissões de vendedores.

    status:
      a_pagar  — pendente de pagamento no próximo ciclo (dia 5)
      pago     — marcado como pago pelo financeiro
      cancelado — evento cancelado antes do pagamento; sem movimentação financeira

    Para estorno (evento cancelado após pagamento), cria-se uma nova linha com
    amount negativo e status='a_pagar', referenciando o registro original em original_id.
    """
    __tablename__ = "commission_payments"
    __table_args__ = (
        db.Index("ix_commission_payments_seller_id", "seller_id"),
        db.Index("ix_commission_payments_event_id",  "event_id"),
        db.Index("ix_commission_payments_status",    "status"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    event_id    = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)
    event_title = db.Column(db.String(200), nullable=False)  # cópia: persiste mesmo se evento for deletado
    seller_id   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sale_date   = db.Column(db.Date, nullable=True)          # data da venda (herda do evento)
    # Feature 109: comissões EducaManto só entram no ciclo de pagamento após a realização do
    # evento — esta é a data da realização. NULL = comissão comum (ciclo pela sale_date).
    payable_from = db.Column(db.Date, nullable=True)
    amount      = db.Column(db.Numeric(12, 2), nullable=False)  # positivo ou negativo (estorno)
    status      = db.Column(db.String(20), nullable=False, default="a_pagar", server_default="a_pagar")
    paid_at     = db.Column(db.Date, nullable=True)
    notes       = db.Column(db.Text, nullable=True)
    original_id = db.Column(db.Integer, db.ForeignKey("commission_payments.id"), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    seller   = db.relationship("User", foreign_keys=[seller_id], lazy=True)
    event    = db.relationship(
        "CalendarEvent",
        foreign_keys=[event_id],
        backref=db.backref("commission_payments", lazy=True),
        lazy=True,
    )
    original = db.relationship("CommissionPayment", remote_side="CommissionPayment.id", lazy=True)


class SalaryPayment(db.Model):
    """Registro gerado automaticamente de pagamento de salário.

    Criado preguiçosamente ao carregar a planilha de pagamentos do mês.
    payment_type herdado do SalaryHistory vigente:
      semanal   → gerado para cada segunda-feira do mês
      quinzenal → gerado para os dias 5 e 20 do mês
    """
    __tablename__ = "salary_payments"
    __table_args__ = (
        db.Index("ix_salary_payments_user_id",   "user_id"),
        db.Index("ix_salary_payments_month_ref",  "month_ref"),
        db.UniqueConstraint("user_id", "due_date", name="uq_salary_payment_user_due"),
    )

    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    salary_history_id = db.Column(db.Integer, db.ForeignKey("salary_history.id"), nullable=True)
    due_date          = db.Column(db.Date, nullable=False)
    amount            = db.Column(db.Numeric(12, 2), nullable=False)
    payment_status    = db.Column(db.String(20), nullable=False, default="nao_pago", server_default="nao_pago")
    paid_at           = db.Column(db.Date, nullable=True)
    notes             = db.Column(db.Text, nullable=True)
    month_ref         = db.Column(db.String(7), nullable=False)  # YYYY-MM
    created_at        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Adiantamento (feature 067): valor já pago antecipadamente + comprovante. Reduz o valor a
    # pagar (líquido = amount − advance_amount); NÃO reduz o custo de salário do balanço.
    advance_amount    = db.Column(db.Numeric(12, 2), nullable=True)   # legado (feature 067) — migrado p/ SalaryAdvance
    advance_proof     = db.Column(db.String(300), nullable=True)      # legado (feature 067)

    user           = db.relationship("User", backref=db.backref("salary_payments", lazy="dynamic"))
    salary_history = db.relationship("SalaryHistory", lazy=True)
    advances       = db.relationship(
        "SalaryAdvance", backref="payment", lazy=True,
        cascade="all, delete-orphan", order_by="SalaryAdvance.created_at",
    )

    @property
    def advance_total(self):
        """Soma de todos os adiantamentos deste salário (feature 089)."""
        from decimal import Decimal as _D
        return sum((a.amount or _D("0") for a in self.advances), _D("0"))


class SalaryAdvance(db.Model):
    """Um adiantamento de salário (valor + comprovante) — feature 089.

    Vários por ``SalaryPayment``; o líquido a pagar = salário − soma dos adiantamentos. Não reduz o
    custo de salário do balanço (apenas o valor a pagar).
    """
    __tablename__ = "salary_advances"
    __table_args__ = (db.Index("ix_salary_advances_payment_id", "salary_payment_id"),)

    id                = db.Column(db.Integer, primary_key=True)
    salary_payment_id = db.Column(db.Integer, db.ForeignKey("salary_payments.id"), nullable=False)
    amount            = db.Column(db.Numeric(12, 2), nullable=False)
    proof             = db.Column(db.String(300), nullable=True)
    # Data do adiantamento (feature 120) — escolhida pelo financeiro no lançamento, default
    # hoje; diferente de created_at (timestamp de quando o registro foi gravado no sistema).
    advance_date      = db.Column(db.Date, nullable=False)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class SpecialExpense(db.Model):
    """Gasto especial/extra da empresa (figurino, escritório, marketing, etc.).

    Fluxo: qualquer colaborador registra (status 'pendente'); só impacta o balanço
    financeiro quando um super admin aprova (status 'aprovado'). O impacto ocorre no
    período/mês da `expense_date` (regime de competência).
    """
    __tablename__ = "special_expenses"
    __table_args__ = (
        db.Index("ix_special_expenses_status", "status"),
        db.Index("ix_special_expenses_expense_date", "expense_date"),
    )

    CATEGORIES = ["Figurino", "Escritório", "Marketing", "Manutenção", "Outros"]
    STATUSES = ["pendente", "aprovado", "rejeitado"]
    DISBURSEMENT_TYPES = ["reembolso", "fornecedor"]

    id             = db.Column(db.Integer, primary_key=True)
    description    = db.Column(db.String(200), nullable=False)
    category       = db.Column(db.String(30), nullable=False, default="Outros")
    amount         = db.Column(db.Numeric(10, 2), nullable=False)    # valor em R$
    expense_date   = db.Column(db.Date, nullable=False)             # data do gasto (competência)
    receipt_path   = db.Column(db.String(300), nullable=True)       # ex.: "expenses/arquivo.pdf"
    status         = db.Column(db.String(20), nullable=False, default="pendente", server_default="pendente")
    notes          = db.Column(db.Text, nullable=True)             # observações / motivo da rejeição
    created_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at    = db.Column(db.DateTime, nullable=True)

    # Desembolso: como o gasto será pago (entra na lista de pagamentos quando aprovado)
    disbursement_type = db.Column(db.String(20), nullable=True)   # "reembolso" | "fornecedor"
    reimburse_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # funcionário a reembolsar
    supplier_name     = db.Column(db.String(200), nullable=True)  # nome do fornecedor
    supplier_pix      = db.Column(db.String(120), nullable=True)  # chave PIX do fornecedor
    payment_status    = db.Column(db.String(20), nullable=False, default="nao_pago", server_default="nao_pago")
    # True quando o desembolso já foi pago no ato do registro (ex.: PIX direto da conta
    # da Manto) — nunca entra na Planilha de Pagamentos, mesmo com payment_status="pago"
    # (feature 128).
    paid_at_creation  = db.Column(db.Boolean, default=False, nullable=False)

    # Vínculo opcional a um evento: gasto aprovado entra como custo do evento
    # (lucro do evento = venda − cachês − gastos extras aprovados)
    event_id          = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)

    # True quando um gestor (FINANCEIRO/SUPERADMIN) editou os dados do gasto na mesma operação
    # em que ele está/ficou "aprovado" (migração 179). Não é um status novo — os cálculos que já
    # filtram status=="aprovado" (DRE, planilha de pagamentos, custo de evento) continuam
    # somando esses gastos normalmente; a flag só adiciona transparência visual na tela React.
    approved_with_edits = db.Column(
        db.Boolean, default=False, nullable=False, server_default="false"
    )

    created_by     = db.relationship("User", foreign_keys=[created_by_id], lazy=True)
    approved_by    = db.relationship("User", foreign_keys=[approved_by_id], lazy=True)
    reimburse_user = db.relationship("User", foreign_keys=[reimburse_user_id], lazy=True)
    event          = db.relationship("CalendarEvent", foreign_keys=[event_id], lazy=True)

    @property
    def receipt_url(self):
        """URL para visualizar o comprovante, ou None se não houver."""
        if not self.receipt_path:
            return None
        return f"/uploads/{self.receipt_path}"

    @property
    def payee_name(self):
        """Nome de quem recebe o desembolso (funcionário reembolsado ou fornecedor)."""
        if self.disbursement_type == "reembolso":
            return self.reimburse_user.name if self.reimburse_user else "—"
        if self.disbursement_type == "fornecedor":
            return self.supplier_name or "—"
        return "—"

    @property
    def payee_pix(self):
        """Chave PIX do destinatário do desembolso, ou ''."""
        if self.disbursement_type == "reembolso":
            return (self.reimburse_user.pix_key or "").strip() if self.reimburse_user else ""
        if self.disbursement_type == "fornecedor":
            return (self.supplier_pix or "").strip()
        return ""


class RecurringExpense(db.Model):
    """Gasto recorrente da empresa (feature 110): conta de luz, advogado, assinaturas.

    Diferente do gasto extra (``SpecialExpense``): não passa por aprovação, é restrito a
    FINANCEIRO/SUPERADMIN e repete todo mês. Três tipos:

    - ``variavel``: valor muda dentro de uma faixa (``amount_min``–``amount_max``); a partir
      do ``due_day`` a home alerta até o lançamento do mês ser preenchido e pago.
    - ``debito_automatico``: valor fixo debitado sozinho — lançamento mensal automático
      "registrado", sem ação de pagamento.
    - ``assinatura``: valor fixo no cartão de crédito (``card_name``) — idem.
    """
    __tablename__ = "recurring_expenses"

    # Feature 121: "programado" não segue ciclo automático — parcelas com data e valor
    # próprios, criadas de uma vez no cadastro (ver RecurringExpenseEntry).
    TYPES = ["variavel", "debito_automatico", "assinatura", "programado"]
    TYPE_LABELS = {
        "variavel": "Conta variável",
        "debito_automatico": "Débito automático",
        "assinatura": "Assinatura (cartão)",
        "programado": "Pagamento programado",
    }
    # Feature 112: frequência da cobrança.
    FREQUENCIES = ["mensal", "semanal", "quinzenal", "anual"]
    FREQUENCY_LABELS = {
        "mensal": "Mensal",
        "semanal": "Semanal",
        "quinzenal": "Quinzenal",
        "anual": "Anual",
    }
    # Feature 113: dia da semana da cobrança semanal (índice = weekday() do Python).
    WEEKDAY_LABELS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(200), nullable=False)
    expense_type  = db.Column(db.String(20), nullable=False)
    amount        = db.Column(db.Numeric(10, 2), nullable=True)   # valor fixo (fixos)
    amount_min    = db.Column(db.Numeric(10, 2), nullable=True)   # faixa esperada (variável)
    amount_max    = db.Column(db.Numeric(10, 2), nullable=True)
    due_day       = db.Column(db.Integer, nullable=False)         # 1–31; clampado no fim do mês
    default_pix   = db.Column(db.String(120), nullable=True)
    card_name     = db.Column(db.String(100), nullable=True)      # assinaturas
    notes         = db.Column(db.Text, nullable=True)
    is_active     = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    # Feature 112: frequência da cobrança e vigência (end_date NULL = eterna).
    frequency     = db.Column(db.String(20), nullable=False, default="mensal", server_default="mensal")
    start_date    = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    end_date      = db.Column(db.Date, nullable=True)
    # Feature 113: dia da semana (0=segunda … 6=domingo) — só para frequência semanal.
    weekday       = db.Column(db.Integer, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy=True)
    entries    = db.relationship(
        "RecurringExpenseEntry", backref="recurring", lazy=True,
        order_by="RecurringExpenseEntry.month_ref.desc()",
    )

    @property
    def is_fixed(self) -> bool:
        """True para tipos de valor fixo (débito automático/assinatura)."""
        return self.expense_type in ("debito_automatico", "assinatura")

    @property
    def expected_label(self) -> str | None:
        """Rótulo da referência da conta variável (feature 111): faixa ou valor exato.

        Variável com ``amount`` preenchido = valor exato esperado; com min/max = faixa;
        sem nada = None (sem referência). Não se aplica aos tipos fixos.
        """
        if self.expense_type != "variavel":
            return None
        from app.money import format_brl
        if self.amount is not None:
            return f"esperado {format_brl(self.amount, prefix=True)}"
        if self.amount_min is not None or self.amount_max is not None:
            lo = format_brl(self.amount_min or 0, prefix=True)
            hi = format_brl(self.amount_max or 0, prefix=True)
            return f"faixa {lo} – {hi}"
        return None

    @property
    def parcelas_summary(self) -> str:
        """Resumo do pagamento programado (feature 121): "N parcelas · R$ total"."""
        from app.money import format_brl
        n = len(self.entries)
        total = sum((e.amount or 0 for e in self.entries), 0)
        plural = "s" if n != 1 else ""
        return f"{n} parcela{plural} · {format_brl(total, prefix=True)} no total"

    def occurrences_in_month(self, year: int, month: int) -> int:
        """Quantas cobranças a conta tem no mês (feature 112). 0 = fora do ciclo/vigência.

        Regras: fora de [start_date, end_date] → 0; anual → 1 só no mês de aniversário da
        data de início; quinzenal → janelas 1–15 e 16–fim que intersectam a vigência no mês;
        semanal → nº de ocorrências do dia da semana da data de início dentro da interseção
        mês × vigência; mensal → 1.
        """
        import calendar as cal_mod
        from datetime import date as _date
        _, last_day = cal_mod.monthrange(year, month)
        month_start = _date(year, month, 1)
        month_end = _date(year, month, last_day)
        if self.start_date and self.start_date > month_end:
            return 0
        if self.end_date and self.end_date < month_start:
            return 0
        lo = max(month_start, self.start_date or month_start)
        hi = min(month_end, self.end_date or month_end)
        freq = self.frequency or "mensal"
        if freq == "anual":
            anchor = self.start_date or month_start
            return 1 if month == anchor.month else 0
        if freq == "quinzenal":
            n = 0
            if lo.day <= 15 and hi.day >= 1:          # janela 1–15 intersecta a vigência
                n += 1
            if hi.day >= 16:                          # janela 16–fim intersecta a vigência
                n += 1
            return n
        if freq == "semanal":
            return sum(
                1 for d in range(lo.day, hi.day + 1)
                if _date(year, month, d).weekday() == self.anchor_weekday
            )
        return 1

    @property
    def anchor_weekday(self) -> int:
        """Dia da semana da cobrança semanal (feature 113): escolhido, ou o da data de início."""
        if self.weekday is not None:
            return self.weekday
        return self.start_date.weekday() if self.start_date else 0

    @property
    def dia_label(self) -> str:
        """Rótulo do "dia" da conta: "dia N" ou, na semanal, "toda semana (quarta)"."""
        if self.frequency == "semanal":
            return f"toda semana ({self.WEEKDAY_LABELS[self.anchor_weekday]})"
        return f"dia {self.due_day}"

    @property
    def vigencia_label(self) -> str:
        """Rótulo da vigência: "desde dd/mm/aaaa" + "até dd/mm/aaaa" ou "eterna"."""
        desde = self.start_date.strftime("%d/%m/%Y") if self.start_date else "—"
        if self.end_date:
            return f"desde {desde} até {self.end_date.strftime('%d/%m/%Y')}"
        return f"desde {desde} · eterna"


class RecurringExpenseEntry(db.Model):
    """Lançamento mensal de um gasto recorrente (feature 110) — um por conta/mês.

    Estados: ``a_pagar`` (variável preenchida, entra na planilha de pagamentos) → ``pago``;
    ``registrado`` (fixos, criado automaticamente, nunca vira pendência); ``pulado``
    (variável cujo boleto não veio no mês — sem valor). "Aguardando valor" não é linha no
    banco: é a ausência de lançamento no mês para conta variável ativa.
    """
    __tablename__ = "recurring_expense_entries"
    __table_args__ = (
        db.UniqueConstraint("recurring_id", "month_ref", name="uq_recurring_entry_month"),
        db.Index("ix_recurring_entries_month_ref", "month_ref"),
        db.Index("ix_recurring_entries_status", "status"),
    )

    STATUSES = ["a_pagar", "pago", "registrado", "pulado"]

    id           = db.Column(db.Integer, primary_key=True)
    recurring_id = db.Column(db.Integer, db.ForeignKey("recurring_expenses.id"), nullable=False)
    month_ref    = db.Column(db.String(7), nullable=False)   # "YYYY-MM"
    amount       = db.Column(db.Numeric(10, 2), nullable=True)  # NULL só em "pulado"
    pix          = db.Column(db.String(120), nullable=True)
    due_date     = db.Column(db.Date, nullable=True)
    status       = db.Column(db.String(20), nullable=False, default="a_pagar")
    filled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    filled_at    = db.Column(db.DateTime, nullable=True)
    paid_at      = db.Column(db.Date, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    filled_by = db.relationship("User", foreign_keys=[filled_by_id], lazy=True)

    @property
    def out_of_range(self) -> bool:
        """True se o valor preenchido fugiu da referência da conta (só destaque visual).

        Feature 111: a referência da conta variável pode ser uma faixa (min–max) ou um
        valor exato esperado (``recurring.amount``) — qualquer diferença do exato destaca.
        """
        if self.amount is None or not self.recurring:
            return False
        if self.recurring.expense_type == "variavel" and self.recurring.amount is not None:
            return self.amount != self.recurring.amount
        lo, hi = self.recurring.amount_min, self.recurring.amount_max
        if lo is not None and self.amount < lo:
            return True
        return hi is not None and self.amount > hi


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ══════════════════════════════════════════════════════════════════
#  EducaManto — Motor de Orçamentos por Pacote
# ══════════════════════════════════════════════════════════════════

class EducaMantoPackage(db.Model):
    """Pacote de precificação (ex: Uma Aventura Animal)."""
    __tablename__ = "educamanto_packages"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    margin_1s       = db.Column(db.Float, nullable=False, default=1.41)
    margin_2s       = db.Column(db.Float, nullable=False, default=1.70)
    margin_1s_days  = db.Column(db.Float, nullable=False, default=1.50)
    margin_2s_days  = db.Column(db.Float, nullable=False, default=1.80)
    discount_days    = db.Column(db.Integer, nullable=False, default=2)
    discount_pct     = db.Column(db.Float, nullable=False, default=0.05)
    commission_rate  = db.Column(db.Float, nullable=False, default=0.05)
    # Cachê do ensemble (figurante extra) por cenário — somado por ensemble no orçamento.
    ensemble_1s      = db.Column(db.Float, nullable=False, default=350, server_default="350")
    ensemble_2s      = db.Column(db.Float, nullable=False, default=600, server_default="600")
    ensemble_1s_days = db.Column(db.Float, nullable=False, default=300, server_default="300")
    ensemble_2s_days = db.Column(db.Float, nullable=False, default=550, server_default="550")
    created_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship(
        "EducaMantoItem",
        backref="package",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="EducaMantoItem.sort_order",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "margin_1s": self.margin_1s,
            "margin_2s": self.margin_2s,
            "margin_1s_days": self.margin_1s_days,
            "margin_2s_days": self.margin_2s_days,
            "discount_days": self.discount_days,
            "discount_pct": self.discount_pct,
            "commission_rate": self.commission_rate,
            "ensemble_1s": self.ensemble_1s,
            "ensemble_2s": self.ensemble_2s,
            "ensemble_1s_days": self.ensemble_1s_days,
            "ensemble_2s_days": self.ensemble_2s_days,
            "items": [item.to_dict() for item in self.items],
        }


class EducaMantoItem(db.Model):
    """Linha de custo dentro de um pacote EducaManto."""
    __tablename__ = "educamanto_items"

    id           = db.Column(db.Integer, primary_key=True)
    package_id   = db.Column(db.Integer, db.ForeignKey("educamanto_packages.id"), nullable=False)
    name         = db.Column(db.String(200), nullable=False)
    qty          = db.Column(db.Integer, nullable=False, default=1)
    cost_1s      = db.Column(db.Float, nullable=False, default=0)
    cost_2s      = db.Column(db.Float, nullable=False, default=0)
    cost_1s_days = db.Column(db.Float, nullable=False, default=0)
    cost_2s_days = db.Column(db.Float, nullable=False, default=0)
    sort_order   = db.Column(db.Integer, nullable=False, default=0)
    # Quanto a quantidade do item cresce por ensemble adicionado (0 = não cresce).
    ensemble_add = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "qty": self.qty,
            "cost_1s": self.cost_1s,
            "cost_2s": self.cost_2s,
            "cost_1s_days": self.cost_1s_days,
            "cost_2s_days": self.cost_2s_days,
            "ensemble_add": self.ensemble_add,
        }


class EducaMantoQuote(db.Model):
    """Orçamento PDF gerado no EducaManto (feature 077) — histórico por usuário.

    Guarda um instantâneo (``snapshot``) da configuração e dos valores por pacote no momento da
    geração, para reproduzir o mesmo PDF depois (valores congelados, como o histórico da calculadora).
    """
    __tablename__ = "educamanto_quotes"
    __table_args__ = (
        db.Index("ix_educamanto_quotes_user_id", "user_id"),
    )

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    client_name    = db.Column(db.String(200), nullable=True)
    packages_label = db.Column(db.String(300), nullable=True)   # nomes p/ a lista do histórico
    snapshot       = db.Column(db.Text, nullable=True)          # JSON: dias/ensemble/transporte + pacotes

    user = db.relationship("User", lazy=True)


class ImportState(db.Model):
    __tablename__ = "import_state"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)  # ex: "talents_form"
    last_row = db.Column(db.Integer, default=1, nullable=False)  # começa 1 (header)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_checked_at = db.Column(db.DateTime, nullable=True)
    last_import_count = db.Column(db.Integer, default=0, nullable=False)


class OrcamentoHistory(db.Model):
    """Histórico de orçamentos gerados, persistido por usuário."""
    __tablename__ = "orcamento_history"
    __table_args__ = (
        db.Index("ix_orcamento_history_user_id", "user_id"),
    )

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    client_name    = db.Column(db.String(200), nullable=True)
    event_location = db.Column(db.String(300), nullable=True)
    event_date     = db.Column(db.String(20), nullable=True)   # ISO date string
    total_1h       = db.Column(db.Numeric(10, 2), nullable=True)
    total_2h       = db.Column(db.Numeric(10, 2), nullable=True)
    total_3h       = db.Column(db.Numeric(10, 2), nullable=True)  # feature 098
    total_4h       = db.Column(db.Numeric(10, 2), nullable=True)
    has_show       = db.Column(db.Boolean, default=False, nullable=False)
    form_snapshot  = db.Column(db.Text, nullable=True)  # JSON com todo o estado do form
    # Snapshot do RESULTADO (totais, multiplicadores, mensagem) — congela o orçamento:
    # "Ver" mostra exatamente o que foi cotado, imune a mudanças de preço posteriores.
    result_snapshot = db.Column(db.Text, nullable=True)  # JSON do quote gerado

    user = db.relationship("User", lazy=True)


# ══════════════════════════════════════════════════════════════════
#  Avaliações de eventos (via portal do artista)
# ══════════════════════════════════════════════════════════════════

class EventRating(db.Model):
    """Avaliação geral de um evento, submetida pelo talento via portal."""
    __tablename__ = "event_ratings"
    __table_args__ = (
        db.UniqueConstraint("event_id", "talent_id", name="uq_event_rating"),
        db.Index("ix_event_ratings_event_id",  "event_id"),
        db.Index("ix_event_ratings_talent_id", "talent_id"),
    )

    id                  = db.Column(db.Integer, primary_key=True)
    event_id            = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    talent_id           = db.Column(db.Integer, db.ForeignKey("talents.id"), nullable=False)
    score               = db.Column(db.Integer, nullable=False)   # 1–5
    comment             = db.Column(db.Text, nullable=True)
    submitted_at        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    detail_submitted_at = db.Column(db.DateTime, nullable=True)   # quando etapa 2 foi enviada
    edited_at           = db.Column(db.DateTime, nullable=True)   # última edição após o envio
    edit_count          = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    event       = db.relationship("CalendarEvent", lazy=True)
    talent      = db.relationship("Talent", foreign_keys=[talent_id], lazy=True)
    sub_ratings = db.relationship(
        "EventSubRating", backref="rating", lazy=True, cascade="all, delete-orphan"
    )
    versions    = db.relationship(
        "EventRatingVersion", backref="rating", lazy=True,
        cascade="all, delete-orphan", order_by="EventRatingVersion.replaced_at.desc()",
    )


class EventSubRating(db.Model):
    """Sub-avaliação por categoria dentro de um EventRating."""
    __tablename__ = "event_sub_ratings"
    __table_args__ = (
        db.Index("ix_event_sub_ratings_rating_id", "rating_id"),
        db.Index("ix_event_sub_ratings_subject",   "subject_talent_id"),
    )

    id                = db.Column(db.Integer, primary_key=True)
    rating_id         = db.Column(db.Integer, db.ForeignKey("event_ratings.id"), nullable=False)
    category          = db.Column(db.String(20), nullable=False)
    # category: 'som' | 'figurino' | 'texto' | 'coordenacao' | 'maquiagem' | 'artista'
    subject_talent_id = db.Column(db.Integer, db.ForeignKey("talents.id"), nullable=True)
    # null para categorias gerais (som, figurino, texto); preenchido para avaliações de pessoa
    score             = db.Column(db.Integer, nullable=False)    # 1–5
    comment           = db.Column(db.Text, nullable=True)

    subject_talent = db.relationship("Talent", foreign_keys=[subject_talent_id], lazy=True)


class EventRatingVersion(db.Model):
    """Versão anterior de uma avaliação, guardada quando ela é editada (substituída).

    snapshot: JSON com {score, comment, subs:[{category, subject_talent_id, score, comment}]}
    do estado que deixou de ser vigente.
    """
    __tablename__ = "event_rating_versions"
    __table_args__ = (
        db.Index("ix_event_rating_versions_rating_id", "rating_id"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    rating_id   = db.Column(db.Integer, db.ForeignKey("event_ratings.id"), nullable=False)
    snapshot    = db.Column(db.Text, nullable=False)              # JSON
    replaced_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def data(self) -> dict:
        """Snapshot desserializado."""
        import json as _json
        try:
            return _json.loads(self.snapshot)
        except (ValueError, TypeError):
            return {}


class ClientFeedback(db.Model):
    """Avaliação da cliente sobre a experiência com a equipe da Manto (feature 130).

    Distinta de ``EventRating`` (avaliação do artista sobre o evento, via portal do
    talento, com login): aqui quem avalia é a cliente, sem login, através do link público
    gerado a partir de ``CalendarEvent.feedback_token``. Sem identificação de quem
    responde, então cada envio vira uma linha própria — não há "atualizar" uma avaliação
    anterior.
    """
    __tablename__ = "client_feedbacks"
    __table_args__ = (
        db.Index("ix_client_feedbacks_event_id", "event_id"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    event_id     = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    score        = db.Column(db.Integer, nullable=False)  # 1–5
    tags         = db.Column(db.Text, nullable=True)      # JSON: lista de cards marcados
    comment      = db.Column(db.Text, nullable=True)
    # Nome de quem respondeu (feature 132) — obrigatório no formulário público a partir
    # dessa feature; nulo em avaliações enviadas antes dela (nunca retroativamente exigido).
    client_name  = db.Column(db.String(200), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship("CalendarEvent", lazy=True)

    @property
    def tags_list(self) -> list[str]:
        """Cards marcados, desserializados."""
        import json as _json
        try:
            return _json.loads(self.tags) if self.tags else []
        except (ValueError, TypeError):
            return []


class SyncLog(db.Model):
    """Log global de sincronização da agenda — persiste mesmo após exclusão do evento."""
    __tablename__ = "sync_logs"
    __table_args__ = (
        db.Index("ix_sync_logs_created_at", "created_at"),
    )

    id              = db.Column(db.Integer, primary_key=True)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # action: 'google_created' | 'platform_created' | 'google_updated' | 'auto_deleted' | 'manual_deleted'
    action          = db.Column(db.String(30), nullable=False)
    event_title     = db.Column(db.String(300), nullable=True)
    google_event_id = db.Column(db.String(200), nullable=True)
    event_id        = db.Column(db.Integer, nullable=True)   # sem FK — evento pode ter sido deletado
    details         = db.Column(db.Text, nullable=True)      # mudanças ou motivo
    actor           = db.Column(db.String(120), nullable=True)  # "Sistema" ou nome do usuário


class ReviewSpace(db.Model):
    """Espaço de revisão de mídia estilo Vimeo Review (feature 088)."""
    __tablename__ = "review_spaces"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    creator = db.relationship("User", lazy=True, foreign_keys=[created_by])
    assets = db.relationship(
        "ReviewAsset", backref="space", lazy=True,
        cascade="all, delete-orphan", order_by="ReviewAsset.position",
    )
    reviewers = db.relationship(
        "ReviewReviewer", backref="space", lazy=True, cascade="all, delete-orphan",
    )

    @property
    def reviewer_ids(self) -> set:
        return {r.user_id for r in self.reviewers}


class ReviewAsset(db.Model):
    """Material (vídeo/áudio/imagem/PDF) dentro de um espaço de revisão (feature 088)."""
    __tablename__ = "review_assets"
    __table_args__ = (db.Index("ix_review_assets_space_id", "space_id"),)

    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey("review_spaces.id"), nullable=False)
    file_path = db.Column(db.String(400), nullable=False)   # URL no nosso armazenamento
    original_name = db.Column(db.String(300), nullable=True)
    media_type = db.Column(db.String(10), nullable=False)   # 'video' | 'audio' | 'image' | 'pdf'
    position = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Arquivos temporários (feature 090): expiram em 7 dias; o arquivo é removido do armazenamento
    # (registro e comentários permanecem). 'finalized' = aprovado pelo criador (arquivo removido na hora).
    expires_at   = db.Column(db.DateTime, nullable=True)
    finalized_at = db.Column(db.DateTime, nullable=True)
    file_removed = db.Column(db.Boolean, default=False, nullable=False, server_default="0")
    version      = db.Column(db.Integer, default=1, nullable=False, server_default="1")
    # Quem enviou a versão ATUAL do arquivo (feature 104) — copiado para o snapshot na substituição.
    uploaded_by  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    # Status de aprovação (feature 182): 'em_revisao' | 'aprovado' | 'precisa_ajustes' | 'rejeitado'.
    # Redefinido para 'em_revisao' a cada nova versão enviada (ver review_ops.replace_asset).
    status = db.Column(db.String(20), nullable=False, default="em_revisao", server_default="em_revisao")

    uploader = db.relationship("User", lazy=True, foreign_keys=[uploaded_by])
    comments = db.relationship(
        "ReviewComment", backref="asset", lazy=True,
        cascade="all, delete-orphan", order_by="ReviewComment.created_at",
    )
    versions = db.relationship(
        "ReviewAssetVersion", backref="asset", lazy=True,
        cascade="all, delete-orphan", order_by="ReviewAssetVersion.version_number",
    )

    @property
    def is_available(self) -> bool:
        """True se o arquivo ainda está no armazenamento (não expirado nem finalizado)."""
        return not self.file_removed

    @property
    def days_left(self):
        """Dias restantes (arredondados p/ cima) até a expiração; None se sem prazo/removido."""
        if self.file_removed or not self.expires_at:
            return None
        import math
        secs = (self.expires_at - datetime.utcnow()).total_seconds()
        return math.ceil(secs / 86400) if secs > 0 else 0

    @property
    def history(self) -> list:
        """Snapshots de versões anteriores, da mais recente para a mais antiga."""
        return sorted(self.versions, key=lambda v: v.version_number, reverse=True)


class ReviewAssetVersion(db.Model):
    """Snapshot de uma versão ANTERIOR de um material de revisão (feature 104).

    Criado no momento da substituição do arquivo: a versão atual continua vivendo no próprio
    ``ReviewAsset``; aqui fica o histórico navegável. O arquivo do snapshot herda o
    ``expires_at`` que tinha quando era atual (não renova) e é removido pelo cleanup da
    feature 090 quando vence.
    """
    __tablename__ = "review_asset_versions"
    __table_args__ = (db.Index("ix_review_asset_versions_asset_id", "asset_id"),)

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("review_assets.id"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)  # número que tinha quando era atual
    file_path = db.Column(db.String(400), nullable=False)
    original_name = db.Column(db.String(300), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    file_removed = db.Column(db.Boolean, default=False, nullable=False, server_default="0")

    uploader = db.relationship("User", lazy=True, foreign_keys=[uploaded_by])

    @property
    def is_available(self) -> bool:
        """True se o arquivo do snapshot ainda está no armazenamento."""
        return not self.file_removed


class ReviewReviewer(db.Model):
    """Usuário autorizado a revisar um espaço (feature 088)."""
    __tablename__ = "review_reviewers"
    __table_args__ = (
        db.UniqueConstraint("space_id", "user_id", name="uq_review_reviewer"),
        db.Index("ix_review_reviewers_space_id", "space_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey("review_spaces.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", lazy=True, foreign_keys=[user_id])


class ReviewComment(db.Model):
    """Comentário ancorado num material (feature 088).

    Âncora conforme o tipo: ``timecode`` (segundos) em vídeo/áudio; ``page`` em PDF;
    ``pos_x``/``pos_y`` (0–1, relativos) em imagem.
    """
    __tablename__ = "review_comments"
    __table_args__ = (db.Index("ix_review_comments_asset_id", "asset_id"),)

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("review_assets.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timecode = db.Column(db.Float, nullable=True)   # segundos (vídeo/áudio)
    page = db.Column(db.Integer, nullable=True)     # página (PDF)
    pos_x = db.Column(db.Float, nullable=True)       # 0–1 (imagem)
    pos_y = db.Column(db.Float, nullable=True)       # 0–1 (imagem)
    resolved = db.Column(db.Boolean, default=False, nullable=False, server_default="0")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Feature 104: versão do material vigente quando o comentário foi criado, e registro
    # transparente de conclusão (quem concluiu e quando — visível a todos os envolvidos).
    version_number = db.Column(db.Integer, default=1, nullable=False, server_default="1")
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", lazy=True, foreign_keys=[user_id])
    resolver = db.relationship("User", lazy=True, foreign_keys=[resolved_by])


class EventAcrescimo(db.Model):
    """Acréscimo tipado de um evento/orçamento (feature 099).

    Cada acréscimo tem um ``tipo`` (lista fixa + BV + Outro) e um valor em R$ ou %. O valor efetivo em
    reais fica congelado em ``amount_brl`` (fonte estável para lucro/comissão/pagamento). O tipo **BV** é
    um repasse: não é lucro da Manto nem entra na comissão da vendedora, e vira um pagamento (com PIX do
    recebedor) na planilha de pagamentos.
    """

    __tablename__ = "event_acrescimos"
    __table_args__ = (db.Index("ix_event_acrescimos_event_id", "event_id"),)

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    tipo = db.Column(db.String(40), nullable=False)
    descricao = db.Column(db.String(200), nullable=True)   # usado quando tipo = "Outro"
    is_percent = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    value = db.Column(db.Numeric(12, 2), nullable=True)     # número informado (R$ ou % base)
    amount_brl = db.Column(db.Numeric(12, 2), nullable=True)  # valor efetivo em R$ (congelado no save)
    is_bv = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

    # Dados do repasse BV (preenchidos na tela comercial do evento)
    bv_recipient = db.Column(db.String(200), nullable=True)
    bv_pix = db.Column(db.String(140), nullable=True)
    bv_payment_status = db.Column(db.String(20), nullable=False, default="nao_pago",
                                  server_default="nao_pago")

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def display_label(self) -> str:
        """Rótulo do acréscimo: a descrição (para 'Outro') ou o próprio tipo."""
        if self.tipo == "Outro" and self.descricao:
            return self.descricao
        return self.tipo


class EventClient(db.Model):
    """Associação evento↔cliente com tipo de relação (feature 100).

    Um evento pode ter vários clientes (contratante, assessora, mãe/pai, familiar, outros). Substitui o
    vínculo único ``CalendarEvent.client_id`` como fonte de verdade; ``client_id`` é mantido de forma
    denormalizada apontando para o contratante (compat com telas que mostram "o cliente").
    """

    __tablename__ = "event_clients"
    __table_args__ = (
        db.Index("ix_event_clients_event_id", "event_id"),
        db.Index("ix_event_clients_client_id", "client_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    relationship_type = db.Column(db.String(30), nullable=False, default="Contratante",
                                  server_default="Contratante")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    client = db.relationship("Client", lazy=True, foreign_keys=[client_id])


class Client(db.Model):
    """Cliente da base de relacionamento/marketing (feature 094).

    Importado do Kommo CRM (CSV) ou criado manualmente pelo vendedor. A identidade é o **telefone
    normalizado** (``phone``, só dígitos) — chave única usada para deduplicar a base. Um cliente
    relaciona-se a zero ou mais ``CalendarEvent`` via ``CalendarEvent.client_id``.
    """

    __tablename__ = "clients"
    __table_args__ = (
        db.Index("ix_clients_name", "name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    # telefone normalizado (apenas dígitos, com DDI/DDD) — chave de identidade/dedup
    phone = db.Column(db.String(20), nullable=False, unique=True, index=True)
    phone_display = db.Column(db.String(30), nullable=True)  # telefone como exibir/formatar
    email = db.Column(db.String(200), nullable=True)
    company = db.Column(db.String(200), nullable=True)
    # CPF (pessoa física) / CNPJ (empresa) e endereço — texto livre, como capturado no
    # formulário de pré-contrato (feature 119) ou digitado manualmente na ficha do cliente.
    cpf = db.Column(db.String(20), nullable=True)
    cnpj = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    source = db.Column(db.String(20), nullable=False, default="manual",
                       server_default="manual")  # 'kommo_import' | 'manual'

    # ── Metadados de marketing (agregados do Kommo) ──────────────────
    kommo_lead_id = db.Column(db.String(40), nullable=True)   # lead mais recente do telefone
    responsible = db.Column(db.String(120), nullable=True)    # "Usuário responsável"
    tags = db.Column(db.String(300), nullable=True)           # "Tags" agregadas
    lead_stage = db.Column(db.String(120), nullable=True)     # "Etapa do lead" mais recente
    funnel = db.Column(db.String(120), nullable=True)         # "Funil de vendas"
    lead_value = db.Column(db.Numeric(12, 2), nullable=True)  # "Lead venda R$" (maior/agregado)
    kommo_created_at = db.Column(db.DateTime, nullable=True)  # "Criado em" no Kommo
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    events = db.relationship(
        "CalendarEvent", back_populates="client", lazy=True,
        foreign_keys="CalendarEvent.client_id",
    )

    @property
    def event_count(self) -> int:
        """Número de eventos associados a este cliente."""
        return len(self.events)

    @property
    def whatsapp_number(self) -> str:
        """Número para links wa.me: dígitos com DDI, sem ``+`` (assume Brasil se vier sem país)."""
        digits = _re.sub(r"\D", "", self.phone or "")
        if not digits:
            return ""
        if len(digits) <= 11:
            return "55" + digits
        return digits


class FormResponse(db.Model):
    """Resposta de um formulário público de pré-contrato (feature 118).

    Substitui o WhatsForm: a cliente preenche o formulário hospedado no Manto, a resposta é
    salva aqui ANTES de abrir o WhatsApp dela com a mensagem formatada. ``data`` guarda o
    JSON completo (rótulo→valor, na ordem do formulário); as colunas extraídas cobrem
    busca, sugestão de cliente por telefone e ordenação.
    """

    __tablename__ = "form_responses"

    id = db.Column(db.Integer, primary_key=True)
    form_type = db.Column(db.String(20), nullable=False)  # 'comum' | 'corporativo'
    # JSON: [{"secao":..., "campos": [[chave, rotulo, valor], ...]}] (feature 123 — chave
    # estável de FormFieldDefinition.field_key; respostas anteriores à 123 têm campos com só
    # [rotulo, valor], sem chave — lidas normalmente, só não participam de busca por chave)
    data = db.Column(db.Text, nullable=False)
    contact_name = db.Column(db.String(200), nullable=False)  # contratante / razão social
    # WhatsApp normalizado (só dígitos, com DDI) — usado para sugerir cliente existente
    contact_phone = db.Column(db.String(20), nullable=True, index=True)
    contact_phone_display = db.Column(db.String(30), nullable=True)
    event_date = db.Column(db.Date, nullable=True, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=True, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True, index=True)
    # Vínculo automático de evento (feature 126): 'auto_date' | 'auto_client' | 'manual' | None.
    event_link_source = db.Column(db.String(20), nullable=True)
    # True quando a tentativa automática ficou ambígua/conflitante — aparece no aviso da home.
    event_link_ambiguous = db.Column(db.Boolean, default=False, nullable=False)
    # True assim que um humano decide (associa OU desvincula manualmente) — a automação
    # nunca mais tenta vincular essa resposta sozinha depois disso (não sobrescreve decisão).
    event_link_locked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    client = db.relationship("Client", lazy=True)
    event = db.relationship("CalendarEvent", lazy=True, backref=db.backref("form_responses", lazy=True))

    @property
    def data_sections(self) -> list:
        """Seções decodificadas do JSON de ``data`` (lista vazia se corrompido)."""
        import json

        try:
            return json.loads(self.data or "[]")
        except (ValueError, TypeError):
            return []

    @property
    def form_type_label(self) -> str:
        """Rótulo amigável do tipo de formulário."""
        return "Corporativo" if self.form_type == "corporativo" else "Pré-contrato"


class FormFieldDefinition(db.Model):
    """Definição editável de um campo de formulário público (feature 123).

    Substitui os campos hardcoded que existiam em ``app/formularios/routes.py``. Cada linha é
    um campo de um dos dois formulários (``form_type``: ``'comum'`` | ``'corporativo'``),
    agrupado visualmente por ``section_name`` e ordenado por ``order`` (a seção muda quando
    ``section_name`` muda ao percorrer os campos em ordem — não existe tabela de seção
    separada). Campos com ``is_system=True`` alimentam outras partes do sistema (extração de
    contratante/telefone/data do evento, preenchimento automático de CPF/CNPJ/endereço do
    cliente na feature 119, autopreenchimento por CEP) e por isso não podem ser removidos nem
    ter ``field_type``/``field_key`` alterados pelo editor.
    """

    __tablename__ = "form_field_definitions"

    FIELD_TYPES = (
        "texto_curto", "texto_longo", "selecao", "data", "hora",
        "telefone", "email", "cpf", "cnpj", "cep", "sim_nao",
    )

    id = db.Column(db.Integer, primary_key=True)
    form_type = db.Column(db.String(20), nullable=False)
    section_name = db.Column(db.String(100), nullable=False)
    field_key = db.Column(db.String(60), nullable=False)
    field_type = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    help_text = db.Column(db.String(300), nullable=True)
    placeholder = db.Column(db.String(200), nullable=True)
    required = db.Column(db.Boolean, default=False, nullable=False)
    options = db.Column(db.Text, nullable=True)  # JSON list[str] — só para field_type='selecao'
    order = db.Column(db.Integer, nullable=False)
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint("form_type", "field_key", name="uq_form_field_key"),)

    @property
    def options_list(self) -> list[str]:
        """Opções decodificadas do JSON de ``options`` (lista vazia se corrompido/ausente)."""
        import json

        try:
            return json.loads(self.options or "[]")
        except (ValueError, TypeError):
            return []


# ── Catálogo público de personagens (feature 133) ───────────────────────────

catalog_item_categories = db.Table(
    "catalog_item_categories",
    db.Column("item_id", db.Integer, db.ForeignKey("catalog_items.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("catalog_categories.id"), primary_key=True),
)


class CatalogCategory(db.Model):
    """Seção/categoria do catálogo (ex.: "Natal", "Princesas") — importada do WordPress."""
    __tablename__ = "catalog_categories"

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True)


class CatalogItem(db.Model):
    """Item do catálogo público (personagem/show) — importado do export do WordPress.

    ``wp_product_id`` é a chave de deduplicação: reimportar o mesmo CSV não duplica itens
    já trazidos. Sem tela de edição nesta feature (feature 133) — ``is_active`` já existe
    para que uma futura tela de gestão não precise de uma migration nova só pra isso.
    """
    __tablename__ = "catalog_items"

    id                      = db.Column(db.Integer, primary_key=True)
    wp_product_id           = db.Column(db.Integer, nullable=True, unique=True)
    name                    = db.Column(db.String(200), nullable=False)
    slug                    = db.Column(db.String(220), nullable=False, unique=True)
    short_description_html = db.Column(db.Text, nullable=True)
    tags                    = db.Column(db.Text, nullable=True)  # JSON: lista de strings, só para busca
    is_active               = db.Column(db.Boolean, default=True, nullable=False)
    imported_at             = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    categories = db.relationship("CatalogCategory", secondary=catalog_item_categories, lazy=True)
    images     = db.relationship(
        "CatalogItemImage", backref="item", lazy=True,
        cascade="all, delete-orphan", order_by="CatalogItemImage.position",
    )

    @property
    def tags_list(self) -> list[str]:
        import json as _json
        try:
            return _json.loads(self.tags) if self.tags else []
        except (ValueError, TypeError):
            return []

    @property
    def cover_image(self) -> "CatalogItemImage | None":
        return self.images[0] if self.images else None


class CatalogItemImage(db.Model):
    """Uma foto de um item do catálogo — posição 0 é a capa (usada no Open Graph)."""
    __tablename__ = "catalog_item_images"
    __table_args__ = (
        db.Index("ix_catalog_item_images_item_id", "item_id"),
    )

    id               = db.Column(db.Integer, primary_key=True)
    item_id          = db.Column(db.Integer, db.ForeignKey("catalog_items.id"), nullable=False)
    url              = db.Column(db.String(500), nullable=False)
    original_url     = db.Column(db.String(500), nullable=True)
    position         = db.Column(db.Integer, default=0, nullable=False)
    file_size_bytes  = db.Column(db.Integer, nullable=True)

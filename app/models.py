from flask_login import UserMixin
import logging

logger = logging.getLogger(__name__)
from werkzeug.security import generate_password_hash, check_password_hash
import re as _re
from . import db, login_manager
from datetime import datetime, date
from .constants import (
    FIGURINO_ANEXO_FOTO,
    FIGURINO_KIND_COMPRA,
    FIGURINO_KIND_MANUTENCAO,
    FIGURINO_KIND_PRODUCAO,
    FIGURINO_PROD_ABERTOS,
    FIGURINO_PROD_SOLICITADO,
    FIGURINO_SEV_IMPEDE,
    GIFT_3D_STATUS_PENDENTE,
    now_sp,
    RoleName,
    VIRTUAL_CAMPAIGN_STATUS_PUBLICADA,
    VIRTUAL_CAMPAIGN_STATUS_RASCUNHO,
    VIRTUAL_ORDER_STATUS_RESERVADO,
    VIRTUAL_PRODUCTION_STATUS_PENDENTE,
    VIRTUAL_REFUND_STATUS_PENDENTE,
    VIRTUAL_SLOT_STATUS_LIVRE,
    VIRTUAL_SLOT_STATUS_TRAVADO,
)

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

    # Confirmação do email do cadastro público (feature 219). O talento digita o email errado
    # (`hotmail.con`) e ninguém descobre até um convite voltar; aqui ele confirma logo após enviar
    # o formulário, com o cadastro **já gravado** — nada do que preencheu depende disso.
    email_verified_at = db.Column(db.DateTime, nullable=True)
    # Token do link de confirmação. Serve também de credencial da tela de sucesso para corrigir o
    # email e reenviar; é zerado ao confirmar, o que fecha os dois caminhos de uma vez.
    email_verify_token = db.Column(db.String(80), nullable=True, unique=True)
    email_verify_sent_at = db.Column(db.DateTime, nullable=True)

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

    # Cancelamento (feature 224). Evento que já tem dinheiro preso — pagamento recebido,
    # contrato ou elenco escalado — não é apagado: vira cancelado. Some da agenda e de toda
    # métrica, mas o registro fica, porque é a ele que a devolução ao cliente se refere.
    # Excluir de verdade continua valendo para evento vazio (criado por engano).
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)

    # Solicitação de exclusão (feature 224): o Comercial pede, o Superadmin decide. Os três
    # campos são zerados quando a solicitação é recusada.
    deletion_requested_at = db.Column(db.DateTime, nullable=True)
    deletion_requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    deletion_request_reason = db.Column(db.Text, nullable=True)

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
    def is_cancelled(self) -> bool:
        """True se o evento foi cancelado (feature 224) — o registro existe, mas não conta.

        Cancelado não aparece na agenda nem em nenhuma métrica (venda, DRE, planilha de
        pagamentos, disponibilidade do casting). Equivalente SQL:
        ``CalendarEvent.cancelled_at.isnot(None)``.
        """
        return self.cancelled_at is not None

    @property
    def has_pending_deletion_request(self) -> bool:
        """True se alguém pediu a exclusão e o Superadmin ainda não decidiu (feature 224)."""
        return self.deletion_requested_at is not None and self.cancelled_at is None

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

    # Quantos figurinos IGUAIS a Manto tem desta ficha (feature 235). Não confundir com o `qty`
    # de dentro de `pieces` — aquele é "2 luvas" DENTRO de um figurino; este é "temos 3 Gatunos".
    # 0 é válido: ficha de um figurino que ainda não foi produzido (ver `FigurinoProducao`).
    quantity = db.Column(db.Integer, nullable=False, default=1, server_default="1")

    # Native fields (created inside the platform)
    photo_filename = db.Column(db.String(300), nullable=True)
    pieces = db.Column(db.Text, nullable=True)       # JSON: ["Blazer azul", "Calça preta"]
    tags = db.Column(db.Text, nullable=True)         # JSON: ["anjo", "natal"] (feature 183)
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
    def tags_list(self):
        """Returns list of tag strings (feature 183). Corrupted/empty JSON returns []."""
        import json as _json
        if not self.tags:
            return []
        try:
            data = _json.loads(self.tags)
            return [str(t) for t in data if str(t).strip()]
        except Exception as exc:  # noqa: BLE001 — JSON de tags corrompido não pode quebrar a tela
            logger.warning("tags JSON inválido na FigurinoSheet %s: %s", self.id, exc)
            return []

    @property
    def photo_url(self):
        if self.photo_filename:
            # Novo formato: URL completa (local ou S3)
            if self.photo_filename.startswith(("/", "http://", "https://")):
                return self.photo_filename
            # Legado: só o nome do arquivo
            return f"/uploads/figurino_photos/{self.photo_filename}"
        return self.thumbnail_url  # Drive sync fallback


class FigurinoMissingDismissal(db.Model):
    """Descarte de alerta de "personagem sem ficha" (feature 183).

    Guarda os `EventRole.id` cobertos pelo descarte no momento em que ele foi feito — um
    `EventRole` novo criado depois (id fora deste conjunto) faz o personagem reaparecer na
    lista de faltantes (ver `app/figurino/figurino_ops.py::list_sheets`).
    """

    __tablename__ = "figurino_missing_dismissals"
    __table_args__ = (
        db.Index("ix_figurino_missing_dismissals_norm", "character_name_norm"),
    )

    id = db.Column(db.Integer, primary_key=True)
    character_name_norm = db.Column(db.String(200), nullable=False)
    event_role_ids = db.Column(db.Text, nullable=False)  # JSON: [101, 102]
    dismissed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dismissed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    dismisser = db.relationship("User", lazy=True, foreign_keys=[dismissed_by])


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

    # Lembrete de confirmação (feature 231): quando saiu o último e quantos já saíram para ESTE
    # convite. É o que segura o spam — a regra pede 3 dias de intervalo e para no segundo.
    invite_reminder_at = db.Column(db.DateTime, nullable=True)
    invite_reminder_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
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
    # % da comissão do responsável EducaManto sobre o LUCRO do evento (venda − BV − cachês).
    # Era uma constante no código; virou configuração para não exigir deploy ao mudar o acordo.
    # NULL = usa o padrão de 5%.
    educamanto_commission_rate = db.Column(db.Float, nullable=True)
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
    # Link de avaliação no Google mostrado à cliente que dá 5 estrelas no feedback público.
    # NULL = usa DEFAULT_GOOGLE_REVIEW_URL em app/api/feedback_write.py.
    google_review_url = db.Column(db.String(300), nullable=True)
    # ── Loja de Interações Virtuais (feature 205) ────────────────────────────
    # "InfiniteTag" da conta InfinitePay — identifica o vendedor em toda chamada da API.
    infinitepay_handle = db.Column(db.String(100), nullable=True)
    # Segredo do endereço que recebe as notificações de pagamento
    # (`/api/webhooks/infinitepay/<token>`). A InfinitePay não assina seus webhooks, então este
    # token é a única barreira de entrada — e fica no banco justamente para ser revogável sem
    # deploy: trocar a linha invalida o endereço antigo na hora.
    infinitepay_webhook_token = db.Column(db.String(64), nullable=True)
    # Marcador do último ciclo da varredura de reservas virtuais. Serve de "lock" de execução única
    # entre os workers do gunicorn — mesmo papel de `calendar_auto_sync_at` (FR-057a): dois
    # processos expirando a mesma reserva ao mesmo tempo é a corrida que o soft lock existe para
    # evitar.
    virtual_sweep_at = db.Column(db.DateTime, nullable=True)
    # Marcador da última rodada de lembrete de confirmação de convite (feature 231). Mesmo papel
    # de lock dos dois acima — aqui ele é o que impede os 3 workers de mandarem o mesmo e-mail
    # três vezes, que é exatamente o spam que a feature existe para evitar.
    invite_reminder_run_at = db.Column(db.DateTime, nullable=True)
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
      a_pagar   — pendente de pagamento no próximo ciclo (dia 5)
      no_banco  — enviado ao banco, aguardando confirmação de compensação (feature 199)
      pago      — marcado como pago pelo financeiro
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

    # "Devolução a cliente" (feature 224) é o dinheiro que volta para a cliente quando um evento
    # já pago é cancelado. Entra aqui, e não numa entidade própria, porque Gasto Extra já carrega
    # tudo que uma devolução precisa — aprovação, comprovante, PIX do destinatário, status de
    # pago — e já é somado pela Planilha de Pagamentos e pela DRE do período.
    CATEGORIES = [
        "Figurino", "Escritório", "Marketing", "Manutenção", "Devolução a cliente", "Outros",
    ]
    CATEGORY_DEVOLUCAO = "Devolução a cliente"
    STATUSES = ["pendente", "aprovado", "rejeitado"]
    DISBURSEMENT_TYPES = ["reembolso", "fornecedor", "cliente"]

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

    # Vínculo opcional a um pedido de produção de figurino (feature 225). Responde "quanto custou
    # o figurino das Cartas?", que hoje exige ler oito descrições soltas e adivinhar quais são do
    # mesmo trabalho. SET NULL: apagar o pedido não pode apagar o lançamento contábil.
    figurino_producao_id = db.Column(
        db.Integer,
        db.ForeignKey("figurino_producoes.id", ondelete="SET NULL"),
        nullable=True,
    )

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
    figurino_producao = db.relationship(
        "FigurinoProducao", foreign_keys=[figurino_producao_id], lazy=True,
        backref=db.backref("gastos", lazy=True, order_by="SpecialExpense.expense_date"),
    )

    @property
    def receipt_url(self):
        """URL para visualizar o comprovante, ou None se não houver."""
        if not self.receipt_path:
            return None
        return f"/uploads/{self.receipt_path}"

    @property
    def payee_name(self):
        """Nome de quem recebe o desembolso (funcionário, fornecedor ou cliente devolvida)."""
        if self.disbursement_type == "reembolso":
            return self.reimburse_user.name if self.reimburse_user else "—"
        # "cliente" (feature 224) guarda nome e PIX nos mesmos campos do fornecedor: a forma do
        # dado é idêntica (nome livre + chave PIX) e duplicar colunas só para trocar o rótulo
        # obrigaria a mexer em toda query que já lê `supplier_*`.
        if self.disbursement_type in ("fornecedor", "cliente"):
            return self.supplier_name or "—"
        return "—"

    @property
    def payee_pix(self):
        """Chave PIX do destinatário do desembolso, ou ''."""
        if self.disbursement_type == "reembolso":
            return (self.reimburse_user.pix_key or "").strip() if self.reimburse_user else ""
        if self.disbursement_type in ("fornecedor", "cliente"):
            return (self.supplier_pix or "").strip()
        return ""

    @property
    def is_devolucao_cliente(self) -> bool:
        """True se este gasto é uma devolução de dinheiro à cliente (feature 224)."""
        return self.disbursement_type == "cliente"


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

    Estados: ``a_pagar`` (variável preenchida, entra na planilha de pagamentos) → ``no_banco``
    (enviado ao banco, aguardando compensação — feature 199) → ``pago``; ``registrado`` (fixos,
    criado automaticamente, nunca vira pendência); ``pulado`` (variável cujo boleto não veio no
    mês — sem valor). "Aguardando valor" não é linha no banco: é a ausência de lançamento no mês
    para conta variável ativa.
    """
    __tablename__ = "recurring_expense_entries"
    __table_args__ = (
        db.UniqueConstraint("recurring_id", "month_ref", name="uq_recurring_entry_month"),
        db.Index("ix_recurring_entries_month_ref", "month_ref"),
        db.Index("ix_recurring_entries_status", "status"),
    )

    STATUSES = ["a_pagar", "no_banco", "pago", "registrado", "pulado"]

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

class EducaMantoMusical(db.Model):
    """Musical do EducaManto (feature 235) — substitui o antigo pacote por nível.

    Uma linha por espetáculo (ex.: Uma Aventura Animal). Os antigos níveis
    Master/Intermediário/Econômica viraram RESPONSABILIDADES escolhidas por orçamento
    (som/iluminação/alimentação por conta da Manto ou da contratante); os custos de
    cada bloco vivem em colunas próprias e só entram na conta quando o bloco é da Manto.
    Cenário saiu na 4ª rodada: não há custo adicional nem diferença Manto×contratante hoje.
    Ids preservados dos pacotes Master de origem (o "Recalcular" de snapshots antigos depende).
    """
    __tablename__ = "educamanto_musicals"

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(200), nullable=False)
    # Equipe declarada do musical (aparece no PDF e deriva os headcounts). Regra do dono
    # (4ª rodada): personagens = Cara Limpa + Bonecos (+ Papai Noel); produção = item
    # "Produção" — Cenógrafo/Maquiador ficam fora das contagens.
    num_personagens = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    num_producao    = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    # Nº de ensaios do pacote — mínimo de negócio 2 (validação em musical_ops).
    num_ensaios     = db.Column(db.Integer, nullable=False, default=2, server_default="2")
    margin_1s       = db.Column(db.Float, nullable=False, default=1.41)
    margin_2s       = db.Column(db.Float, nullable=False, default=1.70)
    margin_1s_days  = db.Column(db.Float, nullable=False, default=1.50)
    margin_2s_days  = db.Column(db.Float, nullable=False, default=1.80)
    # Default 3 = paridade com produção (todos os musicais reais usam 3; o default antigo 2
    # fazia pacote novo nascer descontando diferente dos existentes).
    discount_days    = db.Column(db.Integer, nullable=False, default=3)
    discount_pct     = db.Column(db.Float, nullable=False, default=0.05)
    # Cachê do ensemble (figurante extra) por cenário — somado por ensemble no orçamento.
    ensemble_1s      = db.Column(db.Float, nullable=False, default=350, server_default="350")
    ensemble_2s      = db.Column(db.Float, nullable=False, default=600, server_default="600")
    ensemble_1s_days = db.Column(db.Float, nullable=False, default=300, server_default="300")
    ensemble_2s_days = db.Column(db.Float, nullable=False, default=550, server_default="550")
    # Som/iluminação NÃO ficam aqui: são a tabela única por combinação em
    # `pricing_config['educamanto_som_luz']` (3ª rodada, valores reais — os preços não são
    # aditivos e a equipe técnica já está dentro). Cenário não tem custo (4ª rodada).
    # Alimentação do DIA DO EVENTO, POR PESSOA (headcount do evento) — migrada do item
    # "Catering apresentação" (55 em 1 sessão, 73 em 2 sessões; diárias usam os mesmos valores).
    custo_alimentacao_1s = db.Column(db.Float, nullable=False, default=55, server_default="55")
    custo_alimentacao_2s = db.Column(db.Float, nullable=False, default=73, server_default="73")
    # Custos POR PESSOA POR ENSAIO (headcount de ensaio × num_ensaios) — migrados dos itens
    # "Catering ensaio" (28) e "Ajuda de custo ensaio" (50).
    custo_catering_ensaio_pp = db.Column(db.Float, nullable=False, default=28, server_default="28")
    custo_ajuda_ensaio_pp    = db.Column(db.Float, nullable=False, default=50, server_default="50")
    created_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    items = db.relationship(
        "EducaMantoMusicalItem",
        backref="musical",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="EducaMantoMusicalItem.sort_order",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "num_personagens": self.num_personagens,
            "num_producao": self.num_producao,
            "num_ensaios": self.num_ensaios,
            "margin_1s": self.margin_1s,
            "margin_2s": self.margin_2s,
            "margin_1s_days": self.margin_1s_days,
            "margin_2s_days": self.margin_2s_days,
            "discount_days": self.discount_days,
            "discount_pct": self.discount_pct,
            "ensemble_1s": self.ensemble_1s,
            "ensemble_2s": self.ensemble_2s,
            "ensemble_1s_days": self.ensemble_1s_days,
            "ensemble_2s_days": self.ensemble_2s_days,
            "custo_alimentacao_1s": self.custo_alimentacao_1s,
            "custo_alimentacao_2s": self.custo_alimentacao_2s,
            "custo_catering_ensaio_pp": self.custo_catering_ensaio_pp,
            "custo_ajuda_ensaio_pp": self.custo_ajuda_ensaio_pp,
            "items": [item.to_dict() for item in self.items],
        }

    def to_dict_basico(self) -> dict:
        """Payload SEM custos/margens — listagem da calculadora e visão de papel não-superadmin."""
        return {
            "id": self.id,
            "name": self.name,
            "num_personagens": self.num_personagens,
            "num_producao": self.num_producao,
            "num_ensaios": self.num_ensaios,
        }


class EducaMantoMusicalItem(db.Model):
    """Linha de custo sempre inclusa de um musical (elenco, produção, gráfica…)."""
    __tablename__ = "educamanto_musical_items"

    id           = db.Column(db.Integer, primary_key=True)
    musical_id   = db.Column(db.Integer, db.ForeignKey("educamanto_musicals.id"), nullable=False)
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
    video_url               = db.Column(db.String(500), nullable=True)  # feature 185 — Drive/MP4/Vimeo

    categories = db.relationship("CatalogCategory", secondary=catalog_item_categories, lazy=True)
    images     = db.relationship(
        "CatalogItemImage", backref="item", lazy=True,
        cascade="all, delete-orphan", order_by="CatalogItemImage.position",
    )
    # `foreign_keys` explícito: CatalogCharacter tem DOIS FKs para catalog_items desde a
    # feature 209 (o tema pai e a página própria `own_item_id`) — sem isto o mapper falha
    # com AmbiguousForeignKeysError no boot.
    characters = db.relationship(
        "CatalogCharacter", backref="tema", lazy=True,
        foreign_keys="CatalogCharacter.catalog_item_id",
        cascade="all, delete-orphan", order_by="CatalogCharacter.position",
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


class CatalogCharacter(db.Model):
    """Personagem filho de um Tema do catálogo (feature 185).

    Entidade vendável independente do Tema pai: tem foto, vídeo e link direto opcionais, e pode
    ser vinculada a uma ``FigurinoSheet`` para auto-preencher o elenco de um evento (ver
    ``app/admin/catalog_character_ops.py`` e ``specs/185-catalogo-vitrine-completo/``).
    """
    __tablename__ = "catalog_characters"
    __table_args__ = (
        db.Index("ix_catalog_characters_catalog_item_id", "catalog_item_id"),
    )

    id                 = db.Column(db.Integer, primary_key=True)
    catalog_item_id    = db.Column(
        db.Integer, db.ForeignKey("catalog_items.id", ondelete="CASCADE"), nullable=False
    )
    name               = db.Column(db.String(200), nullable=False)
    slug               = db.Column(db.String(240), nullable=False, unique=True)
    photo_url          = db.Column(db.String(500), nullable=True)
    video_url          = db.Column(db.String(500), nullable=True)
    figurino_sheet_id  = db.Column(
        db.Integer, db.ForeignKey("figurino_sheets.id", ondelete="SET NULL"), nullable=True
    )
    # Página própria do personagem (feature 209, caso "Coelho Branco" dentro do tema Alice):
    # aponta para o CatalogItem que É a página/busca deste personagem. UNIQUE — um item só
    # pode ser página de um personagem. NULL = personagem só existe no elenco do tema.
    own_item_id        = db.Column(
        db.Integer,
        db.ForeignKey("catalog_items.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    position           = db.Column(db.Integer, default=0, nullable=False)
    is_active          = db.Column(db.Boolean, default=True, nullable=False)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    figurino_sheet = db.relationship("FigurinoSheet", lazy=True)
    # `as_character` no CatalogItem: o personagem cuja página própria é este item (ou None).
    own_item = db.relationship(
        "CatalogItem",
        foreign_keys=[own_item_id],
        backref=db.backref("as_character", uselist=False),
        lazy=True,
    )


# ── Impressões e Acervo 3D (feature 200) ────────────────────────────────────


class Acervo3DItem(db.Model):
    """Modelo 3D base do acervo — o "catálogo de peças" do Artista 3D (feature 200).

    A foto (``photo_url``) é obrigatória porque toda seleção de peça 3D é visual (Princípio X.2 —
    miniatura quadrada ao lado do nome, tanto na busca quanto no valor já selecionado).

    Os arquivos 3D ficam em ``Acervo3DFile`` (1:N, feature 201): um mesmo presente costuma ser
    fatiado em várias partes (corpo, argola, base), e cada parte é um arquivo próprio. A regra de
    negócio exige **pelo menos um** arquivo — uma peça sem arquivo não é imprimível.
    """

    __tablename__ = "acervo_3d_items"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    # URL pública da foto de preview (JPG/PNG) — sempre presente.
    photo_url  = db.Column(db.String(500), nullable=False)
    is_active  = db.Column(db.Boolean, default=True, nullable=False, server_default="1")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    files = db.relationship(
        "Acervo3DFile", back_populates="item", lazy="joined",
        cascade="all, delete-orphan", order_by="Acervo3DFile.position",
    )


class Acervo3DFile(db.Model):
    """Um arquivo 3D bruto (``.stl``/``.3mf``/``.zip``) de uma peça do Acervo (feature 201).

    Existe porque um presente raramente é um arquivo só: o modelo vem fatiado em partes, e o
    Artista 3D precisa baixar todas. ``original_name`` guarda o nome que o usuário enviou — o
    caminho salvo é um UUID, e "corpo.stl"/"argola.stl" é o que diz qual parte é qual.
    """

    __tablename__ = "acervo_3d_files"
    __table_args__ = (
        db.Index("ix_acervo_3d_files_item_id", "item_id"),
    )

    id            = db.Column(db.Integer, primary_key=True)
    item_id       = db.Column(
        db.Integer, db.ForeignKey("acervo_3d_items.id", ondelete="CASCADE"), nullable=False
    )
    file_path     = db.Column(db.String(500), nullable=False)
    original_name = db.Column(db.String(255), nullable=True)
    position      = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    item = db.relationship("Acervo3DItem", back_populates="files", lazy=True)


class Event3DGift(db.Model):
    """Presente 3D vinculado a um evento (relação 1:N com ``CalendarEvent``, feature 200).

    Um evento SHOW pode ter vários presentes; cada linha aponta para uma peça do
    ``Acervo3DItem`` e carrega a quantidade, o prazo e o estado de produção. ``status`` percorre
    ``GIFT_3D_STATUSES`` (``pendente`` → ``imprimindo`` → ``finalizado`` → ``entregue``); só o
    que ainda não está ``entregue`` aparece na Fila de Impressão.
    """

    __tablename__ = "event_3d_gifts"
    __table_args__ = (
        db.Index("ix_event_3d_gifts_event_id", "event_id"),
        db.Index("ix_event_3d_gifts_item_id",  "item_id"),
        db.Index("ix_event_3d_gifts_status",   "status"),
    )

    id            = db.Column(db.Integer, primary_key=True)
    event_id      = db.Column(
        db.Integer, db.ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False
    )
    item_id       = db.Column(
        db.Integer, db.ForeignKey("acervo_3d_items.id"), nullable=False
    )
    status        = db.Column(
        db.String(20), nullable=False,
        default=GIFT_3D_STATUS_PENDENTE, server_default=GIFT_3D_STATUS_PENDENTE,
    )
    deadline_date = db.Column(db.Date, nullable=True)
    quantity      = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    notes         = db.Column(db.Text, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event = db.relationship(
        "CalendarEvent", lazy=True,
        backref=db.backref(
            "presentes_3d", lazy=True, cascade="all, delete-orphan",
            order_by="Event3DGift.id",
        ),
    )
    item = db.relationship("Acervo3DItem", lazy="joined", backref=db.backref("gifts", lazy=True))


class Event3DDismissal(db.Model):
    """Dispensa da pendência "show sem presente 3D" de um evento (feature 202).

    Todo evento SHOW futuro sem nenhum ``Event3DGift`` vira uma tarefa na Fila de Impressão —
    é o evento que gera o trabalho, não o presente. Nem todo show leva presente, então esta
    tabela registra "este aqui não leva", tirando a tarefa da fila sem inventar um presente
    fantasma. Mesmo padrão de ``FigurinoMissingDismissal`` (feature 183) e de
    ``EventRole.dismissed_at`` (feature 108).

    A dispensa é reversível (basta apagar a linha) e é descartada automaticamente quando alguém
    vincula um presente ao evento — se leva presente, a decisão anterior deixou de valer.
    """

    __tablename__ = "event_3d_dismissals"

    id           = db.Column(db.Integer, primary_key=True)
    event_id     = db.Column(
        db.Integer, db.ForeignKey("calendar_events.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    dismissed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dismissed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    event     = db.relationship(
        "CalendarEvent", lazy=True,
        backref=db.backref("dispensa_3d", uselist=False, cascade="all, delete-orphan"),
    )
    dismisser = db.relationship("User", lazy=True, foreign_keys=[dismissed_by])


# ── Gestão de Marketing e Frequência (feature 204) ──────────────────────────


marketing_post_temas = db.Table(
    "marketing_post_temas",
    db.Column(
        "post_id", db.Integer,
        db.ForeignKey("marketing_posts.id", ondelete="CASCADE"), primary_key=True,
    ),
    db.Column(
        "catalog_item_id", db.Integer,
        db.ForeignKey("catalog_items.id", ondelete="CASCADE"), primary_key=True,
    ),
    db.Index("ix_marketing_post_temas_catalog_item_id", "catalog_item_id"),
)
"""Tabela de associação N:N entre ``MarketingPost`` e ``CatalogItem`` (feature 204+).

Um post pode falar de vários Temas ao mesmo tempo (ex.: um Reels que junta "15 Anos" e "Debutante"
no mesmo vídeo) — por isso a relação nasceu N:N em vez de uma segunda FK direta em
``marketing_posts``. ``ondelete="CASCADE"`` dos dois lados: a linha de associação não tem sentido
sem o post nem sem o Tema."""


class MarketingPost(db.Model):
    """Postagem planejada pela equipe de marketing — o card do Kanban (feature 204).

    ``status`` percorre ``MARKETING_STATUSES`` (``ideia`` → ``producao`` → ``revisao`` →
    ``agendado`` → ``publicado``); ``publish_date`` é a data em que o post foi (ou será)
    publicado e é o que alimenta o cálculo de frequência de ``MarketingFrequencyGoal``.

    Os três vínculos existem para o post não virar uma ilha:
    - ``temas`` — os **Temas** do catálogo de que o post fala (N:N — é por eles que a meta de
      frequência sabe que "15 Anos" foi postado, mesmo quando o post junta vários assuntos);
    - ``review_space_id`` — vínculo **1:1** com o módulo de Revisão de Mídia (feature 088): o
      material do post é aprovado lá, não numa segunda ferramenta paralela;
    - ``assignee_id`` — quem está com o card na mão.

    ``drive_folder_url`` é só texto de propósito: o acervo bruto (raw de filmagem) continua no
    Google Drive do time; o sistema guarda o atalho, não o arquivo.
    """

    __tablename__ = "marketing_posts"
    __table_args__ = (
        db.Index("ix_marketing_posts_status", "status"),
        db.Index("ix_marketing_posts_publish_date", "publish_date"),
    )

    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(200), nullable=False)
    status           = db.Column(
        db.String(20), nullable=False, default="ideia", server_default="ideia",
    )
    deadline_date    = db.Column(db.Date, nullable=True)
    publish_date     = db.Column(db.Date, nullable=True)
    platform         = db.Column(db.String(40), nullable=True)
    drive_folder_url = db.Column(db.Text, nullable=True)
    notes            = db.Column(db.Text, nullable=True)

    assignee_id      = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_space_id  = db.Column(
        db.Integer, db.ForeignKey("review_spaces.id", ondelete="SET NULL"),
        nullable=True, unique=True,
    )

    created_at       = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    assignee     = db.relationship("User", lazy="joined", foreign_keys=[assignee_id])
    temas        = db.relationship("CatalogItem", secondary=marketing_post_temas, lazy="joined")
    review_space = db.relationship("ReviewSpace", lazy="joined")


class MarketingFrequencyGoal(db.Model):
    """Meta de frequência de postagem — "postar sobre 15 Anos a cada 15 dias" (feature 204).

    O motor de metas não guarda estado de cumprimento: ``last_posted_date`` e o status derivado
    (``on_track``/``delayed``) são **calculados na leitura** a partir dos ``MarketingPost`` já
    publicados (ver ``app/marketing/marketing_ops.py``). Assim nada precisa ser recalculado por
    job noturno, e mover um card para "publicado" já conserta a saúde da meta na hora.

    ``catalog_item_id`` é opcional: com Tema vinculado, o casamento é exato (o post aponta para o
    mesmo Tema); sem Tema, cai no casamento por ``name`` no título do post — é o caso de assunto
    que não existe como item do catálogo (ex.: "Bastidores").
    """

    __tablename__ = "marketing_frequency_goals"
    __table_args__ = (
        db.Index("ix_marketing_frequency_goals_catalog_item_id", "catalog_item_id"),
    )

    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(200), nullable=False)
    target_interval_days = db.Column(db.Integer, nullable=False)
    catalog_item_id     = db.Column(
        db.Integer, db.ForeignKey("catalog_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at          = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    catalog_item = db.relationship("CatalogItem", lazy="joined")


# ── Loja de Interações Virtuais (feature 205) ───────────────────────────────
#
# Canal B2C self-service que vende chamadas de vídeo de 10 min e vídeos gravados com Personagens
# do catálogo. Duas regras atravessam todas as tabelas abaixo:
#
# 1. **Dinheiro é sempre Numeric(12, 2)** (Princípio IX). A InfinitePay conta em centavos inteiros,
#    mas isso é característica do fornecedor: a conversão vive só em
#    `app/integracoes/infinitepay_client.py`. Nenhuma coluna aqui representa centavos.
# 2. **Nada é decidido pelo aviso de pagamento.** O webhook da operadora não é assinado, então ele
#    serve de gatilho; a verdade vem da reconsulta da cobrança. É por isso que existem
#    `VirtualPaymentNotification` (auditoria + idempotência) e `recheck_attempts`.


virtual_campaign_acervo = db.Table(
    "virtual_campaign_acervo",
    db.Column(
        "campaign_id", db.Integer,
        db.ForeignKey("virtual_campaigns.id", ondelete="CASCADE"), primary_key=True,
    ),
    db.Column(
        "acervo_3d_item_id", db.Integer,
        db.ForeignKey("acervo_3d_items.id", ondelete="CASCADE"), primary_key=True,
    ),
)
"""Peças do Acervo 3D liberadas para oferta numa campanha (feature 205, FR-006).

``CASCADE`` dos dois lados: a linha de associação não faz sentido sem a campanha nem sem a peça.
Liberar uma peça é decisão por campanha — o Acervo inteiro nunca é ofertado por padrão."""


class VirtualCampaign(db.Model):
    """A oferta publicada de um Personagem do catálogo (feature 205).

    Guarda tudo que a família lê antes de comprar (textos, capa, FAQ, prazo) e o estoque de vídeos
    gravados; os horários das chamadas vivem em ``VirtualCampaignSlot``. O vínculo é com
    ``CatalogCharacter`` — esta feature não cria cadastro paralelo de personagens (Princípio I).

    ``talent_id``/``figurino_sheet_id`` são o que a automação usa para pré-escalar o elenco quando
    a venda se efetiva; o padrão sugerido vem do figurino já vinculado ao personagem no catálogo.
    """

    __tablename__ = "virtual_campaigns"
    __table_args__ = (
        db.Index("ix_virtual_campaigns_status", "status"),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    catalog_character_id = db.Column(
        db.Integer, db.ForeignKey("catalog_characters.id"), nullable=False
    )
    slug                 = db.Column(db.String(160), nullable=False, unique=True)
    status               = db.Column(
        db.String(20), nullable=False,
        default=VIRTUAL_CAMPAIGN_STATUS_RASCUNHO, server_default=VIRTUAL_CAMPAIGN_STATUS_RASCUNHO,
    )
    title                = db.Column(db.String(200), nullable=False)
    intro_html           = db.Column(db.Text, nullable=True)
    tolerance_terms      = db.Column(db.Text, nullable=True)
    # JSON: [{"pergunta": ..., "resposta": ...}] — renderizado só no fim da landing (FR-013).
    faq_json             = db.Column(db.Text, nullable=True)
    cover_url            = db.Column(db.String(500), nullable=True)
    whatsapp_phone       = db.Column(db.String(20), nullable=True)

    # Dinheiro em Numeric — ver a nota do bloco (Princípio IX).
    price_live           = db.Column(db.Numeric(12, 2), nullable=False)
    price_recorded       = db.Column(db.Numeric(12, 2), nullable=False)
    price_gift           = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")

    recorded_capacity      = db.Column(db.Integer, nullable=False, server_default="0")
    recorded_sold          = db.Column(db.Integer, nullable=False, server_default="0")
    recorded_delivery_days = db.Column(db.Integer, nullable=False, server_default="7")

    talent_id            = db.Column(db.Integer, db.ForeignKey("talents.id"), nullable=True)
    figurino_sheet_id    = db.Column(
        db.Integer, db.ForeignKey("figurino_sheets.id", ondelete="SET NULL"), nullable=True
    )

    max_reservations_per_origin = db.Column(db.Integer, nullable=False, server_default="5")
    reservation_window_minutes  = db.Column(db.Integer, nullable=False, server_default="60")

    created_at = db.Column(db.DateTime, default=now_sp, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=now_sp, onupdate=now_sp, nullable=False
    )

    character      = db.relationship("CatalogCharacter", lazy="joined")
    talent         = db.relationship("Talent", lazy="joined")
    figurino_sheet = db.relationship("FigurinoSheet", lazy=True)
    acervo_items   = db.relationship("Acervo3DItem", secondary=virtual_campaign_acervo, lazy=True)
    slots          = db.relationship(
        "VirtualCampaignSlot", back_populates="campaign", lazy=True,
        cascade="all, delete-orphan", order_by="VirtualCampaignSlot.start_at",
    )

    @property
    def faq_items(self) -> list:
        """Itens do FAQ decodificados (lista vazia se o JSON estiver corrompido)."""
        import json

        try:
            data = json.loads(self.faq_json or "[]")
        except (ValueError, TypeError):
            return []
        return data if isinstance(data, list) else []

    @property
    def recorded_available(self) -> int:
        """Quantos vídeos gravados ainda cabem na campanha (nunca negativo)."""
        return max((self.recorded_capacity or 0) - (self.recorded_sold or 0), 0)

    @property
    def is_public(self) -> bool:
        """True quando a campanha aceita novas reservas (FR-007)."""
        return self.status == VIRTUAL_CAMPAIGN_STATUS_PUBLICADA


class VirtualCampaignSlot(db.Model):
    """Um horário de 10 minutos vendável de uma campanha (feature 205).

    ``UNIQUE(campaign_id, start_at)`` é o que torna a geração de horários idempotente: reexecutar a
    mesma janela não duplica nada (FR-004).

    Um slot está disponível quando ``status == 'livre'`` **ou** quando está ``'travado'`` com
    ``locked_until`` já vencido. A segunda condição é o que faz a expiração funcionar mesmo se a
    varredura atrasar — quem abre a landing já vê o horário livre, sem depender de job.
    """

    __tablename__ = "virtual_campaign_slots"
    __table_args__ = (
        db.UniqueConstraint("campaign_id", "start_at", name="uq_virtual_slot_campaign_start"),
        db.Index("ix_virtual_campaign_slots_status", "status"),
        db.Index("ix_virtual_campaign_slots_start_at", "start_at"),
    )

    id           = db.Column(db.Integer, primary_key=True)
    campaign_id  = db.Column(
        db.Integer, db.ForeignKey("virtual_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    start_at     = db.Column(db.DateTime, nullable=False)
    status       = db.Column(
        db.String(20), nullable=False,
        default=VIRTUAL_SLOT_STATUS_LIVRE, server_default=VIRTUAL_SLOT_STATUS_LIVRE,
    )
    locked_until = db.Column(db.DateTime, nullable=True)
    order_id     = db.Column(db.Integer, db.ForeignKey("virtual_orders.id"), nullable=True)
    created_at   = db.Column(db.DateTime, default=now_sp, nullable=False)

    campaign = db.relationship("VirtualCampaign", back_populates="slots", lazy=True)

    def is_available(self, now=None) -> bool:
        """True se o horário pode ser reservado agora (livre, ou travado com lock vencido).

        ``now`` deve vir em **naive São Paulo** (use ``virtuais_ops.agora()``), a mesma convenção
        de ``start_at`` e ``locked_until``. O padrão existe só para chamadas soltas; quem compara
        contra horário de slot sempre passa o valor explicitamente.
        """
        moment = now or now_sp()
        if self.status == VIRTUAL_SLOT_STATUS_LIVRE:
            return True
        if self.status == VIRTUAL_SLOT_STATUS_TRAVADO:
            return self.locked_until is not None and self.locked_until <= moment
        return False


class VirtualOrder(db.Model):
    """A intenção de compra de uma família (feature 205).

    ``order_nsu`` é o identificador que viaja até a InfinitePay e volta em todo aviso — é a chave
    que liga notificação a pedido e a base da idempotência. ``public_token`` é o endereço não
    adivinhável da página de acompanhamento; sozinho ele só mostra status e horário: qualquer dado
    da criança exige também o telefone da compradora (FR-044a).

    Os valores são congelados na reserva (FR-022) — alterar o preço da campanha depois não mexe em
    pedido nenhum. Todos em ``Numeric``, ver a nota do bloco.
    """

    __tablename__ = "virtual_orders"
    __table_args__ = (
        db.Index("ix_virtual_orders_status", "status"),
        db.Index("ix_virtual_orders_campaign_id", "campaign_id"),
        db.Index("ix_virtual_orders_contact_phone", "contact_phone"),
        db.Index("ix_virtual_orders_created_at", "created_at"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("virtual_campaigns.id"), nullable=False)
    slot_id     = db.Column(db.Integer, db.ForeignKey("virtual_campaign_slots.id"), nullable=True)
    modality    = db.Column(db.String(12), nullable=False)
    status      = db.Column(
        db.String(16), nullable=False,
        default=VIRTUAL_ORDER_STATUS_RESERVADO, server_default=VIRTUAL_ORDER_STATUS_RESERVADO,
    )
    order_nsu    = db.Column(db.String(64), nullable=False, unique=True)
    public_token = db.Column(db.String(43), nullable=False, unique=True)

    # Ficha da criança — dados sensíveis, só saem sob validação dupla (FR-044a).
    child_name            = db.Column(db.String(120), nullable=False)
    child_age             = db.Column(db.Integer, nullable=False)
    behavior_notes        = db.Column(db.Text, nullable=True)
    contact_phone         = db.Column(db.String(20), nullable=False)
    contact_phone_display = db.Column(db.String(30), nullable=True)
    contact_email         = db.Column(db.String(180), nullable=False)
    delivery_address      = db.Column(db.String(300), nullable=True)

    gift_item_id = db.Column(db.Integer, db.ForeignKey("acervo_3d_items.id"), nullable=True)

    price_interaction = db.Column(db.Numeric(12, 2), nullable=False)
    price_gift        = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")
    total_value       = db.Column(db.Numeric(12, 2), nullable=False)

    locked_until    = db.Column(db.DateTime, nullable=True)
    payment_url     = db.Column(db.String(500), nullable=True)
    invoice_slug    = db.Column(db.String(120), nullable=True)
    transaction_nsu = db.Column(db.String(120), nullable=True)
    paid_at         = db.Column(db.DateTime, nullable=True)

    event_id = db.Column(db.Integer, db.ForeignKey("calendar_events.id"), nullable=True)
    # Link da SALA (Google Meet) — é o que a família recebe. Distinto de
    # `CalendarEvent.google_html_link`, que abre o Calendar e exige login no calendário.
    meet_url     = db.Column(db.String(500), nullable=True)
    meet_pending = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    # Progresso da política de retry da sala (FR-056/FR-057). `meet_pending` diz *que* falta sala;
    # estes dois dizem *onde a política parou* — e precisam ser coluna, não memória, porque a
    # varredura decide num ciclo e volta no seguinte, possivelmente em outro worker.
    meet_attempts        = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    meet_last_attempt_at = db.Column(db.DateTime, nullable=True)

    origin_hash = db.Column(db.String(64), nullable=True)
    # Token do navegador que criou a reserva. Existe para o duplo clique devolver o mesmo pedido
    # em vez de travar um segundo horário (FR-026). Não dá para usar `origin_hash` no lugar: duas
    # famílias atrás do mesmo NAT compartilham origem, e uma receberia o pedido da outra.
    client_token = db.Column(db.String(64), nullable=True)
    # Tolerância quando a operadora não responde na expiração (FR-018a, FR-056).
    grace_until        = db.Column(db.DateTime, nullable=True)
    recheck_attempts   = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    expired_unverified = db.Column(
        db.Boolean, nullable=False, default=False, server_default="0"
    )
    # Tentativas de telefone na página do pedido (FR-044b).
    access_attempts      = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    access_blocked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=now_sp, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=now_sp, onupdate=now_sp, nullable=False
    )

    campaign  = db.relationship("VirtualCampaign", lazy="joined")
    slot      = db.relationship("VirtualCampaignSlot", foreign_keys=[slot_id], lazy=True)
    gift_item = db.relationship("Acervo3DItem", lazy="joined")
    event     = db.relationship("CalendarEvent", lazy=True)


class VirtualPaymentNotification(db.Model):
    """Cada aviso de pagamento recebido da operadora (feature 205).

    Existe por três motivos inseparáveis:

    * **idempotência** — ``UNIQUE(transaction_nsu)`` faz a reentrega do mesmo aviso falhar na
      inserção, e é isso que impede evento, escala, presente e baixa de estoque duplicados
      (FR-028);
    * **segurança** — registra se o segredo do endereço conferia e o que a reconsulta na operadora
      respondeu; a decisão nunca vem do corpo do aviso (FR-027a/FR-027b);
    * **auditoria** — nada é descartado, nem aviso órfão, nem chamada com segredo errado (FR-034).
    """

    __tablename__ = "virtual_payment_notifications"
    __table_args__ = (
        db.Index("ix_virtual_payment_notifications_order_id", "order_id"),
    )

    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey("virtual_orders.id"), nullable=True)
    order_nsu       = db.Column(db.String(64), nullable=True)
    transaction_nsu = db.Column(db.String(120), nullable=True, unique=True)
    raw_payload     = db.Column(db.Text, nullable=True)
    secret_ok       = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    # 'paid' | 'unpaid' | 'divergent' | 'unavailable' | 'error'
    recheck_result  = db.Column(db.String(20), nullable=True)
    recheck_payload = db.Column(db.Text, nullable=True)
    # 'efetivado' | 'duplicado' | 'recusado' | 'conflito' | 'retido' | 'orfao'
    outcome         = db.Column(db.String(24), nullable=True)
    message         = db.Column(db.Text, nullable=True)
    created_at      = db.Column(db.DateTime, default=now_sp, nullable=False)

    order = db.relationship(
        "VirtualOrder", lazy=True, backref=db.backref("notifications", lazy=True)
    )


class VirtualMediaDelivery(db.Model):
    """A unidade de trabalho da Fila de Produção de Mídia (feature 205).

    Nasce de um pedido pago (1:1) e percorre ``pendente`` → ``gravando`` → ``finalizado``, os três
    únicos estados (FR-048a). Enviar o vídeo é a **ação** que permite chegar a ``finalizado``,
    nunca um estado próprio.

    ``video_path`` é caminho interno de armazenamento e **não é divulgável**: o vídeo só sai por um
    endpoint que valida o acesso a cada requisição (FR-038e). Um vídeo em que o nome da criança é
    dito em voz alta não pode depender de o endereço não vazar.
    """

    __tablename__ = "virtual_media_deliveries"
    __table_args__ = (
        db.Index("ix_virtual_media_deliveries_status", "status"),
        db.Index("ix_virtual_media_deliveries_due_date", "due_date"),
    )

    id       = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("virtual_orders.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    status   = db.Column(
        db.String(16), nullable=False,
        default=VIRTUAL_PRODUCTION_STATUS_PENDENTE,
        server_default=VIRTUAL_PRODUCTION_STATUS_PENDENTE,
    )
    due_date = db.Column(db.Date, nullable=True)

    video_path         = db.Column(db.String(500), nullable=True)
    video_mime         = db.Column(db.String(60), nullable=True)
    video_size_bytes   = db.Column(db.BigInteger, nullable=True)
    video_published_at = db.Column(db.DateTime, nullable=True)
    last_upload_error  = db.Column(db.Text, nullable=True)
    # Quando a equipe foi alertada do prazo se aproximando (FR-057). Marcador de idempotência, não
    # de status: sem ele a varredura alertaria a cada ciclo, e alerta de minuto em minuto é alerta
    # que ninguém lê.
    deadline_alert_at  = db.Column(db.DateTime, nullable=True)

    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at    = db.Column(db.DateTime, default=now_sp, nullable=False)
    updated_at    = db.Column(
        db.DateTime, default=now_sp, onupdate=now_sp, nullable=False
    )

    order = db.relationship(
        "VirtualOrder", lazy="joined",
        backref=db.backref("media_delivery", uselist=False, cascade="all, delete-orphan"),
    )
    updated_by = db.relationship("User", lazy=True)


class VirtualRefundRequest(db.Model):
    """Devolução a executar quando um pagamento cai em horário indisponível (feature 205).

    Existe porque a InfinitePay não publica API de estorno: o sistema garante que a devolução seja
    aberta, rastreada e cobrada até a conclusão, mas quem devolve o dinheiro é uma pessoa, no
    painel da operadora (FR-042/FR-043). ``invoice_slug`` e ``transaction_nsu`` estão aqui para a
    equipe achar a cobrança sem sair procurando.
    """

    __tablename__ = "virtual_refund_requests"
    __table_args__ = (
        db.Index("ix_virtual_refund_requests_status", "status"),
    )

    id              = db.Column(db.Integer, primary_key=True)
    order_id        = db.Column(db.Integer, db.ForeignKey("virtual_orders.id"), nullable=False)
    amount          = db.Column(db.Numeric(12, 2), nullable=False)
    reason          = db.Column(db.String(40), nullable=False, server_default="conflito_horario")
    status          = db.Column(
        db.String(16), nullable=False,
        default=VIRTUAL_REFUND_STATUS_PENDENTE, server_default=VIRTUAL_REFUND_STATUS_PENDENTE,
    )
    invoice_slug    = db.Column(db.String(120), nullable=True)
    transaction_nsu = db.Column(db.String(120), nullable=True)
    resolved_by_id  = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at     = db.Column(db.DateTime, nullable=True)
    created_at      = db.Column(db.DateTime, default=now_sp, nullable=False)

    order       = db.relationship("VirtualOrder", lazy="joined")
    resolved_by = db.relationship("User", lazy=True)


class VirtualOrderNotification(db.Model):
    """Registro de cada aviso automático enviado à família (feature 205).

    **É a trava de idempotência do aviso**, não só um log: ``UNIQUE(order_id, kind)`` garante que
    cada tipo saia no máximo uma vez por pedido (FR-028a). A linha é gravada na mesma transação que
    decide enviar, **antes** do disparo — a violação de unicidade é o que impede o segundo envio
    quando a operadora reentrega o mesmo aviso de pagamento (FR-028b).

    Reenvio deliberado pela equipe apaga a linha; nunca burla a restrição.
    """

    __tablename__ = "virtual_order_notifications"
    __table_args__ = (
        db.UniqueConstraint("order_id", "kind", name="uq_virtual_order_notification_kind"),
    )

    id            = db.Column(db.Integer, primary_key=True)
    order_id      = db.Column(
        db.Integer, db.ForeignKey("virtual_orders.id", ondelete="CASCADE"), nullable=False
    )
    kind          = db.Column(db.String(24), nullable=False)
    sent_ok       = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    error_message = db.Column(db.Text, nullable=True)
    created_at    = db.Column(db.DateTime, default=now_sp, nullable=False)
    # Progresso da entrega deste aviso (FR-056). A **trava** é do aviso (`UNIQUE(order_id, kind)`,
    # um por pedido e tipo); o **retry** é da entrega dele. Separar os dois é o que permite
    # retentar o envio sem nunca abrir brecha para um segundo e-mail.
    attempts        = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    last_attempt_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship(
        "VirtualOrder", lazy=True,
        backref=db.backref("sent_notifications", lazy=True, cascade="all, delete-orphan"),
    )


class EmailBounce(db.Model):
    """Uma devolução de email detectada na caixa do remetente (feature 219).

    O talento se cadastra com o email errado (``hotmail.con``) ou com a caixa lotada, e a falha só
    aparece como um aviso do Mail Delivery Subsystem na caixa de quem enviou — invisível para o
    sistema. Uma varredura IMAP periódica lê essas devoluções, extrai o destinatário e o motivo do
    bloco ``message/delivery-status``, e vira fila de contato para o casting.

    **Só grava quando o destinatário casa com um talento ou usuário da plataforma.** Devolução de
    email pessoal de quem opera a conta não entra no banco — o escopo é a comunicação da Manto.

    Uma linha por mensagem de devolução (``message_id`` único = idempotência: reler a caixa não
    duplica). O agrupamento por endereço é feito na leitura, em `bounce_ops.pending_queue`.
    """

    __tablename__ = "email_bounces"
    __table_args__ = (
        db.Index("ix_email_bounces_email", "email"),
        db.Index("ix_email_bounces_talent_id", "talent_id"),
        db.Index("ix_email_bounces_resolved_at", "resolved_at"),
    )

    id = db.Column(db.Integer, primary_key=True)

    # `Message-Id` da devolução — a trava de idempotência da varredura.
    message_id = db.Column(db.String(300), nullable=False, unique=True)

    # Endereço que falhou, sempre minúsculo (`Final-Recipient`).
    email = db.Column(db.String(200), nullable=False)
    talent_id = db.Column(db.Integer, db.ForeignKey("talents.id", ondelete="CASCADE"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Classificação derivada do código estendido — a ação do casting muda com ela:
    # caixa_cheia → avisar para liberar espaço; endereco_invalido/dominio_invalido → pegar o
    # email certo; bloqueado/outro → investigar.
    kind = db.Column(db.String(24), nullable=False)
    # `Action:` do DSN — "failed" (definitivo) ou "delayed" (o servidor ainda vai retentar).
    is_permanent = db.Column(db.Boolean, nullable=False, default=True, server_default="1")

    status_code = db.Column(db.String(12), nullable=True)   # "5.1.2", "4.2.2"…
    diagnostic = db.Column(db.Text, nullable=True)          # `Diagnostic-Code`, para depurar
    original_subject = db.Column(db.String(300), nullable=True)  # qual mensagem voltou

    occurred_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Resolução é por **endereço**, não por mensagem: marcar resolvido carimba todas as linhas
    # daquele email (ver `bounce_ops.resolve_email`).
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note = db.Column(db.Text, nullable=True)

    talent = db.relationship("Talent", lazy="joined", foreign_keys=[talent_id])
    user = db.relationship("User", lazy="joined", foreign_keys=[user_id])
    resolved_by = db.relationship("User", lazy=True, foreign_keys=[resolved_by_id])


class FigurinoProducao(db.Model):
    """Pedido de produção de uma peça de figurino (feature 225).

    É a entidade que faltava entre o catálogo e o caixa. ``FigurinoSheet`` descreve o figurino
    **pronto** de um personagem (a peça é uma string dentro de um JSON, sem identidade);
    ``SpecialExpense`` registra o dinheiro **depois** que saiu. No meio — o trabalho de produzir,
    com responsável, prazo e evolução — não havia nada, e por isso os oito lançamentos do figurino
    das Cartas (Alice/Cuiabá) ficam soltos, sem nada dizendo que são um trabalho só.

    O vínculo com evento e com ficha é **opcional** de propósito: cinco dos 40 gastos de figurino
    de hoje são produção de acervo, sem show ("Mascotes Copa 4/4", "SAPATO GABBY HUMANA").
    """

    __tablename__ = "figurino_producoes"
    __table_args__ = (
        db.Index("ix_figurino_producoes_status", "status"),
        db.Index("ix_figurino_producoes_responsible_id", "responsible_id"),
        db.Index("ix_figurino_producoes_event_id", "event_id"),
        db.Index("ix_figurino_producoes_due_date", "due_date"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status      = db.Column(
        db.String(20), nullable=False,
        default=FIGURINO_PROD_SOLICITADO, server_default=FIGURINO_PROD_SOLICITADO,
    )
    quantity    = db.Column(db.Integer, nullable=False, default=1, server_default="1")

    # `producao` cria o que não existe; `manutencao` mexe no que já existe (feature 225b) —
    # conserto de defeito relatado no evento, ajuste para uma data, adaptação. Boa parte da
    # manutenção não tem compra nenhuma: é trabalho manual que hoje se combina por voz e some.
    kind = db.Column(
        db.String(20), nullable=False,
        default=FIGURINO_KIND_PRODUCAO, server_default=FIGURINO_KIND_PRODUCAO,
    )
    # Só faz sentido em `manutencao`: a peça pode ir para o próximo evento assim, ou não pode?
    # É a única informação da manutenção que muda uma decisão — a de escalar ou não aquele boneco.
    severity = db.Column(db.String(20), nullable=True)

    # SET NULL, não CASCADE: excluir o evento não pode apagar o pedido — o trabalho existiu e o
    # dinheiro saiu. Mesma regra que a feature 224 teve que aplicar a `special_expenses.event_id`
    # (lá o NO ACTION original quebrava a exclusão do evento com violação de chave estrangeira).
    event_id = db.Column(
        db.Integer, db.ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True
    )
    figurino_sheet_id = db.Column(
        db.Integer, db.ForeignKey("figurino_sheets.id", ondelete="SET NULL"), nullable=True
    )

    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    responsible_id  = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_id  = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at     = db.Column(db.DateTime, nullable=True)

    due_date       = db.Column(db.Date, nullable=True)
    estimated_cost = db.Column(db.Numeric(10, 2), nullable=True)

    done_at             = db.Column(db.DateTime, nullable=True)
    cancelled_at        = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)

    # Compromisso criado na agenda da empresa com a pessoa responsável como convidada (FR-022).
    # Guardado para poder mover (mudou o prazo), reconvidar (mudou o responsável) e apagar
    # (pedido pronto ou cancelado) sem depender de busca por título.
    google_event_id = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    event          = db.relationship("CalendarEvent", lazy="joined", foreign_keys=[event_id])
    figurino_sheet = db.relationship("FigurinoSheet", lazy="joined")
    requested_by   = db.relationship("User", lazy="joined", foreign_keys=[requested_by_id])
    responsible    = db.relationship("User", lazy="joined", foreign_keys=[responsible_id])
    approved_by    = db.relationship("User", lazy=True, foreign_keys=[approved_by_id])

    anexos = db.relationship(
        "FigurinoProducaoAnexo", back_populates="producao",
        cascade="all, delete-orphan", order_by="FigurinoProducaoAnexo.created_at",
    )
    logs = db.relationship(
        "FigurinoProducaoLog", back_populates="producao",
        cascade="all, delete-orphan", order_by="FigurinoProducaoLog.created_at.desc()",
    )

    @property
    def is_open(self) -> bool:
        """True enquanto o pedido ainda dá trabalho a alguém."""
        return self.status in FIGURINO_PROD_ABERTOS

    @property
    def is_manutencao(self) -> bool:
        return self.kind == FIGURINO_KIND_MANUTENCAO

    @property
    def is_compra(self) -> bool:
        """True quando o pedido é de compra (feature 225c) — ninguém produz, alguém compra."""
        return self.kind == FIGURINO_KIND_COMPRA

    @property
    def impede_uso(self) -> bool:
        """True quando a peça **não pode** ir para um evento até isto ser resolvido.

        É o que alimenta o aviso na ficha e no elenco do evento: sem ele, o defeito relatado numa
        festa vira uma conversa que ninguém lembra na hora de separar o figurino da próxima.
        """
        return (
            self.is_open
            and self.is_manutencao
            and self.severity == FIGURINO_SEV_IMPEDE
        )

    @property
    def prazo_efetivo(self):
        """Prazo do pedido, caindo na data do evento quando ninguém informou um (FR-004)."""
        if self.due_date:
            return self.due_date
        if self.event and self.event.start_at:
            return self.event.start_at.date()
        return None

    @property
    def dias_para_prazo(self) -> int | None:
        """Dias até o prazo (negativo se venceu); None quando não há prazo."""
        prazo = self.prazo_efetivo
        if not prazo:
            return None
        return (prazo - now_sp().date()).days

    @property
    def is_late(self) -> bool:
        """True quando o prazo já passou e o pedido continua aberto."""
        dias = self.dias_para_prazo
        return self.is_open and dias is not None and dias < 0

    @property
    def total_gasto(self):
        """Soma dos gastos extras **aprovados** vinculados ao pedido.

        Só aprovados: é o mesmo recorte da DRE e da planilha de pagamentos, e um pedido não pode
        exibir um total que o financeiro ainda não reconheceu.
        """
        from decimal import Decimal

        return sum(
            (g.amount or Decimal("0")) for g in self.gastos if g.status == "aprovado"
        ) or Decimal("0")


class FigurinoProducaoAnexo(db.Model):
    """Foto de evolução ou orçamento de fornecedor anexado a um pedido (feature 225).

    Uma tabela só, com ``kind`` discriminando, porque a forma do dado é a mesma (arquivo + nome
    original + quem subiu). ``supplier_name``/``amount`` só fazem sentido em ``kind="orcamento"``,
    e existem para o que o cliente pediu: colocar as propostas lado a lado antes de decidir.
    """

    __tablename__ = "figurino_producao_anexos"
    __table_args__ = (
        db.Index("ix_figurino_producao_anexos_producao_id", "producao_id"),
    )

    id         = db.Column(db.Integer, primary_key=True)
    producao_id = db.Column(
        db.Integer, db.ForeignKey("figurino_producoes.id", ondelete="CASCADE"), nullable=False
    )
    kind          = db.Column(db.String(20), nullable=False, default=FIGURINO_ANEXO_FOTO)
    file_path     = db.Column(db.String(500), nullable=False)
    original_name = db.Column(db.String(255), nullable=True)
    caption       = db.Column(db.String(300), nullable=True)

    # Só para kind="orcamento".
    supplier_name = db.Column(db.String(200), nullable=True)
    amount        = db.Column(db.Numeric(10, 2), nullable=True)

    uploaded_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    producao    = db.relationship("FigurinoProducao", back_populates="anexos")
    uploaded_by = db.relationship("User", lazy="joined", foreign_keys=[uploaded_by_id])


class FigurinoProducaoLog(db.Model):
    """Uma linha do histórico de evolução de um pedido de produção (feature 225).

    Mesma forma de ``EventLog`` (autor + papel + texto), porque é a mesma coisa: a narrativa que
    alguém lê depois para entender o que aconteceu. A diferença é ``photo_path`` — aqui a foto faz
    parte do relato ("ficou assim hoje"), que é exatamente o "mini histórico de evolução" pedido.
    ``status_from``/``status_to`` ficam preenchidos quando a linha nasceu de uma mudança de estado.
    """

    __tablename__ = "figurino_producao_logs"
    __table_args__ = (
        db.Index("ix_figurino_producao_logs_producao_id", "producao_id"),
    )

    id          = db.Column(db.Integer, primary_key=True)
    producao_id = db.Column(
        db.Integer, db.ForeignKey("figurino_producoes.id", ondelete="CASCADE"), nullable=False
    )
    actor_name  = db.Column(db.String(120), nullable=False, default="Sistema")
    actor_role  = db.Column(db.String(120), nullable=True)
    message     = db.Column(db.Text, nullable=False)
    photo_path  = db.Column(db.String(500), nullable=True)
    status_from = db.Column(db.String(20), nullable=True)
    status_to   = db.Column(db.String(20), nullable=True)
    created_at  = db.Column(db.DateTime, default=now_sp, nullable=False)

    producao = db.relationship("FigurinoProducao", back_populates="logs")

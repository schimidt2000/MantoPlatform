"""Núcleo de negócio de conta do Portal do Artista (feature 191).

Fluxos de credencial e aceite de termos: primeiro acesso, troca de senha obrigatória, "esqueci
minha senha", redefinição por token e aceite dos termos de uso. Extraído de
`app/talent_portal/routes.py` para virar fonte única (Princípio I) reusada pela view Jinja
legada e pelos endpoints `app/api/portal_auth.py`.

Funções puras no mesmo sentido dos demais `*_ops`: não importam `flask.request`/
`render_template`/`flash`/`session`. O disparo de e-mail é feito por callback injetado pela
camada de rota (`send_async`), porque montar a URL de reset depende de `url_for`/`request`.
"""

from __future__ import annotations

import logging
import re
import secrets
import string
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from app import db
from app.models import Talent
from app.talent_portal.portal_ops import find_talent_by_login

log = logging.getLogger(__name__)

#: Duração da validade de um token de redefinição de senha pedido pela própria pessoa.
RESET_TOKEN_TTL = timedelta(hours=1)

#: Validade do link mandado num disparo em lote (feature 293). Uma hora é o certo para quem
#: acabou de clicar em "esqueci minha senha" e está olhando a caixa de entrada; num e-mail que sai
#: para dezenas de pessoas ao mesmo tempo, é a garantia de que quem abrir à tarde recebe "link
#: inválido". Foi exatamente assim que a campanha de 28/08/2026 terminou sem nenhuma resposta.
#: O token continua de uso único e é sobrescrito a cada emissão nova.
CAMPANHA_RESET_TTL = timedelta(days=7)

#: Fuso de exibição. O token vive em UTC; quem lê a tela vive em São Paulo.
_TZ_SP = ZoneInfo("America/Sao_Paulo")

#: Comprimento da senha temporária gerada no primeiro acesso.
TEMP_PASSWORD_LENGTH = 10

#: Regras de força de senha, na ordem em que são reportadas ao usuário.
PASSWORD_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r".{8,}"), "A senha deve ter pelo menos 8 caracteres."),
    (re.compile(r"[A-Z]"), "A senha deve ter pelo menos 1 letra maiúscula."),
    (re.compile(r"[a-z]"), "A senha deve ter pelo menos 1 letra minúscula."),
    (re.compile(r"[0-9]"), "A senha deve ter pelo menos 1 número."),
    (re.compile(r"[^A-Za-z0-9]"), "A senha deve ter pelo menos 1 símbolo (ex.: @, #, !, %)."),
]


class PortalAccountError(Exception):
    """Erro de validação num fluxo de conta (senha fraca, CPF inexistente, token expirado…)."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class FirstAccessResult(NamedTuple):
    """Resultado de um primeiro acesso bem-sucedido."""

    email_hint: str
    """E-mail mascarado (ex.: `jo***@dominio.com`) para o talento confirmar o destino."""


def validate_password_strength(password: str) -> str | None:
    """Primeira regra de força violada pela senha, ou `None` se a senha é aceitável.

    Args:
        password: Senha em texto puro digitada pelo talento.

    Returns:
        Mensagem de erro amigável em pt-BR, ou `None` quando a senha passa em todas as regras.
    """
    for pattern, message in PASSWORD_RULES:
        if not pattern.search(password or ""):
            return message
    return None


def _require_valid_new_password(new_password: str, confirm_password: str) -> None:
    """Valida força e confirmação de uma senha nova.

    Raises:
        PortalAccountError: Senha fraca ou confirmação divergente.
    """
    error = validate_password_strength(new_password)
    if error:
        raise PortalAccountError(error, field="new_password")
    if new_password != confirm_password:
        raise PortalAccountError("As senhas não coincidem.", field="confirm_password")


def mask_email(email: str) -> str:
    """Mascara um e-mail para exibição (`joao@x.com` → `jo***@x.com`)."""
    parts = (email or "").split("@")
    if len(parts) != 2:
        return "***"
    return f"{parts[0][:2]}***@{parts[1]}"


def generate_temp_password() -> str:
    """Gera uma senha temporária alfanumérica para o e-mail de boas-vindas."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(TEMP_PASSWORD_LENGTH))


def start_first_access(login_value: str, send_welcome: Callable[[Talent, str], None]) -> FirstAccessResult:
    """Gera senha temporária para um talento que ainda não tem senha e dispara o e-mail.

    Args:
        login_value: CPF (dígitos) ou e-mail digitado pelo talento.
        send_welcome: Callback que recebe `(talent, senha_temporária)` e dispara o e-mail de
            boas-vindas. Injetado pela rota para manter este módulo livre de `flask.request`.

    Returns:
        `FirstAccessResult` com o e-mail mascarado de destino.

    Raises:
        PortalAccountError: Talento não encontrado, já com senha definida, ou sem e-mail.
    """
    talent = find_talent_by_login(login_value)
    if talent is None:
        raise PortalAccountError(
            "CPF/e-mail não encontrado. Verifique se você está cadastrado ou fale com nossa equipe.",
            field="login",
        )
    if talent.password_hash:
        raise PortalAccountError(
            "Este CPF já possui senha. Use a opção 'Esqueci minha senha' para recuperar o acesso.",
            field="login",
        )
    if not talent.email_contact:
        raise PortalAccountError(
            "Seu e-mail não está cadastrado. Entre em contato com nossa equipe de casting.",
            field="login",
        )

    temp_password = generate_temp_password()
    email_hint = mask_email(talent.email_contact)
    talent.set_password(temp_password)
    talent.must_change_password = True
    db.session.commit()

    send_welcome(talent, temp_password)
    return FirstAccessResult(email_hint=email_hint)


def request_password_reset(
    login_value: str,
    email: str,
    send_reset: Callable[[Talent, str], None],
    build_reset_url: Callable[[str], str],
) -> None:
    """Emite um token de redefinição e dispara o e-mail, se CPF e e-mail baterem.

    Cobre também talentos que nunca definiram senha (`password_hash` NULL): não exigimos
    senha prévia na condição de match, porque `reset_password_with_token` já define a senha
    e zera `must_change_password` — na prática esse link também serve como "definir a primeira
    senha". Antes dessa mudança, quem nunca passou pelo Primeiro Acesso clicava em "Esqueci
    minha senha" e caía num retorno silencioso, sem receber e-mail nenhum (caso real: talento
    139, e outros 118 talentos ativos sem senha no mesmo buraco). Primeiro Acesso continua
    existindo como caminho paralelo (lá a senha temporária vai no e-mail de boas-vindas; aqui
    o talento define a senha pelo link com token).

    Silencioso por design (enumeração de conta): nunca sinaliza ao chamador se o talento existe
    — a rota sempre responde "se os dados conferem, enviamos o link". Qualquer falha é logada e
    engolida, para que um erro de SMTP não vire 500 nem revele o estado da conta.

    Args:
        login_value: CPF (dígitos) ou e-mail digitado.
        email: E-mail que o talento afirma ser o dele — precisa bater com `email_contact`.
        send_reset: Callback `(talent, reset_url)` que dispara o e-mail.
        build_reset_url: Callback que recebe o token e devolve a URL absoluta de redefinição.
    """
    try:
        talent = find_talent_by_login(login_value)
        matches = (
            talent is not None
            and talent.email_contact
            and talent.email_contact.strip().lower() == (email or "").strip().lower()
        )
        if not matches:
            return

        token = emitir_token_de_reset(talent)
        db.session.commit()
        send_reset(talent, build_reset_url(token))
    except Exception:
        log.exception("Erro ao solicitar redefinição de senha do portal")
        db.session.rollback()


def expiracao_para_exibir(talent: Talent) -> str | None:
    """Validade do link como horário de parede de São Paulo, para mostrar a uma pessoa.

    `password_reset_expires` é UTC ingênuo (`datetime.utcnow()`), e a comparação que decide se o
    token vale continua em UTC. Só a exibição converte: sem isto, a tela dizia "vale até 00:01"
    para um link que expira às 21:01 — a mesma armadilha de fuso que a plataforma já pagou na
    agenda (`app/calendar/service.py`).
    """
    if not talent.password_reset_expires:
        return None
    return (
        talent.password_reset_expires.replace(tzinfo=UTC)
        .astimezone(_TZ_SP)
        .replace(tzinfo=None)
        .isoformat()
    )


def emitir_token_de_reset(talent: Talent, ttl: timedelta = RESET_TOKEN_TTL) -> str:
    """Grava um token novo de redefinição no talento e devolve o token (sem commit).

    Fonte única do token: o pedido do próprio artista ("Esqueci minha senha"), o envio feito pelo
    casting (feature 274) e o disparo em lote (feature 293) só divergem em **quem tem direito de
    pedir** e em **quanto tempo o link vale**, nunca no que é gravado. Trocar o token invalida o
    anterior, então um segundo pedido não deixa dois links vivos.

    Args:
        talent: Dono da conta.
        ttl: Validade do link. O default preserva a hora do autoatendimento; a campanha passa
            `CAMPANHA_RESET_TTL` porque um lote não é lido no minuto seguinte.
    """
    token = secrets.token_urlsafe(32)
    talent.password_reset_token = token
    talent.password_reset_expires = datetime.utcnow() + ttl
    return token


def enviar_reset_pelo_staff(
    talent: Talent,
    send_reset: Callable[[Talent, str], None],
    build_reset_url: Callable[[str], str],
    ttl: timedelta = RESET_TOKEN_TTL,
) -> dict:
    """Manda o link de redefinição para o e-mail cadastrado, a pedido de quem atende o artista.

    Existe porque o autoatendimento tem dois becos sem saída que só uma pessoa de dentro
    desfaz (feature 274): "Esqueci minha senha" exige digitar **exatamente** o e-mail que está no
    cadastro e, quando não bate, não faz nada e não avisa (é assim de propósito, para não revelar
    quem é cadastrado); e "Primeiro Acesso" recusa quem já tem senha. Um artista que erra a
    grafia do próprio e-mail cadastrado — ou que não lembra qual usou — fica preso, e não havia
    ferramenta nenhuma do lado do casting.

    Diferente do fluxo público, aqui **não** se exige que o e-mail seja digitado de novo (quem
    chama já está vendo a ficha) e o erro **é** devolvido: quem atende precisa saber que faltou
    e-mail no cadastro.

    Args:
        talent: Talento dono da conta.
        send_reset: Callback `(talent, reset_url)` que dispara o e-mail.
        build_reset_url: Callback que recebe o token e devolve a URL absoluta.

    Returns:
        `{"email": ..., "expira_em": ISO, "tinha_senha": bool}` — o e-mail volta inteiro de
        propósito: é lendo o endereço em voz alta que se descobre o erro de digitação do cadastro.

    Raises:
        PortalAccountError: Talento sem e-mail cadastrado.
    """
    if not (talent.email_contact or "").strip():
        raise PortalAccountError(
            "Este talento não tem e-mail no cadastro. Preencha o e-mail antes de enviar o link.",
            field="email_contact",
        )
    tinha_senha = bool(talent.password_hash)
    token = emitir_token_de_reset(talent, ttl)
    db.session.commit()
    send_reset(talent, build_reset_url(token))
    return {
        "email": talent.email_contact,
        "expira_em": expiracao_para_exibir(talent),
        "tinha_senha": tinha_senha,
    }


def find_talent_by_reset_token(token: str) -> Talent | None:
    """Talento dono de um token de redefinição ainda válido, ou `None` se inválido/expirado."""
    if not token:
        return None
    talent = Talent.query.filter_by(password_reset_token=token).first()
    if talent is None:
        return None
    expires = talent.password_reset_expires
    if expires is None or expires < datetime.utcnow():
        return None
    return talent


def reset_password_with_token(token: str, new_password: str, confirm_password: str) -> Talent:
    """Redefine a senha a partir de um token válido e invalida o token.

    Args:
        token: Token recebido por e-mail.
        new_password: Senha nova em texto puro.
        confirm_password: Repetição da senha nova.

    Returns:
        O talento com a senha já redefinida.

    Raises:
        PortalAccountError: Token inválido/expirado, senha fraca ou confirmação divergente.
    """
    talent = find_talent_by_reset_token(token)
    if talent is None:
        raise PortalAccountError(
            "Este link de redefinição é inválido ou expirou. Solicite um novo.", field="token"
        )
    _require_valid_new_password(new_password, confirm_password)

    talent.set_password(new_password)
    talent.must_change_password = False
    talent.password_reset_token = None
    talent.password_reset_expires = None
    db.session.commit()
    return talent


def change_password(talent: Talent, new_password: str, confirm_password: str) -> Talent:
    """Troca a senha do talento logado e limpa a exigência de troca obrigatória.

    Args:
        talent: Talento autenticado.
        new_password: Senha nova em texto puro.
        confirm_password: Repetição da senha nova.

    Returns:
        O talento atualizado.

    Raises:
        PortalAccountError: Senha fraca ou confirmação divergente.
    """
    _require_valid_new_password(new_password, confirm_password)
    talent.set_password(new_password)
    talent.must_change_password = False
    db.session.commit()
    return talent


def accept_terms(talent: Talent) -> Talent:
    """Registra o aceite dos termos de uso — idempotente (não sobrescreve um aceite anterior)."""
    if talent.terms_accepted_at is None:
        talent.terms_accepted_at = datetime.utcnow()
        db.session.commit()
    return talent


def pending_account_steps(talent: Talent) -> list[str]:
    """Etapas de conta que o talento ainda precisa concluir antes de usar o portal.

    Returns:
        Lista com `"change_password"` e/ou `"accept_terms"`, na ordem em que devem ser feitas.
        Vazia quando a conta está em dia.
    """
    steps: list[str] = []
    if talent.must_change_password:
        steps.append("change_password")
    if not talent.terms_accepted_at:
        steps.append("accept_terms")
    return steps

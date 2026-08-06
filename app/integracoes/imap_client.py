"""Leitura IMAP da caixa do remetente, só para colher devoluções (feature 219).

Camada de I/O pura: conecta, busca e devolve os bytes das mensagens. Quem interpreta é
`app/talents/bounce_ops.py` — separados de propósito, para o parser ser testável sem rede.

Reaproveita a credencial que o envio já usa (`MAIL_USERNAME` + `MAIL_PASSWORD`, a App Password do
Workspace). Nenhum escopo OAuth novo, nenhuma credencial nova.

**Nunca escreve na caixa**: abre a pasta com ``EXAMINE`` (somente leitura) e busca com
``BODY.PEEK[]``, então nada é marcado como lido, movido ou apagado.
"""

from __future__ import annotations

import imaplib
import logging
from datetime import date, timedelta

log = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_TIMEOUT = 30

# Remetentes de aviso de devolução. O Gmail usa `mailer-daemon@googlemail.com`; `postmaster`
# cobre servidores intermediários que respondam em nome do domínio de destino.
BOUNCE_SENDERS = ("mailer-daemon", "postmaster")


class ImapUnavailableError(RuntimeError):
    """Não foi possível ler a caixa (credencial recusada, IMAP desligado, rede fora)."""


def _all_mail_folder(box: imaplib.IMAP4_SSL) -> str:
    """Nome da pasta "Todos os e-mails" nesta conta, ou ``INBOX``.

    O nome é traduzido ("[Gmail]/Todos os e-mails" vs "[Gmail]/All Mail"), então é resolvido pela
    flag de uso especial ``\\All`` do LIST em vez de chutar o texto.
    """
    try:
        status, folders = box.list()
        if status == "OK":
            for raw in folders or []:
                line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
                if "\\All" in line:
                    return '"' + line.split(' "/" ')[-1].strip().strip('"') + '"'
    except imaplib.IMAP4.error as exc:
        log.debug("[email-bounce] LIST falhou, caindo para INBOX: %s", exc)
    return "INBOX"


def fetch_bounce_messages(
    username: str, password: str, lookback_days: int = 90, limit: int = 300
) -> list[bytes]:
    """Baixa as mensagens de devolução recentes da caixa do remetente.

    Args:
        username: Conta que envia os emails da plataforma (`MAIL_USERNAME`).
        password: App Password do Workspace (`MAIL_PASSWORD`); espaços são ignorados.
        lookback_days: Janela de busca. Reprocessar é inofensivo — `message_id` é único.
        limit: Teto de mensagens por varredura, para uma caixa antiga não travar o ciclo.

    Returns:
        Os bytes brutos de cada devolução encontrada (as mais recentes primeiro).

    Raises:
        ImapUnavailableError: Login recusado ou IMAP indisponível.
    """
    clean_password = (password or "").replace(" ", "")
    if not username or not clean_password:
        raise ImapUnavailableError("MAIL_USERNAME/MAIL_PASSWORD não configurados.")

    try:
        box = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=IMAP_TIMEOUT)
    except OSError as exc:
        raise ImapUnavailableError(f"conexão IMAP falhou: {exc}") from exc

    try:
        try:
            box.login(username, clean_password)
        except imaplib.IMAP4.error as exc:
            raise ImapUnavailableError(f"login IMAP recusado: {exc}") from exc

        folder = _all_mail_folder(box)
        status, _ = box.select(folder, readonly=True)  # readonly → EXAMINE
        if status != "OK":
            status, _ = box.select("INBOX", readonly=True)
            if status != "OK":
                raise ImapUnavailableError("nenhuma pasta legível na conta.")

        since = (date.today() - timedelta(days=max(1, lookback_days))).strftime("%d-%b-%Y")
        ids: list[bytes] = []
        for sender in BOUNCE_SENDERS:
            status, data = box.search(None, "FROM", sender, "SINCE", since)
            if status == "OK" and data and data[0]:
                ids.extend(data[0].split())

        # As mais recentes primeiro; `limit` evita varrer uma caixa de anos num ciclo só.
        unique_ids = list(dict.fromkeys(reversed(ids)))[:limit]
        if len(ids) > limit:
            log.info(
                "[email-bounce] %d devoluções na janela, lendo as %d mais recentes",
                len(ids), limit,
            )

        messages: list[bytes] = []
        for message_id in unique_ids:
            status, raw = box.fetch(message_id, "(BODY.PEEK[])")  # PEEK → não marca como lida
            if status == "OK" and raw and isinstance(raw[0], tuple):
                messages.append(raw[0][1])
        return messages
    finally:
        try:
            box.logout()
        except (imaplib.IMAP4.error, OSError):
            pass

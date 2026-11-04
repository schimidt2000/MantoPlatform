"""A ficha da cliente na conversa (feature 333): ligar, trocar, remover e criar, e a ficha do envio.

A ligação automática pelo telefone é da 325 (`aviso_ops._vincular_cliente`) e usa a regra daqui,
``ficha_pelo_telefone``. Escolha feita à mão (inclusive "Remover vínculo") marca ``ficha_manual``, e a
automática não mexe mais na conversa: sem a marca, a próxima mensagem religaria a ficha errada.

A ficha nova sai da base de clientes (`client_ops.quick_create_client`, que reaproveita a do mesmo
telefone), com a origem ``conversa``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError

from app import db
from app.clientes import client_ops
from app.clientes.importer import normalize_phone
from app.conversas import constantes as K
from app.conversas.leitura_ops import telefone_legivel
from app.conversas.recusa import Recusa, campo
from app.conversas.telefone import so_digitos, variantes_de_telefone
from app.models import Client, Conversa

# Os campos do `ClientValidationError` da base de clientes, com os nomes desta API.
_CAMPO_DA_BASE = {"name": "nome", "phone": "telefone"}


@dataclass(frozen=True)
class Ligacao:
    """A conversa depois de ligada e se a ficha "nova" já existia pelo telefone."""

    conversa: Conversa
    reaproveitada: bool


def ficha_pelo_telefone(telefone: str | None) -> Client | None:
    """A ficha do telefone, com e sem o nono dígito (regra da 325, FR-005).

    Com duas fichas (uma gravada com o 9 e outra sem), vale a do telefone exato; sem ela, nenhuma —
    escolher "a primeira" ligaria a conversa à cliente errada.
    """
    if not telefone:
        return None
    candidatos = Client.query.filter(Client.phone.in_(variantes_de_telefone(telefone))).all()
    if len(candidatos) == 1:
        return candidatos[0]
    exatos = [c for c in candidatos if c.phone == telefone]
    return exatos[0] if len(exatos) == 1 else None


def _conversa_ou_404(conversa_id: int) -> Conversa:
    conversa = db.session.get(Conversa, conversa_id)
    if conversa is None:
        raise Recusa("nao_encontrada", K.TEXTO_CONVERSA_NAO_ENCONTRADA, 404)
    return conversa


def _ficha_existente(client_id: Any) -> Client:
    valido = isinstance(client_id, int) and not isinstance(client_id, bool)
    ficha = db.session.get(Client, client_id) if valido else None
    if ficha is None:
        raise campo("cliente", K.TEXTO_FICHA_NAO_ENCONTRADA)
    return ficha


def _nova_ou_existente(nome: Any, telefone: Any, *, e164: bool = False) -> tuple[Client, bool]:
    """A ficha do telefone, se já existe; senão, uma nova com origem ``conversa``.

    ``e164``: o telefone é o wa_id do WhatsApp, já com o país — vai como veio. O digitado passa pela
    normalização da base de clientes (DDD sem país vira Brasil).
    """
    texto = telefone if isinstance(telefone, str) else ""
    digitos = so_digitos(texto) if e164 else normalize_phone(texto)
    existente = ficha_pelo_telefone(digitos)
    if existente is not None:
        return existente, True
    try:
        ficha, reaproveitada = client_ops.quick_create_client(
            nome if isinstance(nome, str) else "",
            texto,
            phone_display=telefone_legivel(digitos) if digitos else None,
            source=K.ORIGEM_DA_FICHA,
            phone_digits=digitos if e164 else None,
        )
    except client_ops.ClientValidationError as exc:
        raise campo(_CAMPO_DA_BASE.get(exc.field, exc.field), exc.message) from exc
    except IntegrityError:
        # Dois envios ao mesmo tempo criando a mesma ficha: quem perdeu usa a do vencedor.
        db.session.rollback()
        ficha = ficha_pelo_telefone(digitos)
        if ficha is None:
            raise
        return ficha, True
    return ficha, reaproveitada


def _ficha_dos_dados(dados: dict[str, Any]) -> tuple[Client, bool]:
    """``{"client_id"}`` (ou ``{"id"}``) liga a uma ficha existente; ``{"nome", "telefone"}`` cria."""
    if "client_id" in dados or "id" in dados:
        return _ficha_existente(dados.get("client_id", dados.get("id"))), False
    if "nome" in dados or "telefone" in dados:
        return _nova_ou_existente(dados.get("nome"), dados.get("telefone"))
    raise campo("cliente", K.TEXTO_ESCOLHA_A_FICHA)


def ligar(conversa_id: int, dados: Any) -> Ligacao:
    """Liga a conversa a uma ficha existente ou nova, à mão (FR-009). Comita.

    Raises:
        Recusa: 404 (conversa); 422 em ``cliente``, ``nome`` ou ``telefone``.
    """
    conversa = _conversa_ou_404(conversa_id)
    ficha, reaproveitada = _ficha_dos_dados(dados if isinstance(dados, dict) else {})
    conversa.client_id = ficha.id
    conversa.ficha_manual = True
    db.session.commit()
    return Ligacao(conversa, reaproveitada)


def remover(conversa_id: int) -> Conversa:
    """Remove o vínculo sem apagar a ficha. A automática não religa depois (FR-009). Comita."""
    conversa = _conversa_ou_404(conversa_id)
    conversa.client_id = None
    conversa.ficha_manual = True
    db.session.commit()
    return conversa


def ficha_para_envio(conversa: Conversa, cliente: Any, nome_do_orcamento: str | None) -> Client:
    """A ficha do envio do orçamento (research R3). Comita a ligação.

    - Conversa com ficha: ela.
    - ``cliente`` no pedido: liga ou cria (escolha do vendedor, então manual).
    - WhatsApp sem ficha e sem escolha manual anterior: a do telefone, ou uma nova com o nome do
      orçamento (sem ele, o do perfil; sem os dois, o telefone).
    - O resto (Instagram, ou ficha removida à mão): a recusa pede a ficha.

    Raises:
        Recusa: 422 em ``cliente``, ``nome`` ou ``telefone``.
    """
    if conversa.cliente is not None:
        return conversa.cliente
    if isinstance(cliente, dict) and cliente:
        ficha, _ = _ficha_dos_dados(cliente)
        conversa.ficha_manual = True
    elif conversa.canal == K.CANAL_WHATSAPP and conversa.telefone and not conversa.ficha_manual:
        ficha = ficha_pelo_telefone(conversa.telefone)
        if ficha is None:
            nome = (
                (nome_do_orcamento or "").strip()
                or (conversa.nome_perfil or "").strip()
                or telefone_legivel(conversa.telefone)
                or conversa.telefone
            )
            ficha, _ = _nova_ou_existente(nome, conversa.telefone, e164=True)
    else:
        raise campo("cliente", K.TEXTO_ESCOLHA_A_FICHA)
    conversa.client_id = ficha.id
    db.session.commit()
    return ficha

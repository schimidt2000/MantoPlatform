"""Leitura das conversas: lista, conversa aberta e serialização (feature 325, FR-013/FR-014).

Horários saem com ``+00:00`` explícito (``_iso_utc``): as colunas destas tabelas são UTC naive, e
um ISO sem fuso seria lido no navegador como hora local (armadilha 1 do `docs/00` §6).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app import db
from app.conversas import constantes as K
from app.conversas.acesso import responsavel_ativo
from app.conversas.relogio import agora_utc
from app.conversas.telefone import so_digitos
from app.models import Client, Conversa, ConversaMensagem, ConversaNota

BUSCA_MINIMA = 2


def _iso_utc(valor: datetime | None) -> str | None:
    """ISO 8601 com o fuso UTC explícito (``…+00:00``), ou ``None``."""
    if valor is None:
        return None
    return valor.replace(tzinfo=UTC).isoformat()


def _de_iso(valor: str | None) -> datetime | None:
    """Lê o cursor ISO da API de volta para UTC naive (ilegível → sem cursor)."""
    if not valor:
        return None
    try:
        lido = datetime.fromisoformat(valor)
    except ValueError:
        return None
    if lido.tzinfo is not None:
        lido = lido.astimezone(UTC).replace(tzinfo=None)
    return lido


def telefone_legivel(digitos: str | None) -> str | None:
    """``5511987654321`` → ``(11) 98765-4321``; fora do padrão brasileiro, devolve como veio."""
    numero = so_digitos(digitos)
    if numero.startswith("55") and len(numero) in (12, 13):
        local = numero[4:]
        return f"({numero[2:4]}) {local[:-4]}-{local[-4:]}"
    return digitos


def janela_aberta(conversa: Conversa) -> bool:
    """A janela de 24 h está aberta? Só a mensagem da cliente a reabre (research R9)."""
    recebida = conversa.ultima_recebida_em
    return recebida is not None and agora_utc() - recebida < K.JANELA


def nome_da_conversa(conversa: Conversa) -> str:
    """Nome da ficha › nome de perfil do WhatsApp › telefone formatado."""
    if conversa.cliente is not None:
        return conversa.cliente.name
    return conversa.nome_perfil or telefone_legivel(conversa.telefone) or conversa.contato_id


def _cliente(conversa: Conversa) -> dict[str, Any] | None:
    if conversa.cliente is None:
        return None
    return {"id": conversa.cliente.id, "nome": conversa.cliente.name}


def serializar_pessoa(user: Any) -> dict[str, Any] | None:
    """Quem atende, escreveu a nota ou está na equipe: ``{id, nome}``."""
    return {"id": user.id, "nome": user.name} if user is not None else None


def serializar_nota(nota: ConversaNota) -> dict[str, Any]:
    """Nota interna (feature 328): nunca sai para a cliente."""
    return {
        "id": nota.id,
        "texto": nota.texto,
        "autor": serializar_pessoa(nota.autor),
        "momento": _iso_utc(nota.created_at),
    }


def serializar_conversa(conversa: Conversa) -> dict[str, Any]:
    """O cartão da conversa (lista e cabeçalho da conversa aberta).

    ``responsavel_ativo`` falso = o responsável perdeu o papel ou o acesso: a tela mostra o nome e
    oferece "Assumir" a qualquer um (feature 328, FR-003).
    """
    fecha_em = conversa.ultima_recebida_em + K.JANELA if conversa.ultima_recebida_em else None
    return {
        "id": conversa.id,
        "canal": conversa.canal,
        "nome": nome_da_conversa(conversa),
        "nome_perfil": conversa.nome_perfil,
        "telefone": conversa.telefone,
        "telefone_legivel": telefone_legivel(conversa.telefone),
        "cliente": _cliente(conversa),
        "ultima_previa": conversa.ultima_previa,
        "ultima_mensagem_em": _iso_utc(conversa.ultima_mensagem_em),
        "nao_lidas": conversa.nao_lidas or 0,
        "janela_aberta": janela_aberta(conversa),
        "janela_fecha_em": _iso_utc(fecha_em),
        "responsavel": serializar_pessoa(conversa.responsavel),
        "responsavel_ativo": responsavel_ativo(conversa),
        "aguardando_desde": _iso_utc(conversa.aguardando_desde),
    }


def _midia(mensagem: ConversaMensagem) -> dict[str, Any] | None:
    midia = mensagem.midia
    if midia is None:
        return None
    return {
        "id": midia.id,
        "estado": midia.estado,
        "mime": midia.mime,
        "tamanho": midia.tamanho,
        "nome": midia.nome_original,
        "url": _url_da_midia(midia) if midia.estado == K.MIDIA_GUARDADA else None,
    }


def _url_da_midia(midia: Any) -> str:
    """URL com o nome do arquivo no fim: é pela extensão que o visualizador (feature 320) sabe
    se abre imagem, PDF ou "outro". O nome não decide nada no servidor — só o id."""
    mime = (midia.mime or "").split(";")[0].strip()
    nome = midia.nome_original or f"arquivo{K.EXTENSAO_DO_MIME.get(mime, '.bin')}"
    return f"/api/conversas/midia/{midia.id}/{quote(nome)}"


def serializar_mensagem(mensagem: ConversaMensagem) -> dict[str, Any]:
    """Uma mensagem como a tela precisa (contrato em ``contracts/api.md``)."""
    autor = mensagem.autor
    erro = None
    if mensagem.situacao == K.SITUACAO_FALHOU:
        erro = {
            "codigo": mensagem.erro_codigo,
            "motivo": mensagem.erro_motivo or K.MOTIVO_INDISPONIVEL,
        }
    return {
        "id": mensagem.id,
        "direcao": mensagem.direcao,
        "tipo": mensagem.tipo,
        "texto": mensagem.texto,
        "momento": _iso_utc(mensagem.momento),
        "situacao": mensagem.situacao,
        "autor": {"id": autor.id, "nome": autor.name} if autor is not None else None,
        "origem": mensagem.origem,
        "modelo_nome": mensagem.modelo_nome,
        "erro": erro,
        "midia": _midia(mensagem),
    }


def listar_conversas(
    busca: str | None,
    antes: str | None,
    filtro: str = K.FILTRO_TODAS,
    usuario_id: int | None = None,
) -> tuple[list[Conversa], str | None]:
    """Página da lista, da última mensagem para trás. Devolve as conversas e o próximo cursor.

    ``filtro`` (feature 328): ``minhas`` = responsável é ``usuario_id``; ``sem_responsavel`` = fila.
    """
    consulta = Conversa.query.options(
        joinedload(Conversa.cliente), joinedload(Conversa.responsavel)
    ).outerjoin(Client, Client.id == Conversa.client_id)
    if filtro == K.FILTRO_MINHAS:
        consulta = consulta.filter(Conversa.responsavel_id == usuario_id)
    elif filtro == K.FILTRO_SEM_RESPONSAVEL:
        consulta = consulta.filter(Conversa.responsavel_id.is_(None))
    termo = (busca or "").strip()
    if len(termo) >= BUSCA_MINIMA:
        filtros = [Conversa.nome_perfil.ilike(f"%{termo}%"), Client.name.ilike(f"%{termo}%")]
        if digitos := so_digitos(termo):
            filtros.append(Conversa.telefone.like(f"%{digitos}%"))
        consulta = consulta.filter(or_(*filtros))
    if cursor := _de_iso(antes):
        consulta = consulta.filter(Conversa.ultima_mensagem_em < cursor)
    linhas = (
        consulta.order_by(Conversa.ultima_mensagem_em.desc().nullslast(), Conversa.id.desc())
        .limit(K.PAGINA_CONVERSAS + 1)
        .all()
    )
    proximo = None
    if len(linhas) > K.PAGINA_CONVERSAS:
        linhas = linhas[: K.PAGINA_CONVERSAS]
        proximo = _iso_utc(linhas[-1].ultima_mensagem_em)
    return linhas, proximo


def mensagens_da_conversa(
    conversa_id: int, antes_id: int | None
) -> tuple[list[ConversaMensagem], bool]:
    """As 50 mensagens mais recentes (ou anteriores a ``antes_id``), em ordem cronológica.

    O cursor é a mensagem, mas a ordem é ``(momento, id)``: um aviso atrasado grava id novo com
    momento antigo, e cortar só por ``id < antes`` abriria buraco ou repetiria mensagem.
    """
    consulta = ConversaMensagem.query.options(
        joinedload(ConversaMensagem.autor), joinedload(ConversaMensagem.midia)
    ).filter(ConversaMensagem.conversa_id == conversa_id)
    cursor = db.session.get(ConversaMensagem, antes_id) if antes_id else None
    if cursor is not None:
        consulta = consulta.filter(
            or_(
                ConversaMensagem.momento < cursor.momento,
                and_(ConversaMensagem.momento == cursor.momento, ConversaMensagem.id < cursor.id),
            )
        )
    linhas = (
        consulta.order_by(ConversaMensagem.momento.desc(), ConversaMensagem.id.desc())
        .limit(K.PAGINA_MENSAGENS + 1)
        .all()
    )
    tem_mais = len(linhas) > K.PAGINA_MENSAGENS
    return list(reversed(linhas[: K.PAGINA_MENSAGENS])), tem_mais

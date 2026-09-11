"""Formulários sem destino: a lista da Home e as ações de destino (feature 298).

Núcleo puro (sem ``flask.request``). O vínculo formulário→evento continua em
``formularios_ops.apply_event_link``; aqui fica o que é "dar destino" a um formulário que chegou
desde o corte: a leitura da Home (grupo, cor, distância em dias) e as ações de encerrar, reabrir,
repetidos e sugestão.

"Destino" = virou evento, foi encerrado com motivo, ou está na lista da Home esperando decisão.
"""

from datetime import date

from sqlalchemy.orm import joinedload

from app.constants import (
    FORM_CLOSE_REASON_LABELS,
    FORM_CLOSE_REASONS,
    FORM_COR_AMARELO_ATE_DIAS,
    FORM_COR_VERMELHO_ATE_DIAS,
    FORM_DATA_SUSPEITA_ANOS,
    now_sp,
)
from app.formularios.formularios_ops import (
    condicao_sem_destino,
    contar_por_destino,
    corte_de_chegada,
    dia_sp,
    iso_utc,
    tipo_rotulo,
)
from app.models import FormResponse


def motivos_encerramento() -> list[dict]:
    """Motivos de encerramento na ordem da tela — a lista vem do servidor, sem espelho no TS."""
    return [{"codigo": c, "rotulo": FORM_CLOSE_REASON_LABELS[c]} for c in FORM_CLOSE_REASONS]


def eh_data_suspeita(data_informada: date | None, chegada: date) -> bool:
    """Data informada antes do dia em que o formulário chegou, ou mais de 2 anos depois.

    Há formulário com 2049 no banco: a cliente erra o ano, e uma data assim não pode pintar a
    linha de urgente nem ir calada para o cadastro do evento.
    """
    if data_informada is None:
        return False
    if data_informada < chegada:
        return True
    return (data_informada - chegada).days > 365 * FORM_DATA_SUSPEITA_ANOS


def severidade(dias_ate_a_data: int | None, suspeita: bool) -> str:
    """Cor da linha: ``vermelho`` 0–7 dias, ``amarelo`` 8–30 e todo "já passou", ``cinza`` o resto.

    Sem data ou com data suspeita é ``cinza``: a cor diz urgência, e não há como saber.
    """
    if suspeita or dias_ate_a_data is None:
        return "cinza"
    if dias_ate_a_data < 0:
        return "amarelo"
    if dias_ate_a_data <= FORM_COR_VERMELHO_ATE_DIAS:
        return "vermelho"
    if dias_ate_a_data <= FORM_COR_AMARELO_ATE_DIAS:
        return "amarelo"
    return "cinza"


def _item(r: FormResponse, hoje: date) -> dict:
    return {
        "id": r.id,
        "tipo_rotulo": tipo_rotulo(r.form_type),
        "data_informada": r.event_date.isoformat() if r.event_date else None,
        "chegou_em": iso_utc(r.created_at),
        "dias_desde_chegada": (hoje - dia_sp(r.created_at)).days,
    }


def _linha(formularios: list[FormResponse], hoje: date) -> dict:
    """Uma linha da Home. ``formularios`` vem do mais recente para o mais antigo."""
    r = formularios[0]
    chegada = dia_sp(r.created_at)
    dias_ate = (r.event_date - hoje).days if r.event_date else None
    suspeita = eh_data_suspeita(r.event_date, chegada)
    return {
        "chave": f"tel:{r.contact_phone}" if r.contact_phone else f"id:{r.id}",
        "representante_id": r.id,
        "cliente": {"id": r.client.id, "nome": r.client.name} if r.client else None,
        "nome_no_formulario": r.contact_name,
        "tipo": r.form_type,
        "tipo_rotulo": tipo_rotulo(r.form_type),
        "data_informada": r.event_date.isoformat() if r.event_date else None,
        "dias_ate_a_data": dias_ate,
        "dias_desde_chegada": (hoje - chegada).days,
        # Sem data informada fica em "ainda vai chegar": não passou, e a linha pede a mesma ação.
        "grupo": "ja_passou" if dias_ate is not None and dias_ate < 0 else "a_chegar",
        "severidade": severidade(dias_ate, suspeita),
        "data_suspeita": suspeita,
        "repetido": len(formularios) > 1,
        "outro_com_evento": False,
        "formularios": [_item(f, hoje) for f in formularios],
        "sugestao": None,
    }


def _ordenar(linhas: list[dict], *, mais_proxima_primeiro: bool) -> list[dict]:
    """Ordena pela data informada; empate → o que chegou por último primeiro.

    Duas passadas estáveis: primeiro pela chegada (mais recente em cima), depois pela data. Linha
    sem data vai para o fim do grupo.
    """
    linhas = sorted(linhas, key=lambda x: x["formularios"][0]["chegou_em"] or "", reverse=True)
    com_data = [x for x in linhas if x["data_informada"]]
    sem_data = [x for x in linhas if not x["data_informada"]]
    com_data.sort(key=lambda x: x["data_informada"], reverse=not mais_proxima_primeiro)
    return com_data + sem_data


def listar_sem_destino(hoje_sp: date | None = None) -> dict:
    """Bloco ``formularios`` da Home: contagens, motivos e os dois grupos de linhas.

    O "hoje" é o de São Paulo (``now_sp``), nunca ``date.today()``: produção roda em UTC, e das
    21h à meia-noite de Brasília a festa de amanhã viraria "hoje".
    """
    corte = corte_de_chegada()
    hoje = hoje_sp or now_sp().date()
    formularios = (
        FormResponse.query.options(joinedload(FormResponse.client))
        .filter(condicao_sem_destino(corte))
        .order_by(FormResponse.created_at.desc())
        .all()
    )
    linhas = [_linha([f], hoje) for f in formularios]
    return {
        "contagens": contar_por_destino(corte),
        "motivos_encerramento": motivos_encerramento(),
        "a_chegar": _ordenar(
            [x for x in linhas if x["grupo"] == "a_chegar"], mais_proxima_primeiro=True
        ),
        "ja_passou": _ordenar(
            [x for x in linhas if x["grupo"] == "ja_passou"], mais_proxima_primeiro=False
        ),
    }

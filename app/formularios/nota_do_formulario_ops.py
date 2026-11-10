"""Do formulário da cliente para os dados da nota da venda (feature 342).

A cliente marca "Preciso de nota fiscal" no formulário público e responde quatro perguntas: o CNPJ ou
CPF de quem recebe a nota, o e-mail, se a empresa retém o ISS e o que precisa constar na nota. Este
módulo lê essas respostas do JSON da `FormResponse` (pelas chaves estáveis da 123) e as entrega a
`pedido_de_nota_ops.completar_pelo_formulario`, que é quem escreve os `nota_*` — só em campo vazio.

Também daqui sai a sugestão de município do evento, onde o ISS do serviço 17.10 é devido: a cidade
do formulário ligado e, sem ela, a que dá para tirar do endereço do evento. A sugestão é calculada
na leitura e nunca gravada sozinha: só vira `nota_municipio` quando alguém salva o bloco.

Puro: sem `flask.request`, sem commit.
"""

from __future__ import annotations

import re
from typing import Any

from app.calendar import pedido_de_nota_ops
from app.documentos import eh_cnpj, so_digitos
from app.formularios.formularios_ops import (
    CHAVE_DOC_DA_NOTA,
    CHAVE_EMAIL_DA_NOTA,
    CHAVE_ISS_SO_PARA_CNPJ,
    CHAVE_PRECISA_NOTA,
    CHAVE_REFERENCIA_DA_NOTA,
)
from app.models import FormResponse

RESPOSTA_SIM = "Sim"
RESPOSTA_NAO = "Não"

CHAVE_CIDADE = "cidade"
CHAVE_ESTADO = "estado"

UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)
# "…, Sorocaba - SP, 18035-000" (o formato do Google e o do formulário), "Praia Grande/SP" e
# "Jundiaí, SP". A cidade não tem dígito nem os separadores; a UF é conferida contra a lista, para
# "Bloco - AB" não virar município.
_RE_CIDADE_UF = re.compile(
    r"(?:^|[,\-–—]\s*)(?P<cidade>[^\d,\-–—/]{2,60}?)\s*(?:-|–|—|/|,)\s*(?P<uf>[A-Za-z]{2})(?=\s*(?:,|$|\d|-|–|—))"
)


def _valores(response: FormResponse) -> dict[str, str]:
    """Chave → valor das respostas com chave estável (as anteriores à 123 ficam de fora)."""
    valores: dict[str, str] = {}
    for secao in response.data_sections:
        for campo in secao.get("campos", []):
            if len(campo) == 3:
                valores[campo[0]] = (campo[2] or "").strip()
    return valores


def respostas_da_nota(response: FormResponse) -> dict[str, Any] | None:
    """O que a cliente respondeu sobre a nota; `None` quando ela não pediu nota.

    Returns:
        `{response_id, doc, email, iss, referencia}` — `doc` só com dígitos; `iss` é o texto da
        resposta ("Sim", "Não", "Não sei") ou `None` quando a pergunta não foi feita (CPF).
    """
    valores = _valores(response)
    if valores.get(CHAVE_PRECISA_NOTA) != RESPOSTA_SIM:
        return None
    doc = so_digitos(valores.get(CHAVE_DOC_DA_NOTA)) or None
    return {
        "response_id": response.id,
        "doc": doc,
        "email": valores.get(CHAVE_EMAIL_DA_NOTA) or None,
        "iss": (valores.get(CHAVE_ISS_SO_PARA_CNPJ) or None) if eh_cnpj(doc) else None,
        "referencia": valores.get(CHAVE_REFERENCIA_DA_NOTA) or None,
    }


def _iss_retido(resposta: str | None) -> bool | None:
    """ "Sim"/"Não" viram o dado; "Não sei" e a pergunta não feita não gravam nada."""
    if resposta == RESPOSTA_SIM:
        return True
    if resposta == RESPOSTA_NAO:
        return False
    return None


def levar_para_o_evento(response: FormResponse, event: Any) -> list[str]:
    """Completa os dados da nota do evento com as respostas do formulário. Sem commit.

    Chamado pelo núcleo único do vínculo (`formularios_ops.apply_event_link`), então vale para o
    automático, o manual, a sugestão confirmada e a criação a partir do formulário.

    Returns:
        As colunas preenchidas; vazio quando a cliente não pediu nota ou nada estava vazio.
    """
    respostas = respostas_da_nota(response)
    if respostas is None:
        return []
    return pedido_de_nota_ops.completar_pelo_formulario(
        event,
        doc=respostas["doc"],
        email=respostas["email"],
        iss_retido=_iss_retido(respostas["iss"]),
        referencia=respostas["referencia"],
    )


def _formularios_do_evento(event: Any) -> list[FormResponse]:
    """Os formulários ligados, o mais recente primeiro."""
    return sorted(getattr(event, "form_responses", None) or [], key=lambda r: r.id, reverse=True)


def do_formulario_do_evento(event: Any) -> dict[str, Any] | None:
    """As respostas da nota do formulário ligado mais recente que pediu nota — o que a vendedora
    confere ao lado dos campos. `None` sem formulário que tenha pedido nota."""
    for response in _formularios_do_evento(event):
        respostas = respostas_da_nota(response)
        if respostas is not None:
            return respostas
    return None


def municipio_do_endereco(endereco: str | None) -> str | None:
    """ "Cidade - UF" tirada de uma linha de endereço; `None` quando não dá para ter certeza.

    Fica com a ÚLTIMA ocorrência: no endereço do Google o bairro vem antes ("… - Centro,
    Sorocaba - SP, …"), e é a cidade que encosta na UF.
    """
    achado = None
    for m in _RE_CIDADE_UF.finditer(endereco or ""):
        if m.group("uf").upper() in UFS and m.group("cidade").strip():
            achado = m
    if achado is None:
        return None
    return f"{achado.group('cidade').strip()} - {achado.group('uf').upper()}"


def _municipio_do_formulario(response: FormResponse) -> str | None:
    valores = _valores(response)
    cidade, uf = valores.get(CHAVE_CIDADE, ""), valores.get(CHAVE_ESTADO, "").upper()
    if cidade and uf in UFS:
        return f"{cidade} - {uf}"
    return municipio_do_endereco(valores.get("endereco_evento"))


def municipio_sugerido(event: Any) -> str | None:
    """A sugestão para o município do evento: o formulário ligado e, sem ele, o endereço do evento.

    A cliente digitou a cidade num campo próprio (ou o CEP a preencheu); o endereço do evento é
    texto livre vindo do Google. Por isso o formulário vem antes.
    """
    for response in _formularios_do_evento(event):
        sugestao = _municipio_do_formulario(response)
        if sugestao:
            return sugestao
    return municipio_do_endereco(getattr(event, "location", None))

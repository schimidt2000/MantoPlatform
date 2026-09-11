"""O formulário traduzido para o cadastro de evento (feature 298).

Extrator puro (sem ``flask.request``): lê o que a cliente escreveu, nos dois vocabulários de chave
que convivem desde 01/06 — o formulário nativo e a carga WhatsForm, cujas chaves são slugs do
rótulo e cuja hora vem dentro de ``data_do_evento`` — e devolve só o que dá para confiar como
valor, com a origem de cada campo, as observações rotuladas, os alertas com o texto da cliente e
os eventos da cliente que ainda não têm formulário.

Valor de venda, vendedor e título NUNCA vêm daqui: são decisão da comercial.

Contrato: ``specs/298-formulario-vira-evento/contracts/pre-evento.md``.
"""

import re
from datetime import datetime, timedelta

from app.formularios.destino_ops import eh_data_suspeita, eventos_livres_por_telefone
from app.formularios.formularios_ops import corte_dia_sp, dia_sp
from app.models import Client, FormResponse
from app.utils import strip_accents_lower

#: Chaves de cada informação nos dois vocabulários (nativo · WhatsForm). Chave desconhecida é
#: ignorada sem erro; opção nova criada pelo editor de campos cai em "sem correspondente".
SINONIMOS: dict[str, tuple[str, ...]] = {
    "hora": ("hora_evento", "hora_do_evento", "horario_do_evento"),
    "data_hora": ("data_do_evento",),
    "periodo": ("periodo_contratacao", "periodo_de_contratacao"),
    "tipo": ("tipo_contratacao", "tipo_de_contratacao"),
    "pagamento": ("forma_pagamento", "forma_de_pagamento"),
    "pagamento_outros": ("descreva_outros",),
    "logradouro": ("logradouro",),
    "numero": ("numero",),
    "complemento": ("complemento",),
    "bairro": ("bairro",),
    "cidade": ("cidade",),
    "estado": ("estado",),
    "cep": ("cep",),
    # Corporativo: o endereço DO EVENTO — nunca `endereco_empresa` (nem `endereco_contratante`).
    "endereco_evento": ("endereco_evento", "endereco_completo_do_evento", "endereco_do_evento"),
    "tema": ("tema_evento", "tema_do_evento"),
    "aniversariante": ("nome_aniversariante", "nome_do_aniversariante"),
    "idade": ("idade_aniversariante", "idade_do_aniversariante"),
    "espaco": ("espaco_evento", "espaco_escolhido_para_o_evento"),
    "briefing": ("briefing", "briefing_do_evento"),
    "observacoes": ("observacoes", "observacoes_contratuais"),
    "assessoria": ("assessoria",),
    "personagens": ("quais_personagens", "personagens"),
    "qtd_personagens": ("qtd_personagens", "quantidade_de_personagens"),
    "email": ("email", "e_mail"),
    "cpf": ("cpf", "cpf_responsavel"),
    "cnpj": ("cnpj",),
}

#: Explicação de cada alerta, em pt-BR — a tela mostra o texto e não conhece os códigos.
_MENSAGENS = {
    "data_suspeita": (
        "A data informada parece errada: é anterior ao dia em que o formulário chegou, ou está a "
        "mais de 2 anos dele. Confira com a cliente."
    ),
    "hora_ausente": "A cliente não informou o horário.",
    "periodo_ambiguo": "Não deu para entender o período contratado — preencha o horário de fim.",
    "endereco_incompleto": "O endereço veio sem número ou sem CEP — complete antes de salvar.",
    "sem_correspondente": "Essa forma de pagamento não existe no cadastro — escolha uma.",
    "tipo_sem_correspondente": (
        "O tipo de contratação não corresponde a um tipo de evento — escolha um."
    ),
    "cliente_sugerida": "Cliente encontrada pelo telefone do formulário — confira se é ela.",
}

#: Forma de pagamento: texto normalizado (sem acento, minúsculo, espaços únicos) → cadastro.
#: "Cartão de Crédito (em até 3x com acréscimo de 15%)", "Em 2x" (corporativo), "Boleto" e
#: "Outros" ficam SEM correspondente de propósito: o cadastro não tem essas formas.
_PAGAMENTOS: dict[str, tuple[str, int | None]] = {
    "a vista": ("avista", None),
    "a vista antecipado": ("avista", None),
    "em 2x no pix (50% no ato + 50% em ate 2 dias antes do evento)": ("pix_parcelado", 2),
    "faturado": ("faturado", None),
}

_HORA = r"(\d{1,2})\s*(?::\s*(\d{2})|h\s*(\d{2})?)?"
_RE_HORA = re.compile(r"(?<!\d)(\d{1,2})\s*(?::\s*(\d{2})|h\s*(\d{2})?)(?!\d)")
_RE_INTERVALO = re.compile(rf"^(?:d[ao]s?\s+)?{_HORA}\s*(?:as|a|ate|-|–)\s*{_HORA}\s*(?:h|hs)?$")
_RE_DURACAO = re.compile(r"^(\d{1,2})\s*(?:h|hs|hora|horas)$")
_RE_CEP = re.compile(r"\d{5}-?\d{3}")
_RE_SEPARA_PERSONAGENS = re.compile(r"\s*(?:,|;|\+|/|\be\b)\s*", re.IGNORECASE)

#: "3 a 4" com as duas horas antes das 7 é duração dita de outro jeito, não festa de madrugada.
_MADRUGADA = 7


def _normalizar(texto: str) -> str:
    return " ".join(strip_accents_lower(texto).split())


def _campos(response: FormResponse) -> dict[str, str]:
    """Respostas por chave estável — a primeira não vazia vence. Resposta sem chave é ignorada."""
    campos: dict[str, str] = {}
    for secao in response.data_sections:
        if not isinstance(secao, dict):
            continue
        for campo in secao.get("campos") or []:
            if len(campo) == 3 and campo[0] and str(campo[2] or "").strip():
                campos.setdefault(campo[0], str(campo[2]).strip())
    return campos


def _valor(campos: dict[str, str], nome: str) -> str:
    for chave in SINONIMOS[nome]:
        if campos.get(chave):
            return campos[chave]
    return ""


def _alerta(campo: str, motivo: str, texto: str | None = None) -> dict:
    return {
        "campo": campo,
        "motivo": motivo,
        "mensagem": _MENSAGENS[motivo],
        "texto_da_cliente": texto or None,
    }


def _hhmm(hora: str, minutos: str | None, minutos_h: str | None) -> str | None:
    h, m = int(hora), int(minutos or minutos_h or 0)
    return f"{h:02d}:{m:02d}" if h <= 23 and m <= 59 else None


def _hora(texto: str) -> str | None:
    """ "15:00", "15h", "15h30", "15", ou a hora dentro de "2026-10-10 16:00" → "HH:MM"."""
    texto = (texto or "").strip()
    if texto.isdigit():
        return _hhmm(texto, None, None)
    achado = _RE_HORA.search(texto)
    return _hhmm(*achado.groups()) if achado else None


def _hora_plausivel(hhmm: str | None) -> str | None:
    """A hora de dentro de ``data_do_evento`` só vale se parece hora de festa.

    Na carga WhatsForm essa hora é a do seletor de data-hora, que a cliente nem sempre mexe — a
    produção tem 15:03, 12:04 e 04:00 (medido em 11/09). Só vale entre 7h e 23h e em minuto
    redondo (múltiplo de 5), e sempre cede ao intervalo escrito no período.
    """
    if not hhmm:
        return None
    hora, minuto = (int(x) for x in hhmm.split(":"))
    return hhmm if _MADRUGADA <= hora <= 23 and minuto % 5 == 0 else None


def _sem_pontas(texto: str) -> str:
    """Tira espaço e pontuação solta das pontas de uma parte do endereço."""
    return (texto or "").strip(" ,;-")


def _eh_duracao(texto: str) -> bool:
    return bool(_RE_DURACAO.match(_normalizar(texto)))


def _periodo(texto: str, inicio: str | None) -> tuple[str | None, str] | None:
    """Início e fim pelo período contratado, só nas formas inequívocas; ``None`` = ambíguo.

    "das 16h às 19h", "16-19", "15h-18h" → (16:00, 19:00). "3 horas" ou "3h" → (início,
    início + 3 h), e exige o início. O resto ("3h ou 4h", "a tarde toda") é ambíguo.
    """
    norm = _normalizar(texto)
    intervalo = _RE_INTERVALO.match(norm)
    if intervalo:
        grupos = intervalo.groups()
        if int(grupos[0]) < _MADRUGADA and int(grupos[3]) < _MADRUGADA:
            return None
        de, ate = _hhmm(*grupos[:3]), _hhmm(*grupos[3:])
        return (de, ate) if de and ate else None
    duracao = _RE_DURACAO.match(norm)
    if duracao and inicio:
        fim = datetime.strptime(inicio, "%H:%M") + timedelta(hours=int(duracao.group(1)))
        return inicio, fim.strftime("%H:%M")
    return None


def _tipo(response: FormResponse, campos: dict[str, str]) -> tuple[str | None, dict | None]:
    if response.form_type == "corporativo":
        return "CORP", None
    texto = _valor(campos, "tipo")
    if not texto:
        return None, None
    norm = _normalizar(texto)
    if "show" in norm:
        return "SHOW", None
    if "receptivo" in norm and "interativo" in norm:
        return "R&I", None
    return None, _alerta("event_type", "tipo_sem_correspondente", texto)


def _pagamento(campos: dict[str, str]) -> tuple[str | None, int | None, dict | None]:
    texto = _valor(campos, "pagamento")
    if not texto:
        return None, None, None
    norm = _normalizar(texto)
    forma = _PAGAMENTOS.get(norm)
    if forma is None and norm.startswith("em 2x no pix"):
        forma = ("pix_parcelado", 2)
    if forma is not None:
        return forma[0], forma[1], None
    outros = _valor(campos, "pagamento_outros")
    escrito = f"{texto} — {outros}" if outros else texto
    return None, None, _alerta("payment_method", "sem_correspondente", escrito)


def _local(response: FormResponse, campos: dict[str, str]) -> tuple[str | None, dict | None]:
    """Uma linha de endereço do EVENTO. Incompleto entra, com alerta — ajuda mais que o vazio."""
    if response.form_type == "corporativo":
        texto = _valor(campos, "endereco_evento")
        if not texto:
            return None, None
        tem_numero = bool(re.search(r"\d", _RE_CEP.sub("", texto)))
        completo = tem_numero and bool(_RE_CEP.search(texto))
        return texto, None if completo else _alerta("location", "endereco_incompleto", texto)
    logradouro, numero, cep = (_valor(campos, k) for k in ("logradouro", "numero", "cep"))
    complemento, bairro = _valor(campos, "complemento"), _valor(campos, "bairro")
    cidade_uf = " - ".join(x for x in (_valor(campos, "cidade"), _valor(campos, "estado")) if x)
    if not (logradouro or bairro or cidade_uf or cep):
        return None, None
    # A cliente às vezes digita a vírgula no próprio campo ("Rua Parauna,") — sem limpar, a linha
    # saía "Rua Parauna,, 23".
    local = ", ".join(_sem_pontas(x) for x in (logradouro, numero, complemento) if _sem_pontas(x))
    for separador, parte in ((" - ", bairro), (", ", cidade_uf), (", ", cep)):
        if _sem_pontas(parte):
            local = f"{local}{separador}{_sem_pontas(parte)}" if local else _sem_pontas(parte)
    completo = bool(logradouro and numero and cep)
    return local, None if completo else _alerta("location", "endereco_incompleto")


def _clientes(
    response: FormResponse, campos: dict[str, str]
) -> tuple[list[dict], dict | None, dict | None]:
    """(clientes do evento, dados do cadastro rápido, alerta).

    A ficha do formulário; senão a ficha com o mesmo telefone (sugerida, para conferir); senão os
    dados para o cadastro rápido abrir preenchido.
    """
    if response.client is not None:
        cliente = response.client
        return (
            [{"client_id": cliente.id, "relation": "Contratante", "name": cliente.name}],
            None,
            None,
        )
    ficha = (
        Client.query.filter_by(phone=response.contact_phone).first()
        if response.contact_phone
        else None
    )
    if ficha is not None:
        alerta = _alerta("clients", "cliente_sugerida", response.contact_name)
        return (
            [{"client_id": ficha.id, "relation": "Contratante", "name": ficha.name}],
            None,
            alerta,
        )
    rapido = {
        "name": response.contact_name or "",
        "phone": response.contact_phone_display or response.contact_phone or "",
        "email": _valor(campos, "email"),
        "cnpj" if response.form_type == "corporativo" else "cpf": _valor(
            campos, "cnpj" if response.form_type == "corporativo" else "cpf"
        ),
    }
    return [], {k: v for k, v in rapido.items() if v}, None


def _personagens(campos: dict[str, str]) -> tuple[list[str], str]:
    """(nomes sugeridos, texto original para a observação). Sempre "confira" na tela."""
    texto = _valor(campos, "personagens")
    if not texto:
        return [], ""
    nomes = [p.strip() for p in _RE_SEPARA_PERSONAGENS.split(texto) if p and p.strip()]
    quantos = _valor(campos, "qtd_personagens")
    return nomes, f"{texto} ({quantos} personagens)" if quantos else texto


def _observacoes(campos: dict[str, str], personagens_escritos: str) -> list[dict]:
    """Viram observações de texto rotuladas — nunca a descrição, que vai para o Google Agenda."""
    nome, idade = _valor(campos, "aniversariante"), _valor(campos, "idade")
    aniversariante = (
        f"{nome}, {idade} anos"
        if nome and idade.isdigit()
        else ", ".join(x for x in (nome, idade) if x)
    )
    rotulos = (
        ("Tema", _valor(campos, "tema")),
        ("Aniversariante", aniversariante),
        ("Espaço", _valor(campos, "espaco")),
        ("Briefing", _valor(campos, "briefing")),
        ("Personagens pedidos (texto da cliente)", personagens_escritos),
        ("Observações contratuais", _valor(campos, "observacoes")),
        ("Assessoria", _valor(campos, "assessoria")),
    )
    return [{"label": rotulo, "text": texto} for rotulo, texto in rotulos if texto]


def _eventos_da_cliente(response: FormResponse) -> list[dict]:
    """Eventos da cliente (pelo telefone) desde o corte que ainda não têm formulário (FR-013).

    Sem janela de dias, ao contrário da sugestão da Home: aqui a pergunta é "não é um destes?"
    antes de criar mais uma festa na Agenda.
    """
    if not response.contact_phone:
        return []
    desde = corte_dia_sp()
    eventos = sorted(
        (
            ev
            for ev, telefones in eventos_livres_por_telefone({response.contact_phone})
            if response.contact_phone in telefones and ev.start_at and ev.start_at.date() >= desde
        ),
        key=lambda ev: ev.start_at,
    )
    return [
        {"event_id": ev.id, "titulo": ev.title, "data": ev.start_at.date().isoformat()}
        for ev in eventos
    ]


def extrair_para_evento(response: FormResponse) -> dict:
    """``{valores, origem, observacoes, alertas, eventos_da_cliente}`` para o cadastro de evento.

    Campo sem valor confiável fica fora de ``valores``, com um alerta que traz o texto da
    cliente. A data suspeita entra, com alerta: o cadastro pede conferência sem desabilitar o
    Salvar.
    """
    campos = _campos(response)
    valores: dict = {}
    origem: list[str] = []
    alertas: list[dict] = []

    def usar(campo: str, valor) -> None:
        if valor not in (None, "", []):
            valores[campo] = valor
            origem.append(campo)

    if response.event_date:
        usar("date", response.event_date.isoformat())
        if eh_data_suspeita(response.event_date, dia_sp(response.created_at)):
            escrito = response.event_date.strftime("%d/%m/%Y")
            alertas.append(_alerta("date", "data_suspeita", escrito))

    # Hora: a escrita no campo próprio é forte; a de dentro de `data_do_evento` (WhatsForm) é
    # fraca — só vale se plausível e cede ao intervalo do período (ver `_hora_plausivel`).
    hora_escrita = _hora(_valor(campos, "hora"))
    data_hora = _valor(campos, "data_hora")
    hora_da_data = _hora_plausivel(_hora(data_hora))
    inicio, fim = hora_escrita, None
    periodo_escrito = _valor(campos, "periodo")
    if periodo_escrito:
        periodo = _periodo(periodo_escrito, hora_escrita or hora_da_data)
        if periodo is None:
            # "4 horas" sem hora de início não é período ambíguo: falta a hora (alerta abaixo).
            if not (_eh_duracao(periodo_escrito) and not (hora_escrita or hora_da_data)):
                alertas.append(_alerta("end", "periodo_ambiguo", periodo_escrito))
        elif hora_escrita and periodo[0] != hora_escrita:
            # O período que contradiz a hora ESCRITA é ambíguo: qual das duas vale?
            alertas.append(_alerta("end", "periodo_ambiguo", periodo_escrito))
        else:
            inicio, fim = periodo
    inicio = inicio or hora_da_data
    usar("start", inicio)
    usar("end", fim)
    if not inicio:
        # Hora de seletor descartada: mostra o que estava lá, para a comercial decidir.
        descartada = data_hora if _hora(data_hora) else None
        alertas.append(_alerta("start", "hora_ausente", descartada))

    local, alerta = _local(response, campos)
    usar("location", local)
    tipo, alerta_tipo = _tipo(response, campos)
    usar("event_type", tipo)
    forma, parcelas, alerta_pagamento = _pagamento(campos)
    usar("payment_method", forma)
    if parcelas:
        valores["payment_installments"] = parcelas
    clientes, rapido, alerta_cliente = _clientes(response, campos)
    usar("clients", clientes)
    valores["quick_create_client"] = rapido or None
    alertas.extend(a for a in (alerta, alerta_tipo, alerta_pagamento, alerta_cliente) if a)
    nomes, personagens_escritos = _personagens(campos)
    usar("characters", nomes)

    return {
        "valores": valores,
        "origem": origem,
        "observacoes": _observacoes(campos, personagens_escritos),
        "alertas": alertas,
        "eventos_da_cliente": _eventos_da_cliente(response),
    }

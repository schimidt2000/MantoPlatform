"""Inventário de mídia: quem aponta para um arquivo que não está mais lá (feature 292).

Nasceu do dano da migração Railway → Render (28/08/2026): o dump do banco veio, o volume de
uploads não. As linhas continuam apontando para `/uploads/...`, o Flask responde 404 e a tela
desenha um quadrado quebrado. **Nenhum campo ficou NULL** — por isso toda consulta escrita com
``IS NULL`` subconta o problema, e o critério certo é cruzar o caminho gravado com a existência
do arquivo em disco.

Módulo puro (não importa `flask.request`), como manda a arquitetura: quem chama é o comando
`flask midia-orfa`, o `flask fix-heic` e a campanha de atualização cadastral.
"""
from __future__ import annotations

import os
from typing import Any, NamedTuple

from app import imaging
from app.storage import caminho_local

#: Motivos pelos quais uma foto não aparece na tela, em ordem de gravidade.
MOTIVO_OK = "ok"
MOTIVO_VAZIO = "campo vazio"
MOTIVO_EXTERNO = "URL externa (Drive)"
MOTIVO_SUMIU = "arquivo sumiu do disco"
MOTIVO_NAO_E_IMAGEM = "arquivo não é imagem"
MOTIVO_ILEGIVEL = "formato que o navegador não abre"

#: `(coluna, rótulo em pt-BR, subpasta esperada)`. O rótulo é o que o artista lê no e-mail de
#: atualização cadastral — por isso mora aqui, junto da coluna, e não numa segunda lista.
ARQUIVOS_DO_TALENTO: tuple[tuple[str, str, str], ...] = (
    ("photo_face_path", "foto de rosto", "talent_photos"),
    ("photo_full_path", "foto de corpo inteiro", "talent_photos"),
    ("doc_photo_path", "foto do documento (RG, CPF ou CNH)", "talent_docs"),
    ("cnh_file_path", "arquivo da CNH aberta", "talent_docs"),
)

#: Extensões que o navegador abre sem conversão. O que estiver fora disto e for aceito no upload
#: (HEIC de iPhone, TIFF) precisa ter virado JPEG na gravação — se não virou, some da tela.
_EXTS_EXIBIVEIS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"})


class Achado(NamedTuple):
    """Um arquivo referenciado pelo banco e o veredito sobre ele."""

    familia: str
    registro_id: int
    nome: str
    coluna: str
    url: str
    motivo: str

    @property
    def problema(self) -> bool:
        """True quando este achado explica uma imagem que não aparece na tela."""
        return self.motivo not in (MOTIVO_OK, MOTIVO_EXTERNO, MOTIVO_VAZIO)


def classificar(url: str | None, *, conferir_conteudo: bool = True) -> str:
    """Diz por que (ou se) esta URL não desenha na tela.

    Args:
        url: O valor gravado na coluna.
        conferir_conteudo: Abre o arquivo para checar que ele é mesmo uma imagem. Custa um decode
            por arquivo; vale para o inventário, não para um laço de request.
    """
    if not url or not str(url).strip():
        return MOTIVO_VAZIO
    if str(url).startswith(("http://", "https://")):
        return MOTIVO_EXTERNO

    caminho = caminho_local(url)
    if caminho is None or not os.path.exists(caminho):
        return MOTIVO_SUMIU

    ext = os.path.splitext(url)[1].lower()
    if ext not in _EXTS_EXIBIVEIS:
        return MOTIVO_ILEGIVEL
    if not conferir_conteudo or ext == ".pdf":
        return MOTIVO_OK

    # A extensão pode estar mentindo: existe pelo menos um PDF gravado como `.jpg` em produção,
    # e ele é servido como `image/jpeg` — existe, tem bytes, e nenhum navegador desenha.
    with open(caminho, "rb") as handle:
        dados = handle.read()
    if dados.startswith(b"%PDF"):
        return MOTIVO_NAO_E_IMAGEM
    return MOTIVO_OK if imaging.abrir(dados) is not None else MOTIVO_NAO_E_IMAGEM


def faltas_do_talento(talent: Any) -> list[str]:
    """Rótulos em pt-BR dos arquivos deste talento que não aparecem mais.

    É o que entra no corpo do e-mail de atualização cadastral: "faltam a foto de rosto e a foto do
    documento", nunca um texto genérico.
    """
    faltas = []
    for coluna, rotulo, _ in ARQUIVOS_DO_TALENTO:
        if classificar(getattr(talent, coluna, None), conferir_conteudo=False) == MOTIVO_SUMIU:
            faltas.append(rotulo)
    return faltas


def _achados_de(familia, registros, nome_attr, colunas, conferir):
    for reg in registros:
        nome = getattr(reg, nome_attr, None) or f"#{reg.id}"
        for coluna in colunas:
            url = getattr(reg, coluna, None)
            motivo = classificar(url, conferir_conteudo=conferir)
            yield Achado(familia, reg.id, str(nome), coluna, str(url or ""), motivo)


def inventario(*, familia: str = "todas", conferir_conteudo: bool = True) -> list[Achado]:
    """Varre o banco inteiro cruzando cada coluna de mídia com o disco.

    Args:
        familia: `"talento"`, `"figurino"`, `"catalogo"`, `"portfolio"`, `"acervo3d"`, `"usuario"`
            ou `"todas"`.
        conferir_conteudo: Abre cada arquivo para checar que é imagem de verdade.

    Returns:
        Um `Achado` por coluna de cada registro — inclusive os `ok`, para o relatório poder dizer
        "40 de 267" em vez de só "40".
    """
    from app.models import (
        Acervo3DItem,
        CatalogCharacter,
        CatalogItemImage,
        FigurinoSheet,
        Talent,
        TalentMedia,
        User,
    )

    colunas_talento = [c for c, _, _ in ARQUIVOS_DO_TALENTO]
    fontes = {
        "talento": (Talent, "full_name", colunas_talento),
        "figurino": (FigurinoSheet, "character_name", ["photo_url"]),
        "catalogo": (CatalogItemImage, "url", ["url"]),
        "personagem": (CatalogCharacter, "name", ["photo_url"]),
        "portfolio": (TalentMedia, "label", ["file_path"]),
        "acervo3d": (Acervo3DItem, "name", ["photo_url"]),
        "usuario": (User, "name", ["profile_photo"]),
    }
    alvos = fontes if familia == "todas" else {familia: fontes[familia]}

    achados: list[Achado] = []
    for nome_familia, (modelo, nome_attr, colunas) in alvos.items():
        registros = modelo.query.order_by(modelo.id).all()
        achados.extend(
            _achados_de(nome_familia, registros, nome_attr, colunas, conferir_conteudo)
        )
    return achados


def resumo(achados: list[Achado]) -> dict[str, dict[str, int]]:
    """Contagem por família e motivo, para o cabeçalho do relatório."""
    saida: dict[str, dict[str, int]] = {}
    for achado in achados:
        saida.setdefault(achado.familia, {}).setdefault(achado.motivo, 0)
        saida[achado.familia][achado.motivo] += 1
    return saida

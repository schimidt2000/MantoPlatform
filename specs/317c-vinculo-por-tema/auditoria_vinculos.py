"""Auditoria (só leitura) dos contratos da ClickSign ligados a uma venda — correção 317c.

Para cada documento de cliente com vínculo "ligado" responde duas perguntas com as funções do próprio
sistema (`sincronizar_ops` e `contratos_ops`), sem reimplementar a regra:

1. **O que sustenta este vínculo hoje?** Telefone do nome ou de quem assina contra os telefones da
   venda (contratantes, ficha, formulário), data contra os dias da venda, e-mail, e por último só a
   palavra do tema (título ou tema do formulário).
2. **O que a regra decidiria hoje, do zero?** Chama `_vincular` no documento e desfaz (`rollback`):
   vínculo automático nunca é reavaliado depois de feito, então a venda certa pode ter aparecido depois.

Uso (da raiz da worktree, contra o espelho da correção — nunca contra a produção):
    $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
    $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
    python specs/317c-vinculo-por-tema/auditoria_vinculos.py

Não grava nada: toda mutação de `_vincular` é desfeita, e não há `commit` no arquivo.
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MANTO_SEM_THREADS", "1")
os.environ.setdefault("FLASK_ENV", "development")

from app import create_app, db  # noqa: E402
from app.constants import CLICKSIGN_TIPO_CLIENTE, VINCULO_LIGADO  # noqa: E402
from app.contratos import contratos_ops as nucleo  # noqa: E402
from app.contratos import sincronizar_ops as sinc  # noqa: E402
from app.models import CalendarEvent, ClicksignDocumento  # noqa: E402

DATA_TELEFONE = "A  data + telefone"
TELEFONE_UM_DIA = "B  telefone, data a um dia"
TELEFONE_OUTRA_DATA = "B2 telefone, outra data"
EMAIL = "C  e-mail"
SO_TEMA = "D  só a palavra do tema"
NADA = "E  nada bate"
_RE_FONE = re.compile(r"\(?\d{2}\)?\s*\d{4,5}-?\d{4}")


def _sem_fone(nome: str | None) -> str:
    """O nome do envelope sem o telefone (a auditoria não precisa dele na tela)."""
    return _RE_FONE.sub("(tel)", nome or "")


def _chaves(doc: ClicksignDocumento) -> set[str]:
    return {
        c
        for c in (
            nucleo.chave_telefone(doc.telefone_lido),
            nucleo.chave_telefone(doc.signatario_telefone),
        )
        if c
    }


def _venda_do(principal: CalendarEvent) -> tuple[sinc._Venda | None, list]:
    dias = sorted({e.start_at.date() for e in [principal, *principal.satellites] if e.start_at})
    if not dias:
        return None, []
    vendas = sinc._vendas_na_data(dias[0], dias[-1])
    return next((v for v in vendas if v.principal.id == principal.id), None), dias


def _sinal(doc: ClicksignDocumento, venda: sinc._Venda | None, dias: list) -> tuple[str, list[str]]:
    if venda is None:
        return NADA, []
    fone = bool(_chaves(doc) & venda.chaves)
    data = doc.data_lida
    comuns = sorted(
        nucleo.palavras_do_tema(doc.tema_lido)
        & set().union(*(nucleo.palavras_do_tema(t) for t in venda.temas if t))
    )
    if fone and data in dias:
        return DATA_TELEFONE, comuns
    if fone and data and any(abs((data - d).days) <= 1 for d in dias):
        return TELEFONE_UM_DIA, comuns
    if fone:
        return TELEFONE_OUTRA_DATA, comuns
    emails = {e.lower() for e in (nucleo.ler_nome(doc.nome).email, doc.signatario_email) if e}
    if emails & venda.emails:
        return EMAIL, comuns
    return (SO_TEMA if comuns else NADA), comuns


def _outra_com_o_telefone(doc: ClicksignDocumento) -> list[int]:
    """Outras vendas vivas no dia do contrato que têm o telefone do contrato."""
    chaves = _chaves(doc)
    if not chaves or doc.data_lida is None:
        return []
    return sorted(
        v.principal.id
        for v in sinc._vendas_na_data(doc.data_lida)
        if v.principal.id != doc.event_id and not v.principal.cancelled_at and chaves & v.chaves
    )


def _regra_hoje(doc: ClicksignDocumento) -> tuple[str, int | None, str | None]:
    """O que `_vincular` decide agora; a mutação é desfeita antes de voltar."""
    sinc._vincular(doc)
    decidido = (doc.vinculo, doc.event_id, doc.vinculo_motivo)
    db.session.rollback()
    return decidido


def main() -> None:
    app = create_app()
    with app.app_context():
        ids = [
            i
            for (i,) in db.session.query(ClicksignDocumento.id)
            .filter_by(vinculo=VINCULO_LIGADO, tipo=CLICKSIGN_TIPO_CLIENTE)
            .order_by(ClicksignDocumento.id)
        ]
        por_sinal: Counter[tuple[str, str]] = Counter()
        mudaria: list[str] = []
        detalhes: dict[str, list[str]] = defaultdict(list)
        for doc_id in ids:
            doc = db.session.get(ClicksignDocumento, doc_id)
            ligado_a = doc.event_id
            principal = db.session.get(CalendarEvent, ligado_a)
            venda, dias = _venda_do(principal)
            sinal, comuns = _sinal(doc, venda, dias)
            origem = doc.vinculo_origem or "?"
            por_sinal[(sinal, origem)] += 1
            outra = _outra_com_o_telefone(doc)
            linha = (
                f"  doc {doc.id} [{origem}/{doc.status}] {_sem_fone(doc.nome)!r}\n"
                f"      → evento {ligado_a} ({principal.event_type}) {(principal.title or '')[:70]!r} "
                f"dias {[d.isoformat() for d in dias[:4]]}{'…' if len(dias) > 4 else ''}\n"
                f"      venda {'COM' if venda and venda.chaves else 'sem'} telefone conhecido; "
                f"palavra em comum: {comuns or '—'}"
                + (
                    f"\n      OUTRA VENDA NO DIA COM O TELEFONE DO CONTRATO: {outra}"
                    if outra
                    else ""
                )
            )
            vinculo, novo_evento, motivo = _regra_hoje(doc)
            if vinculo != VINCULO_LIGADO or novo_evento != ligado_a:
                destino = (
                    f"evento {novo_evento}"
                    if vinculo == VINCULO_LIGADO
                    else f"{vinculo} ({motivo})"
                )
                mudaria.append(f"{linha}\n      REGRA HOJE: {destino}")
            if sinal in (SO_TEMA, NADA, TELEFONE_OUTRA_DATA) or outra:
                detalhes[sinal].append(linha)

        print(f"Documentos de cliente ligados: {len(ids)}\n")
        for (sinal, origem), n in sorted(por_sinal.items()):
            print(f"{n:4d}  {sinal}  ({origem})")
        print(f"\n===== A regra de hoje decidiria diferente em {len(mudaria)} =====")
        print("\n".join(mudaria) or "  (nenhum)")
        for sinal in (SO_TEMA, NADA, TELEFONE_OUTRA_DATA, DATA_TELEFONE, TELEFONE_UM_DIA, EMAIL):
            if detalhes[sinal]:
                print(f"\n===== {sinal} — {len(detalhes[sinal])} para olhar =====")
                print("\n".join(detalhes[sinal]))


if __name__ == "__main__":
    main()

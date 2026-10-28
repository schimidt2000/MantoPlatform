"""Verificação da correção 317b — os sinais novos que ligam o contrato da ClickSign à venda.

Reaproveita o dublê da ClickSign, o disjuntor de rede, a semeadura e a limpeza do `verify_317.py`
(importado como módulo — a ClickSign nunca é chamada). As datas ficam em 2028: o `manto_local` não
tem evento depois de 2027, e a regra do tema olha TODAS as vendas do dia, então um dia vazio é o
único jeito de o resultado não depender do espelho.

Rodar contra o manto_local (PowerShell, a partir do worktree)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    C:/Users/schim/Desktop/Manto_Platform/.venv/Scripts/python.exe specs/317b-ligacao-de-contratos/verify_317b.py
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

_CAMINHO_317 = Path(__file__).resolve().parents[1] / "317-contratos-clicksign" / "verify_317.py"
_spec = importlib.util.spec_from_file_location("verify_317", _CAMINHO_317)
v = importlib.util.module_from_spec(_spec)
sys.modules["verify_317"] = v
_spec.loader.exec_module(v)

app, db, conta, estado = v.app, v.db, v.conta, v.estado
_garante, _doc, _evento, _formulario, _nome_festa = (
    v._garante,
    v._doc,
    v._evento,
    v._formulario,
    v._nome_festa,
)
BASE = date(2028, 3, 1)
_resultados: list[tuple[str, bool, str]] = v.resultados


def _dia(n: int) -> date:
    return BASE + timedelta(days=n)


def _fone(n: int) -> str:
    return f"551190001{n:04d}"


def _sinc() -> None:
    v._sincronizar(desde=v._d(-30))


def _ligado(chave: str, venda: str) -> None:
    d = _doc(chave)
    _garante(
        d is not None and d[4] == "ligado" and d[5] == "auto" and d[3] == estado["ids"][venda],
        f"{chave} deveria ligar em {venda}: {d}",
    )


def _a_conferir(chave: str, motivo: str | None = None) -> None:
    d = _doc(chave)
    _garante(d is not None and d[4] == "a_conferir" and d[3] is None, f"{chave} → {d}")
    if motivo:
        _garante(d[6] == motivo, f"{chave}: motivo {d[6]} ≠ {motivo}")


def preparar() -> None:
    from app.constants import RoleName, now_sp
    from app.models import Client, SiteSetting

    estado["hoje"] = now_sp().date()
    estado["comercial"] = v._usuario("comercial", RoleName.COMERCIAL)
    s = SiteSetting.query.get(1)
    estado["site_original"] = {
        c: getattr(s, c)
        for c in (
            "clicksign_webhook_id",
            "clicksign_webhook_secret",
            "clicksign_webhook_secret_anterior",
            "clicksign_webhook_secret_anterior_ate",
            "clicksign_sync_at",
            "clicksign_sync_cursor",
            "clicksign_sync_pendente",
            "clicksign_sync_fim",
        )
    }
    s.clicksign_sync_at = None
    s.clicksign_sync_cursor = None
    s.clicksign_sync_pendente = False
    s.clicksign_sync_fim = None

    ev = estado["ids"]
    # Cancelado na ClickSign, sem venda; e cancelado com venda (continua ligando, como histórico).
    _evento("hist", _dia(0), telefone=_fone(1), titulo="(R&I) LEGO")
    # Venda cancelada única.
    _evento("canc", _dia(2), telefone=_fone(2), cancelado=True, titulo="(R&I) TIMAO + PUMBA")
    # Telefone a um dia; e a um dia para os dois lados (ambíguo).
    _evento("dia1", _dia(5), telefone=_fone(3), titulo="(SHOW) ANNA + ELSA")
    _evento("amb_a", _dia(7), telefone=_fone(4), titulo="(R&I) BLUEY")
    _evento("amb_b", _dia(9), telefone=_fone(4), titulo="(R&I) BINGO")
    # Formulário do mesmo telefone e da data do contrato, ligado a um evento remarcado (+7 dias).
    _evento("remarc", _dia(19), titulo="(R&I) CACA FANTASMA 1 + CACA FANTASMA 2")
    _formulario(ev["remarc"], _fone(5), "Ghostbusters")
    db.session.flush()
    from app.models import FormResponse

    fr = FormResponse.query.filter_by(event_id=ev["remarc"]).one()
    fr.event_date = _dia(12)
    # E-mail no lugar do telefone: a ficha da venda tem o e-mail.
    _evento("mail", _dia(14), telefone=_fone(6), titulo="(R&I) MICKEY + MINNIE")
    Client.query.filter_by(phone=_fone(6)).one().email = "cliente.317b@exemplo.com"
    # Tema por palavra: duas vendas no dia, sem telefone; uma com SNOOPY.
    _evento("snoopy", _dia(16), titulo="(R&I) SNOOPY + CHARLIE")
    _evento("mickey16", _dia(16), titulo="(R&I) MICKEY CLASSICO + MINNIE CLASSICO")
    # Tema ambíguo: duas vendas com a palavra.
    _evento("pirata_a", _dia(21), titulo="(R&I) MICKEY PIRATA")
    _evento("pirata_b", _dia(21), titulo="(SHOW) JACK PIRATA")
    # Dia sem venda: o tema procura no dia seguinte.
    _evento("chapeu", _dia(24), titulo="(R&I) CHAPEUZINHO VERMELHO + LOBO MAU")
    # Só palavra genérica (e cor): nunca liga.
    _evento("generica", _dia(27), titulo="(R&I) CARRO VERMELHO + FESTA")
    # Empate pelo telefone, resolvido pela palavra; o outro contrato do dia fica a conferir.
    _evento("bela", _dia(30), telefone=_fone(8), titulo="(R&I) BELA + FERA + GASTON")
    _evento("marinheiro", _dia(30), telefone=_fone(8), titulo="(R&I) MICKEY MARINHEIRO")
    # Ligado pela palavra e depois desligado à mão: não religa sozinho.
    _evento("desl", _dia(33), titulo="(R&I) RAYA + AURORA")
    db.session.commit()

    env = estado["env"]
    env["canc_sem"] = conta.envelope(
        "b_canc_sem", _nome_festa(_dia(40), _fone(9), "Princesas"), status="canceled"
    )
    env["canc_hist"] = conta.envelope(
        "b_canc_hist", _nome_festa(_dia(0), _fone(1), "Lego"), status="canceled"
    )
    env["canc"] = conta.envelope(
        "b_canc", _nome_festa(_dia(2), _fone(2), "Rei Leão"), status="closed"
    )
    env["dia1"] = conta.envelope("b_dia1", _nome_festa(_dia(4), _fone(3), "Frozen 2"))
    # Tema que não aparece em nenhuma das duas: senão a palavra decidiria no dia ao lado.
    env["amb"] = conta.envelope("b_amb", _nome_festa(_dia(8), _fone(4), "Dinossauros"))
    env["remarc"] = conta.envelope(
        "b_remarc", _nome_festa(_dia(12), _fone(5), "Ghostbusters (os caça fantasmas)")
    )
    env["mail"] = conta.envelope(
        "b_mail",
        f"{_dia(14):%d-%m-%Y} + cliente.317b@exemplo.com + Festa infantil",
        telefone=None,
        email="cliente.317b@exemplo.com",
        canal="email",
    )
    env["snoopy"] = conta.envelope(
        "b_snoopy", _nome_festa(_dia(16), _fone(10), "Arraiá com o Snoopy")
    )
    env["pirata"] = conta.envelope("b_pirata", _nome_festa(_dia(21), _fone(11), "Pirata"))
    env["chapeu"] = conta.envelope(
        "b_chapeu",
        _nome_festa(_dia(23), _fone(12), "Encontro Chapeuzinho Vermelho e 3 Porquinhos"),
    )
    env["generica"] = conta.envelope(
        "b_generica", _nome_festa(_dia(27), _fone(13), "Festa infantil vermelha")
    )
    env["bela"] = conta.envelope("b_bela", _nome_festa(_dia(30), _fone(8), "Bela e a Fera"))
    env["nautico"] = conta.envelope(
        "b_nautico", _nome_festa(_dia(30), _fone(8), "Náutico Fundo do Mar")
    )
    env["desl"] = conta.envelope(
        "b_desl", _nome_festa(_dia(33), _fone(14), "Raya é o último dragão")
    )


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    """Núcleo puro: palavras do tema e a venda única pela palavra."""
    from app.contratos.contratos_ops import Candidato, palavras_do_tema, tema_por_palavra

    _garante(palavras_do_tema("Turma da Mônica") == {"monica"}, palavras_do_tema("Turma da Mônica"))
    _garante(palavras_do_tema("Festa infantil - 15 anos") == set(), "genérico deveria ficar vazio")
    vendas = [Candidato(1, ("(R&I) MONICA + MAGALI",)), Candidato(2, ("(R&I) CARRO VERMELHO",))]
    _garante(tema_por_palavra("Turma da Mônica", vendas) == 1, "Mônica → 1")
    _garante(tema_por_palavra("Chapeuzinho Vermelho", vendas) is None, "cor não decide")
    dois = [Candidato(1, ("MICKEY PIRATA",)), Candidato(2, ("JACK PIRATA",))]
    _garante(tema_por_palavra("Pirata", dois) is None, "duas com a palavra → nenhuma")
    cancelada = [Candidato(1, ("SNOOPY",), cancelada=True), Candidato(2, ("MICKEY",))]
    _garante(tema_por_palavra("Snoopy", cancelada) is None, "venda cancelada não entra na palavra")
    _garante(
        tema_por_palavra("x", [Candidato(1, ("Bem Estar Qualidade de Vida",))]) is None,
        "tema curto",
    )


def cen_02() -> None:
    """Envelope cancelado sem venda sai da conferência; com venda continua ligando (histórico)."""
    _sinc()
    d = _doc("canc_sem")
    _garante(d[4] == "fora" and d[3] is None, f"cancelado sem venda → {d}")
    r = v._chamar(estado["comercial"], "get", "/api/contratos/a-conferir")
    _garante(r.status_code == 200, f"a-conferir → {r.status_code}")
    ids = {linha.get("documento_id") for linha in r.get_json()["itens"]}
    _garante(d[0] not in ids, "cancelado sem venda apareceu em A conferir")
    _ligado("canc_hist", "hist")


def cen_03() -> None:
    """Venda cancelada certa: liga a ela; o PDF assinado não entra no evento cancelado (312)."""
    _ligado("canc", "canc")
    d = _doc("canc")
    _garante(d[12] is True, f"o PDF deveria ficar pendente: {d}")
    _garante(v._anexos("canc") == 0, "anexou o PDF no evento cancelado")


def cen_04() -> None:
    """Mesmo telefone a um dia liga; um dia para cada lado (duas vendas) fica a conferir (DEVE)."""
    _ligado("dia1", "dia1")
    _a_conferir("amb", "sem_candidato")


def cen_05() -> None:
    """Formulário do mesmo telefone e da data do contrato, ligado a um evento remarcado."""
    _ligado("remarc", "remarc")


def cen_06() -> None:
    """E-mail no lugar do telefone liga pela ficha da venda."""
    _ligado("mail", "mail")


def cen_07() -> None:
    """Tema por palavra: a única venda do dia com a palavra; duas com a palavra = a conferir."""
    _ligado("snoopy", "snoopy")
    _a_conferir("pirata", "sem_candidato")


def cen_08() -> None:
    """Dia sem venda: a palavra procura no dia anterior/seguinte; palavra genérica nunca liga."""
    _ligado("chapeu", "chapeu")
    _a_conferir("generica", "sem_candidato")


def cen_09() -> None:
    """Empate pelo telefone resolvido pela palavra; o contrato sem palavra fica no empate."""
    _ligado("bela", "bela")
    _a_conferir("nautico", "empate")


def cen_10() -> None:
    """Ligado pela palavra, desligado à mão, não religa sozinho (FR-005)."""
    _ligado("desl", "desl")
    r = v._chamar(estado["comercial"], "post", f"/api/contratos/{_doc('desl')[0]}/desligar")
    _garante(r.status_code == 200, f"desligar → {r.status_code}")
    eid = estado["env"]["desl"]
    conta.mudar(eid, status="closed", quando=datetime.combine(estado["hoje"], time(16, 0)))
    v._sincronizar(desde=v._d(-1))
    d = _doc("desl")
    _garante(d[4] == "a_conferir" and d[6] == "desligado" and d[3] is None, f"religou: {d}")


def cen_11() -> None:
    """Repetir a passada não muda nada (idempotente com as regras novas)."""
    antes = {k: _doc(k)[3:7] for k in ("snoopy", "chapeu", "remarc", "mail", "canc", "canc_sem")}
    _sinc()
    depois = {k: _doc(k)[3:7] for k in antes}
    _garante(antes == depois, f"mudou na segunda passada: {antes} → {depois}")


CENARIOS = [
    ("1. núcleo: palavras do tema e venda única", cen_01),
    ("2. cancelado na ClickSign sem venda sai de A conferir", cen_02),
    ("3. venda cancelada certa liga, sem PDF no cancelado", cen_03),
    ("4. telefone a um dia; ambíguo fica (DEVE ficar)", cen_04),
    ("5. formulário ligado: festa remarcada", cen_05),
    ("6. e-mail no lugar do telefone", cen_06),
    ("7. tema por palavra; duas com a palavra ficam (DEVE ficar)", cen_07),
    ("8. dia vazio procura ao lado; genérico nunca liga (DEVE ficar)", cen_08),
    ("9. empate resolvido pela palavra", cen_09),
    ("10. desligado à mão não religa", cen_10),
    ("11. segunda passada idempotente", cen_11),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        v.limpar()
        preparar()
    print("Correção 317b — sinais novos do vínculo, contra manto_local")
    try:
        for nome, fn in CENARIOS:
            v.cenario(nome, fn)
    finally:
        with app.app_context():
            v.cenario("12. limpeza", v.limpar)
    ok = sum(1 for _, passou, _ in _resultados if passou)
    print(f"\n{ok}/{len(_resultados)} OK · escapes de rede: {len(v._ESCAPES)}")
    for nome, passou, erro in _resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(_resultados) else 1


if __name__ == "__main__":
    sys.exit(main())

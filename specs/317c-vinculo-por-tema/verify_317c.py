"""Verificação da correção 317c — palavra de ocasião não liga, e o vínculo fraco cede ao telefone.

Reaproveita o dublê da ClickSign, o disjuntor de rede, a semeadura e a limpeza do `verify_317.py`
(importado como módulo — a ClickSign nunca é chamada), como o `verify_317b.py`. As datas ficam em 2028
(e uma em 2001, para o evento que já passou): a regra do tema olha TODAS as vendas do dia, então um dia
vazio no espelho é o único jeito de o resultado não depender dele.

Rodar contra o espelho da correção (PowerShell, a partir do worktree)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"; $env:MANTO_SEM_THREADS = "1"
    C:/Users/schim/Desktop/Manto_Platform/.venv/Scripts/python.exe specs/317c-vinculo-por-tema/verify_317c.py
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

_CAMINHO_317 = Path(__file__).resolve().parents[1] / "317-contratos-clicksign" / "verify_317.py"
_spec = importlib.util.spec_from_file_location("verify_317", _CAMINHO_317)
v = importlib.util.module_from_spec(_spec)
sys.modules["verify_317"] = v
_spec.loader.exec_module(v)

app, db, conta, estado = v.app, v.db, v.conta, v.estado
_garante, _doc, _evento, _nome_festa = v._garante, v._doc, v._evento, v._nome_festa
BASE = date(2028, 5, 2)
PASSADO = date(2001, 3, 1)
_resultados: list[tuple[str, bool, str]] = v.resultados


def _dia(n: int) -> date:
    return BASE + timedelta(days=n)


def _fone(n: int) -> str:
    return f"551190002{n:04d}"


def _sinc(**kw) -> dict:
    return v._sincronizar(desde=v._d(-30), **kw)


def _ligado(chave: str, venda: str, origem: str = "auto") -> None:
    d = _doc(chave)
    _garante(
        d is not None and d[4] == "ligado" and d[5] == origem and d[3] == estado["ids"][venda],
        f"{chave} deveria estar ligado ({origem}) em {venda}={estado['ids'][venda]}: {d}",
    )


def _a_conferir(chave: str, motivo: str) -> None:
    d = _doc(chave)
    _garante(
        d is not None and d[4] == "a_conferir" and d[3] is None and d[6] == motivo,
        f"{chave} deveria ficar a conferir ({motivo}): {d}",
    )


def _dar_telefone(venda: str, telefone: str) -> None:
    """A venda ganha a cliente depois: é o que acontece quando o formulário ou a ficha chega tarde."""
    from app.models import CalendarEvent, Client, EventClient

    with app.app_context():
        evento = db.session.get(CalendarEvent, estado["ids"][venda])
        cliente = Client.query.filter_by(phone=telefone).first()
        if cliente is None:
            cliente = Client(
                name=f"{v.PREFIX}{venda}",
                phone=telefone,
                phone_display=f"+{telefone}",
                source="manual",
            )
            db.session.add(cliente)
            db.session.flush()
        db.session.add(
            EventClient(event_id=evento.id, client_id=cliente.id, relationship_type="Contratante")
        )
        evento.client_id = cliente.id
        db.session.commit()


def _historico(venda: str, trecho: str) -> int:
    return v._no_banco(
        "SELECT count(*) FROM event_logs WHERE event_id = :e AND message LIKE :m",
        e=estado["ids"][venda],
        m=f"%{trecho}%",
    )[0]


def preparar() -> None:
    from app.constants import RoleName, now_sp
    from app.models import SiteSetting

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

    # Palavra de ocasião: a única venda do dia com a palavra é de outra cliente.
    _evento("corp_natal", _dia(0), titulo="(CORP) NATAL THERMAS")
    _evento("noel", _dia(2), titulo="(VM) PAPAI NOEL + AJUDANTE DO NOEL")
    # Palavra que diz a festa: continua ligando.
    _evento("snoopy", _dia(4), titulo="(R&I) SNOOPY + CHARLIE")
    _evento("mickey4", _dia(4), titulo="(R&I) MICKEY CLASSICO + MINNIE CLASSICO")
    # O vínculo fraco cede: a venda certa ganha o telefone depois.
    _evento("raya_errada", _dia(6), titulo="(R&I) RAYA + AURORA")
    _evento("raya_certa", _dia(6), titulo="(VM) VISITA SURPRESA")
    # Ligado à mão não muda.
    _evento("man_a", _dia(8), titulo="(R&I) BLUEY")
    _evento("man_b", _dia(8), titulo="(R&I) BINGO")
    # Data + telefone com outra venda do mesmo telefone no dia: não muda.
    _evento("forte_a", _dia(10), telefone=_fone(6), titulo="(R&I) BELA + FERA + GASTON")
    _evento("forte_b", _dia(10), telefone=_fone(6), titulo="(R&I) MICKEY MARINHEIRO")
    # Duas vendas passam a ter o telefone: ambíguo, não mexe.
    _evento("amb_errada", _dia(12), titulo="(R&I) MOANA + MAUI")
    _evento("amb_x", _dia(12), titulo="(R&I) LEGO")
    _evento("amb_y", _dia(12), titulo="(R&I) BARBIE")
    # Evento que já passou: não é mexido.
    _evento("velho_errado", PASSADO, titulo="(R&I) TIANA + NAVEEN")
    _evento("velho_certo", PASSADO, titulo="(VM) VISITA ANTIGA")
    db.session.commit()

    env = estado["env"]
    env["natal"] = conta.envelope("c_natal", _nome_festa(_dia(0), _fone(1), "Natal"))
    env["noel"] = conta.envelope("c_noel", _nome_festa(_dia(2), _fone(2), "Papai Noel"))
    env["snoopy"] = conta.envelope(
        "c_snoopy", _nome_festa(_dia(4), _fone(3), "Arraiá com o Snoopy")
    )
    env["raya"] = conta.envelope(
        "c_raya", _nome_festa(_dia(6), _fone(4), "Raya é o último dragão"), status="closed"
    )
    env["man"] = conta.envelope("c_man", _nome_festa(_dia(8), _fone(5), "Dinossauros"))
    env["forte"] = conta.envelope("c_forte", _nome_festa(_dia(10), _fone(6), "Bela e a Fera"))
    env["amb"] = conta.envelope("c_amb", _nome_festa(_dia(12), _fone(7), "Moana"))
    env["velho"] = conta.envelope("c_velho", _nome_festa(PASSADO, _fone(8), "Tiana"))


# ── Cenários ─────────────────────────────────────────────────────────────────────────────────────


def cen_01() -> None:
    """Núcleo puro: palavra de ocasião não diz a festa; a palavra do tema continua dizendo."""
    from app.contratos.contratos_ops import Candidato, palavras_do_tema, tema_por_palavra

    for ocasiao in (
        "Natal",
        "Papai Noel",
        "Natal das Crianças",
        "Páscoa",
        "Festa Junina",
        "Halloween",
    ):
        _garante(palavras_do_tema(ocasiao) == set(), f"{ocasiao!r} → {palavras_do_tema(ocasiao)}")
    thermas = [Candidato(1, ("(CORP) NATAL THERMAS",))]
    _garante(tema_por_palavra("Natal", thermas) is None, "'Natal' ligou no corporativo")
    visita = [Candidato(1, ("(VM) PAPAI NOEL + AJUDANTE DO NOEL",))]
    _garante(tema_por_palavra("Papai Noel", visita) is None, "'Papai Noel' ligou pela palavra")
    _garante(
        palavras_do_tema("Arraiá com o Snoopy") == {"arraia", "snoopy"}, "Snoopy perdeu a palavra"
    )
    _garante(
        tema_por_palavra("Natal do Snoopy", [Candidato(7, ("(R&I) SNOOPY + CHARLIE",))]) == 7,
        "tema com ocasião + personagem deveria ligar pelo personagem",
    )


def cen_02() -> None:
    """'Natal' com um corporativo NATAL de outra cliente no dia: a conferir (DEVE ficar)."""
    _sinc()
    _a_conferir("natal", "sem_candidato")


def cen_03() -> None:
    """'Papai Noel' com uma só visita de Papai Noel sem telefone no dia: a conferir (DEVE ficar)."""
    _a_conferir("noel", "sem_candidato")


def cen_04() -> None:
    """A palavra que diz a festa continua ligando; data + telefone e o empate pela palavra também."""
    _ligado("snoopy", "snoopy")
    _ligado("forte", "forte_a")


def cen_05() -> None:
    """Ligado pela palavra; a venda certa ganha o telefone: a simulação conta e não grava."""
    _ligado("raya", "raya_errada")
    _garante(v._anexos("raya_errada") == 1, "o PDF assinado deveria estar na venda da palavra")
    _dar_telefone("raya_certa", _fone(4))
    resultado = _sinc(aplicar=False)
    _garante(
        resultado.get("movidos") == 1, f"a simulação deveria contar 1 vínculo a passar: {resultado}"
    )
    _ligado("raya", "raya_errada")


def cen_06() -> None:
    """A passada seguinte passa o vínculo para a venda do telefone, com o PDF e o histórico das duas."""
    resultado = _sinc()
    _garante(resultado.get("movidos") == 1, f"deveria passar 1 vínculo: {resultado}")
    _ligado("raya", "raya_certa")
    _garante(v._anexos("raya_errada") == 0, "o PDF ficou na venda errada")
    _garante(v._anexos("raya_certa") == 1, "o PDF não chegou à venda certa")
    _garante(
        _historico("raya_errada", "Passou o contrato") == 1, "sem histórico na venda de origem"
    )
    _garante(_historico("raya_certa", "Ligou o contrato") == 1, "sem histórico na venda de destino")


def cen_07() -> None:
    """Ligado à mão não muda, mesmo com outra venda ganhando o telefone (FR-005 da 317) (DEVE ficar)."""
    _a_conferir("man", "sem_candidato")
    r = v._chamar(
        estado["comercial"],
        "post",
        f"/api/contratos/{_doc('man')[0]}/ligar",
        {"event_id": estado["ids"]["man_a"]},
    )
    _garante(r.status_code == 200, f"ligar → {r.status_code}")
    _dar_telefone("man_b", _fone(5))
    _sinc()
    _ligado("man", "man_a", origem="manual")


def cen_08() -> None:
    """Duas vendas com o telefone do contrato no dia: ambíguo, o vínculo fica onde está (DEVE ficar)."""
    _ligado("amb", "amb_errada")
    _dar_telefone("amb_x", _fone(7))
    _dar_telefone("amb_y", _fone(7))
    resultado = _sinc()
    _garante(resultado.get("movidos") == 0, f"passou vínculo ambíguo: {resultado}")
    _ligado("amb", "amb_errada")


def cen_09() -> None:
    """Contrato de evento que já passou não é reavaliado (DEVE ficar)."""
    _ligado("velho", "velho_errado")
    _dar_telefone("velho_certo", _fone(8))
    _sinc()
    _ligado("velho", "velho_errado")


def cen_10() -> None:
    """Repetir a passada não muda nada, e o vínculo de data + telefone não se mexe."""
    chaves = ("natal", "noel", "snoopy", "raya", "man", "forte", "amb", "velho")
    antes = {k: _doc(k)[3:7] for k in chaves}
    resultado = _sinc()
    _garante(resultado.get("movidos") == 0, f"segunda passada passou vínculo: {resultado}")
    depois = {k: _doc(k)[3:7] for k in chaves}
    _garante(antes == depois, f"mudou na segunda passada: {antes} → {depois}")
    _ligado("forte", "forte_a")


CENARIOS = [
    ("1. núcleo: palavra de ocasião não diz a festa", cen_01),
    ("2. 'Natal' não liga no corporativo de outra cliente (DEVE ficar)", cen_02),
    ("3. 'Papai Noel' não liga pela palavra (DEVE ficar)", cen_03),
    ("4. a palavra do tema e data + telefone continuam ligando", cen_04),
    ("5. vínculo fraco com venda certa: a simulação conta e não grava", cen_05),
    ("6. vínculo fraco cede ao telefone, com PDF e histórico", cen_06),
    ("7. ligado à mão não muda (DEVE ficar)", cen_07),
    ("8. dois telefones no dia: ambíguo não mexe (DEVE ficar)", cen_08),
    ("9. evento que já passou não é reavaliado (DEVE ficar)", cen_09),
    ("10. segunda passada idempotente", cen_10),
]


def main() -> int:
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "MAIL_SUPPRESS_SEND desligado")
        v.limpar()
        preparar()
    print("Correção 317c — palavra de ocasião e vínculo fraco, contra o espelho da correção")
    try:
        for nome, fn in CENARIOS:
            v.cenario(nome, fn)
    finally:
        with app.app_context():
            v.cenario("11. limpeza", v.limpar)
    ok = sum(1 for _, passou, _ in _resultados if passou)
    print(f"\n{ok}/{len(_resultados)} OK · escapes de rede: {len(v._ESCAPES)}")
    for nome, passou, erro in _resultados:
        if not passou:
            print(f"  - {nome}: {erro}")
    return 0 if ok == len(_resultados) else 1


if __name__ == "__main__":
    sys.exit(main())

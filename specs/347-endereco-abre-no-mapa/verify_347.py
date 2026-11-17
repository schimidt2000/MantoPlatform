"""Verificação da 347 — tocar no endereço do evento e escolher o app de mapas.

Cenários (spec.md, "Verificação"):
 1. Endereço com acento, vírgula e número → três opções, na ordem Google Maps, Apple Mapas, Waze,
    com as URLs exatas de `research.md` R1.
 2. "&", "#", "/" e espaços nas pontas → codificados e aparados (FR-009).
 3. Vazio, só espaços, `null`, `undefined` → nenhuma opção (FR-008).
 4. DEVE FALHAR: um montador ingênuo, sem codificação, passado pela mesma checagem é reprovado —
    prova que a checagem dos cenários 1 e 2 tem dente.
 5. `EnderecoNoMapa` exportado em `@manto/ui` e usado com o endereço nas quatro telas; o texto
    puro de antes não sobrou em nenhuma.
 6. `manto_local`, só leitura: o detalhe do evento (`GET /api/events/<id>`) e a agenda do portal
    (`portal_ops.get_agenda`) entregam `location` igual ao gravado no evento — a dependência que o
    data-model assume.
 7. Limpeza (apaga o usuário do verify).

A montagem dos links é TypeScript (`frontend/packages/ui/src/lib/mapas.ts`): o verify a transpila
com o `esbuild` de `frontend/node_modules` e roda no `node`, sem rede. Não semeia evento nem
escala; o único registro escrito é o usuário descartável do login.

Rodar (PowerShell; aqui contra o espelho `manto_347`, dump de 17/11 02h, porque o `manto_local` diz
estar na head mas não tem a coluna `site_settings.meta_pixel_id` da 344 — ver plan.md)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim() -replace '/manto_local$', '/manto_347'
    $env:FLASK_ENV = "development"
    $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"
    .\\.venv\\Scripts\\python.exe specs\\347-endereco-abre-no-mapa\\verify_347.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend"
sys.path.insert(0, str(REPO_ROOT))
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("MANTO_SEM_THREADS", "1")
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = (REPO_ROOT / ".local-db-url").read_text(encoding="utf-8").strip()

from sqlalchemy import create_engine, text  # noqa: E402

from app import create_app, db  # noqa: E402
from app.constants import RoleName  # noqa: E402
from app.models import Role, Talent, User  # noqa: E402
from app.talent_portal import portal_ops  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

PREFIX = "__v347_"
SENHA = "verify-347-senha"
INDEFINIDO = "__undefined__"  # JSON não tem `undefined`; o harness do node traduz este marcador

# O contrato, escrito de novo aqui de propósito: se `mapas.ts` mudar a URL, o verify acusa.
ROTULOS = ["Google Maps", "Apple Mapas", "Waze"]
APPS = ["google", "apple", "waze"]
BASES = [
    "https://www.google.com/maps/search/?api=1&query=",
    "https://maps.apple.com/?q=",
    "https://waze.com/ul?q=",
]

# As quatro telas: (arquivo, trecho que tem de existir, trecho de antes que não pode sobrar).
TELAS = [
    (
        "apps/internal/src/components/EventDetail/EventHeader.tsx",
        "<EnderecoNoMapa endereco={event.location}",
        "<span>• {event.location}</span>",
    ),
    (
        "apps/internal/src/components/EventDetail/ResumoSection.tsx",
        "<EnderecoNoMapa endereco={event.location}",
        '<DataRow label="Local">{event.location || "—"}</DataRow>',
    ),
    (
        "apps/portal/src/pages/PortalAgendaPage.tsx",
        "<EnderecoNoMapa",
        '{role.location ? ` · ${role.location}` : ""}',
    ),
    (
        "apps/portal/src/pages/PortalConvitesPage.tsx",
        "<EnderecoNoMapa",
        '<p className="text-sm text-muted">{role.location}</p>',
    ),
]

# Harness: transpila `mapas.ts` (sem imports) e devolve `linksDeMapa(x)` para cada entrada.
_HARNESS_NODE = r"""
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
const require = createRequire(process.cwd() + "/package.json");
const esbuild = require("esbuild");
const fonte = readFileSync("packages/ui/src/lib/mapas.ts", "utf8");
const { code } = esbuild.transformSync(fonte, { loader: "ts", format: "esm" });
const mod = await import("data:text/javascript;base64," + Buffer.from(code).toString("base64"));
const entradas = JSON.parse(readFileSync(0, "utf8"));
const saida = entradas.map((e) => mod.linksDeMapa(e === "__undefined__" ? undefined : e));
process.stdout.write(JSON.stringify(saida));
"""

app = create_app()
app.config["TESTING"] = True
app.config["RATELIMIT_ENABLED"] = False

_engine_externo = create_engine(os.environ["DATABASE_URL"])

resultados: list[tuple[str, bool, str]] = []
estado: dict = {}


def cenario(nome: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        resultados.append((nome, True, ""))
        print(f"  OK     {nome}")
    except Exception as exc:  # noqa: BLE001 — o verify reporta e segue para o próximo cenário
        with app.app_context():
            db.session.rollback()
        resultados.append((nome, False, traceback.format_exc().strip().splitlines()[-1]))
        print(f"  FALHA  {nome}: {exc}")


def _garante(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _links(entradas: list[str | None]) -> list[list[dict]]:
    """Roda `linksDeMapa` de verdade (o TypeScript da feature) para cada entrada."""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", _HARNESS_NODE],
        cwd=FRONTEND,
        input=json.dumps(entradas),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    _garante(proc.returncode == 0, f"node falhou: {proc.stderr.strip()[-400:]}")
    return json.loads(proc.stdout)


def _encode_uri_component(valor: str) -> str:
    # Mesmo conjunto que o `encodeURIComponent` do JavaScript deixa sem codificar.
    return quote(valor, safe="-_.!~*'()")


def _checa_opcoes(endereco: str, opcoes: list[dict]) -> None:
    """As três opções, na ordem, com a URL exata do contrato para este endereço."""
    _garante(len(opcoes) == 3, f"{len(opcoes)} opções para {endereco!r}")
    q = _encode_uri_component(endereco.strip())
    for i, opcao in enumerate(opcoes):
        _garante(opcao.get("app") == APPS[i], f"opção {i}: app {opcao.get('app')!r}")
        _garante(opcao.get("rotulo") == ROTULOS[i], f"opção {i}: rótulo {opcao.get('rotulo')!r}")
        esperado = BASES[i] + q
        _garante(opcao.get("url") == esperado, f"{ROTULOS[i]}: {opcao.get('url')!r} ≠ {esperado!r}")


# ── preparo e limpeza ───────────────────────────────────────────────────────────────────────────
def preparar() -> None:
    with app.app_context():
        limpar()
        email = f"{PREFIX}superadmin@manto.local"
        user = User(name=f"{PREFIX}superadmin", email=email, is_active=True, has_access=True)
        user.set_password(SENHA)
        user.roles.append(Role.query.filter_by(name=RoleName.SUPERADMIN).one())
        db.session.add(user)
        db.session.commit()
        estado["email"] = email
    # Um evento com endereço e um talento escalado nele (convite não recusado), do mais recente
    # para trás: o mais provável de aparecer em "Próximos eventos". Lido por conexão separada.
    with _engine_externo.connect() as conn:
        linha = conn.execute(
            text(
                """
                SELECT e.id AS event_id, e.location, r.talent_id
                FROM calendar_events e JOIN event_roles r ON r.event_id = e.id
                WHERE e.location IS NOT NULL AND btrim(e.location) <> ''
                  AND e.cancelled_at IS NULL AND r.talent_id IS NOT NULL
                  AND (r.invite_status IS NULL OR r.invite_status <> 'rejected')
                ORDER BY e.start_at DESC
                LIMIT 1
                """
            )
        ).first()
    _garante(linha is not None, "o espelho não tem evento com endereço e talento escalado")
    estado["evento"] = linha


def limpar() -> None:
    db.session.rollback()
    for u in User.query.filter(User.email.like(f"{PREFIX}%")).all():
        u.roles.clear()
        db.session.delete(u)
    db.session.commit()


# ── cenários ────────────────────────────────────────────────────────────────────────────────────
def cen_01_endereco_comum() -> None:
    endereco = "Rua Avanhandava, 126 - Bela Vista, São Paulo - SP, 01306-000"
    _checa_opcoes(endereco, _links([endereco])[0])


def cen_02_simbolos_e_pontas() -> None:
    endereco = "  Buffet A&B #2 / Moema — nº 45?x=1  "
    opcoes = _links([endereco])[0]
    _checa_opcoes(endereco, opcoes)
    google = opcoes[0]["url"]
    _garante("%26" in google and "%23" in google and "%2F" in google, f"símbolo cru em {google}")
    _garante("%20%20" not in google and not google.endswith("%20"), "pontas não aparadas")


def cen_03_sem_endereco() -> None:
    saidas = _links(["", "   ", None, INDEFINIDO])
    _garante(all(s == [] for s in saidas), f"esperado nenhuma opção, veio {saidas}")


def cen_04_ingenuo_reprovado() -> None:
    endereco = "Buffet A&B #2 / Moema"
    ingenuo = [{"app": APPS[i], "rotulo": ROTULOS[i], "url": BASES[i] + endereco} for i in range(3)]
    try:
        _checa_opcoes(endereco, ingenuo)
    except AssertionError:
        return  # reprovado, como deve
    raise AssertionError("a checagem aceitou um link sem codificação")


def cen_05_telas_usam_a_peca() -> None:
    indice = (FRONTEND / "packages/ui/src/index.ts").read_text(encoding="utf-8")
    _garante("EnderecoNoMapa" in indice, "EnderecoNoMapa não exportado em packages/ui/src/index.ts")
    _garante("linksDeMapa" in indice, "linksDeMapa não exportado em packages/ui/src/index.ts")
    for arquivo, novo, velho in TELAS:
        fonte = (FRONTEND / arquivo).read_text(encoding="utf-8")
        _garante(novo in fonte, f"{arquivo}: sem {novo!r}")
        _garante(velho not in fonte, f"{arquivo}: o texto puro de antes sobrou ({velho!r})")
        _garante("EnderecoNoMapa" in fonte.split('from "@manto/ui"')[0], f"{arquivo}: sem import")


def cen_06_endereco_chega_as_telas() -> None:
    ev = estado["evento"]
    c = app.test_client()
    r = c.post("/api/auth/login", json={"email": estado["email"], "password": SENHA})
    _garante(r.status_code == 200, f"login → {r.status_code}")
    r = c.get(f"/api/events/{ev.event_id}")
    _garante(r.status_code == 200, f"GET /api/events/{ev.event_id} → {r.status_code}")
    no_detalhe = r.get_json()["event"].get("location")
    _garante(no_detalhe == ev.location, f"detalhe: {no_detalhe!r} ≠ {ev.location!r}")
    with app.app_context():
        agenda = portal_ops.get_agenda(db.session.get(Talent, ev.talent_id))
    itens = agenda["pending_invites"] + agenda["upcoming"] + agenda["history"]
    do_evento = [i for i in itens if i["event_id"] == ev.event_id]
    _garante(do_evento, f"evento {ev.event_id} fora da agenda do talento {ev.talent_id}")
    _garante(
        all(i["location"] == ev.location for i in do_evento),
        f"portal: {[i['location'] for i in do_evento]} ≠ {ev.location!r}",
    )
    print(f"         (evento {ev.event_id}, talento {ev.talent_id})")


def cen_07_limpeza() -> None:
    with app.app_context():
        limpar()
        _garante(User.query.filter(User.email.like(f"{PREFIX}%")).count() == 0, "sobrou usuário")


def main() -> int:
    print("347 — endereço do evento abre no app de mapas")
    with app.app_context():
        _garante(app.config.get("MAIL_SUPPRESS_SEND") is True, "e-mail não está suprimido")
    preparar()
    try:
        cenario("1. endereço comum: 3 opções, URLs exatas", cen_01_endereco_comum)
        cenario("2. '&', '#', '/' codificados; pontas aparadas", cen_02_simbolos_e_pontas)
        cenario("3. sem endereço: nenhuma opção", cen_03_sem_endereco)
        cenario("4. DEVE FALHAR: montador ingênuo reprovado", cen_04_ingenuo_reprovado)
        cenario("5. peça exportada e usada nas quatro telas", cen_05_telas_usam_a_peca)
        cenario(
            "6. manto_local: endereço chega ao detalhe e ao portal", cen_06_endereco_chega_as_telas
        )
    finally:
        cenario("7. limpeza", cen_07_limpeza)
    ok = sum(1 for _, passou, _ in resultados if passou)
    print(f"{ok}/{len(resultados)} OK")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())

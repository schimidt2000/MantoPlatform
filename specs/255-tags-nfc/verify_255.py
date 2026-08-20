"""Verificação da feature 255 — Tags NFC das peças 3D com página pública por código.

Cenários (quickstart.md da spec):
1. Habilitar `nfc_prefix` num item do acervo via PATCH (normalização p/ maiúsculas).
2. Presente 3D (qty 2) em evento SHOW → 2 tags automáticas `01-XXXXXX`, sequence 1 e 2.
3. Aumentar qty p/ 3 → +1 tag; reduzir p/ 1 → continua 3 (nunca apaga).
4. Lote avulso (qty 2) sem evento → sequence continua do ponto onde parou.
5. Associar evento via PATCH → `client_name` do contratante aparece na lista.
6. GET /api/nfc/<code> SEM login → 200 com produto + campaign null; access_count incrementa.
7. Desativar → payload genérico; código inventado → payload idêntico (SC-006); RBAC do admin.
8. Item sem prefixo → presente não gera tag nenhuma (não-regressão).
9. Limpeza total dos registros de teste.

Rodar contra o manto_local (PowerShell)::

    $env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
    .venv/Scripts/python.exe specs/255-tags-nfc/verify_255.py

O evento de teste é criado DIRETO no banco (nunca pela API de eventos — ela sincroniza com o
Google Calendar de verdade; ver memória do projeto sobre o espelho ter credenciais reais).
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

os.environ.setdefault("FLASK_ENV", "development")
if not os.environ.get("DATABASE_URL"):
    _url_file = os.path.join(os.path.dirname(__file__), "..", "..", ".local-db-url")
    with open(_url_file, encoding="utf-8") as fh:
        os.environ["DATABASE_URL"] = fh.read().strip()

from app import create_app, db  # noqa: E402
from app.models import (  # noqa: E402
    Acervo3DFile,
    Acervo3DItem,
    CalendarEvent,
    Client,
    Event3DGift,
    EventClient,
    NfcTag,
    Role,
    User,
)

MARKER = "__v255"
EMAIL = "__v255@manto.local"
PW = "verify-255-senha"
passed = 0
total = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global passed, total
    total += 1
    passed += 1 if cond else 0
    print(f"  [{'OK ' if cond else 'FALHA'}] {label}{f' — {detail}' if detail else ''}")


def limpar(app) -> None:
    with app.app_context():
        item_ids = [
            i.id for i in Acervo3DItem.query.filter(Acervo3DItem.name.like(f"%{MARKER}%")).all()
        ]
        if item_ids:
            NfcTag.query.filter(NfcTag.item_id.in_(item_ids)).delete(synchronize_session=False)
            Event3DGift.query.filter(Event3DGift.item_id.in_(item_ids)).delete(
                synchronize_session=False
            )
            Acervo3DItem.query.filter(Acervo3DItem.id.in_(item_ids)).delete(
                synchronize_session=False
            )
        for ev in CalendarEvent.query.filter(CalendarEvent.title.like(f"%{MARKER}%")).all():
            EventClient.query.filter_by(event_id=ev.id).delete()
            db.session.delete(ev)
        for cl in Client.query.filter(Client.name.like(f"%{MARKER}%")).all():
            db.session.delete(cl)
        for u in User.query.filter_by(email=EMAIL).all():
            u.roles.clear()
            db.session.delete(u)
        db.session.commit()


app = create_app()
limpar(app)

with app.app_context():
    u = User(email=EMAIL, name="V255", has_access=True, must_change_password=False)
    u.set_password(PW)
    u.roles.append(Role.query.filter_by(name="SUPERADMIN").first())
    db.session.add(u)

    item = Acervo3DItem(name=f"Luminaria {MARKER}", photo_url="/uploads/acervo_3d_photos/v255.jpg")
    item_sem_nfc = Acervo3DItem(name=f"Chaveiro {MARKER}", photo_url="/uploads/acervo_3d_photos/v255b.jpg")
    cliente = Client(name=f"Cliente {MARKER}", phone="999255000001")
    db.session.add_all([item, item_sem_nfc, cliente])
    db.session.flush()
    # Peça sem arquivo 3D não existe na regra de negócio — o PATCH do acervo valida isso.
    db.session.add_all([
        Acervo3DFile(item_id=item.id, file_path="/uploads/acervo_3d_files/v255.stl", position=0),
        Acervo3DFile(item_id=item_sem_nfc.id, file_path="/uploads/acervo_3d_files/v255b.stl", position=0),
    ])

    ev = CalendarEvent(
        title=f"(SHOW) Festa {MARKER}", event_type="SHOW",
        google_event_id=f"{MARKER}-fake-g1",
        start_at=datetime.utcnow() + timedelta(days=30),
        end_at=datetime.utcnow() + timedelta(days=30, hours=2),
    )
    ev2 = CalendarEvent(
        title=f"(SHOW) Festa 2 {MARKER}", event_type="SHOW",
        google_event_id=f"{MARKER}-fake-g2",
        start_at=datetime.utcnow() + timedelta(days=45),
        end_at=datetime.utcnow() + timedelta(days=45, hours=2),
    )
    db.session.add_all([ev, ev2])
    db.session.flush()
    db.session.add(EventClient(event_id=ev2.id, client_id=cliente.id, relationship_type="Contratante"))
    db.session.commit()
    item_id, item2_id, event_id, event2_id = item.id, item_sem_nfc.id, ev.id, ev2.id
    cliente_nome = cliente.name

c = app.test_client()
r = c.post("/api/auth/login", json={"email": EMAIL, "password": PW})
print(f"login: {r.status_code}")

print("\n=== 1. Habilitar prefixo NFC no item do acervo ===")
r = c.patch(f"/api/3d/acervo/{item_id}", data={"nfc_prefix": " 01 "})
body = r.get_json() or {}
check("PATCH aceita nfc_prefix", r.status_code == 200, f"status={r.status_code}")
check("serialize devolve prefixo normalizado '01'", body.get("nfc_prefix") == "01",
      f"nfc_prefix={body.get('nfc_prefix')!r}")

print("\n=== 2. Presente 3D (qty 2) gera 2 tags automaticas ===")
r = c.post(f"/api/events/{event_id}/3d-gifts", json={"item_id": item_id, "quantity": 2})
check("cria presente 201", r.status_code == 201, f"status={r.status_code}")
gift_id = (r.get_json() or {}).get("id")
with app.app_context():
    tags = NfcTag.query.filter_by(item_id=item_id).order_by(NfcTag.sequence).all()
    check("2 tags criadas e associadas ao evento", len(tags) == 2
          and all(t.event_id == event_id for t in tags), f"n={len(tags)}")
    check("codigos no formato 01-XXXXXX sem ambiguidade",
          bool(tags) and all(re.fullmatch(r"01-[A-HJ-NP-Z2-9]{6}", t.code) for t in tags),
          ", ".join(t.code for t in tags))
    check("sequence humana 1 e 2", [t.sequence for t in tags] == [1, 2])
    check("codigos unicos", len({t.code for t in tags}) == len(tags))

print("\n=== 3. Aumentar quantidade completa; reduzir nunca apaga ===")
r = c.patch(f"/api/events/{event_id}/3d-gifts/{gift_id}", json={"quantity": 3})
check("PATCH qty 3", r.status_code == 200, f"status={r.status_code}")
with app.app_context():
    n = NfcTag.query.filter_by(item_id=item_id).count()
    check("3 tags apos aumentar", n == 3, f"n={n}")
r = c.patch(f"/api/events/{event_id}/3d-gifts/{gift_id}", json={"quantity": 1})
with app.app_context():
    n = NfcTag.query.filter_by(item_id=item_id).count()
    check("continua 3 apos reduzir para 1", n == 3, f"n={n}")

print("\n=== 4. Lote avulso sem evento, sequence continua ===")
r = c.post("/api/3d/nfc/lote", json={"item_id": item_id, "quantity": 2})
body = r.get_json() or {}
lote = body.get("tags") or []
check("lote 200 com 2 tags", r.status_code == 200 and len(lote) == 2, f"status={r.status_code}")
check("tags do lote sem evento", all(t.get("event") is None for t in lote))
check("sequence continua (4 e 5)", [t.get("sequence") for t in lote] == [4, 5],
      f"seqs={[t.get('sequence') for t in lote]}")
tag_avulsa_id = lote[0].get("id") if lote else None
tag_avulsa_code = lote[0].get("code") if lote else ""

print("\n=== 5. Associar evento e ver o cliente na lista ===")
r = c.patch(f"/api/3d/nfc/{tag_avulsa_id}", json={"event_id": event2_id})
check("PATCH associa evento", r.status_code == 200, f"status={r.status_code}")
r = c.get("/api/3d/nfc")
rows = (r.get_json() or {}).get("tags") or []
linha = next((t for t in rows if t.get("id") == tag_avulsa_id), {})
check("lista 200 com as 5 tags do item de teste",
      r.status_code == 200 and sum(1 for t in rows if (t.get("item") or {}).get("id") == item_id) == 5,
      f"status={r.status_code}")
check("client_name do contratante na linha", linha.get("client_name") == cliente_nome,
      f"client_name={linha.get('client_name')!r}")
r = c.patch(f"/api/3d/nfc/{tag_avulsa_id}", json={"event_id": None})
check("PATCH desassocia (event_id null)", r.status_code == 200
      and (r.get_json() or {}).get("tag", {}).get("event") is None)

print("\n=== 6. Pagina publica resolve SEM login ===")
anon = app.test_client()  # sem cookie de sessao
r = anon.get(f"/api/nfc/{tag_avulsa_code}")
body = r.get_json() or {}
check("200 sem login", r.status_code == 200, f"status={r.status_code}")
check("produto no payload", (body.get("product") or {}).get("name") == f"Luminaria {MARKER}")
check("campaign e o gancho null", body.get("campaign") is None and "campaign" in body)
check("instagram_url presente", bool(body.get("instagram_url")))
r = anon.get(f"/api/nfc/{tag_avulsa_code.lower()}")
check("lookup case-insensitive", r.status_code == 200
      and (r.get_json() or {}).get("product") is not None)
with app.app_context():
    t = db.session.get(NfcTag, tag_avulsa_id) if tag_avulsa_id else None
    check("access_count incrementou (2 acessos)", t is not None and t.access_count == 2,
          f"count={t.access_count if t else None}")
    check("last_accessed_at registrado", t is not None and t.last_accessed_at is not None)

print("\n=== 7. Desativada e inexistente sao indistinguiveis; RBAC ===")
r = c.patch(f"/api/3d/nfc/{tag_avulsa_id}", json={"is_active": False})
check("PATCH desativa", r.status_code == 200, f"status={r.status_code}")
r1 = anon.get(f"/api/nfc/{tag_avulsa_code}")
r2 = anon.get("/api/nfc/01-QQQQQQ")
b1, b2 = r1.get_json() or {}, r2.get_json() or {}
check("desativada → product null, 200", r1.status_code == 200 and b1.get("product") is None)
check("inexistente → MESMO shape (SC-006)", r2.status_code == 200
      and set(b1.keys()) == set(b2.keys()) and b2.get("product") is None)
r = c.patch(f"/api/3d/nfc/{tag_avulsa_id}", json={"is_active": True})
check("reativar restaura", r.status_code == 200
      and (anon.get(f"/api/nfc/{tag_avulsa_code}").get_json() or {}).get("product") is not None)
r = anon.get("/api/3d/nfc")
check("lista admin exige login (401)", r.status_code == 401, f"status={r.status_code}")
r = anon.post("/api/3d/nfc/lote", json={"item_id": item_id, "quantity": 1})
check("lote exige login (401)", r.status_code == 401, f"status={r.status_code}")

print("\n=== 8. Item sem prefixo nao gera tag ===")
r = c.post(f"/api/events/{event_id}/3d-gifts", json={"item_id": item2_id, "quantity": 2})
check("presente de item comum cria 201", r.status_code == 201, f"status={r.status_code}")
with app.app_context():
    n = NfcTag.query.filter_by(item_id=item2_id).count()
    check("zero tags para item sem nfc_prefix", n == 0, f"n={n}")
r = c.post("/api/3d/nfc/lote", json={"item_id": item2_id, "quantity": 1})
body = r.get_json() or {}
check("lote de item sem prefixo → 400 com campo", r.status_code == 400
      and "item_id" in ((body.get("error") or {}).get("fields") or {}), f"status={r.status_code}")

print("\n=== 9. Limpeza ===")
limpar(app)
with app.app_context():
    sobras = (
        NfcTag.query.join(Acervo3DItem).filter(Acervo3DItem.name.like(f"%{MARKER}%")).count()
        + Acervo3DItem.query.filter(Acervo3DItem.name.like(f"%{MARKER}%")).count()
        + CalendarEvent.query.filter(CalendarEvent.title.like(f"%{MARKER}%")).count()
    )
    check("nenhum registro de teste sobrou", sobras == 0, f"sobras={sobras}")

print(f"\n{passed}/{total} passaram")
sys.exit(0 if passed == total else 1)

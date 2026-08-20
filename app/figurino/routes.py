"""Fichas de figurino para impressão — o único Jinja que a plataforma React abre de propósito.

O Banco de Figurinos é React (`FigurinoListPage`, `/api/figurino`). O que sobrou aqui são as duas
rotas de IMPRESSÃO, e elas ficam porque a interface nova linka para cá: `FigurinoListPage.tsx` e
`FigurinoSection.tsx` abrem estas URLs em nova aba. São também as únicas do Jinja que o
`frontend/server.js` repassa por regex (`^/figurinos/\\d+/print` e `^/figurinos/print-event/\\d+`),
restrita ao sub-path de propósito: `/figurinos` puro é rota do React Router, e um proxy amplo
roubaria o deep link.

Saíram na fase 3 da remoção do Jinja as telas de listagem, criação, edição, rotação/remoção de foto
e exclusão — todas com equivalente na SPA — e o importador de fichas do Google Drive
(`/figurinos/sync-drive`), que o dono confirmou ter rodado uma vez só, na migração, e que não volta
a ser usado. Foram junto as ~160 linhas do parser de Google Docs que só ele chamava.

`drive_service.normalize_name` continua em uso: é o que casa dois cargos escritos diferente
("Assistente do Transformers" / "…Transformes") como o mesmo personagem na impressão do evento.
"""

from flask import Blueprint, render_template
from flask_login import login_required

from app.models import FigurinoSheet

figurino_bp = Blueprint("figurino", __name__)


@figurino_bp.route("/figurinos/<int:sheet_id>/print")
@login_required
def print_sheet(sheet_id: int):
    sheet = FigurinoSheet.query.get_or_404(sheet_id)
    items = [{"sheet": sheet, "pieces": sheet.pieces_list, "role": None, "talent": None}]
    return render_template("figurino_print.html", items=items, event=None,
                           title=f"Ficha: {sheet.character_name}")


@figurino_bp.route("/figurinos/print-event/<int:event_id>")
@login_required
def print_event_figurinos(event_id: int):
    """Uma folha A4 por ESCALAÇÃO (personagem × quem veste) do evento.

    Por personagem não basta: a folha imprime o nome e as medidas do talento
    (`figurino_print.html`), então dois talentos no mesmo personagem são duas folhas —
    dois "Soldado" saíam como uma, com as medidas de só um deles.

    A identidade do personagem é a FICHA quando ela existe: dois cargos com nomes
    digitados diferentes ("Assistente do Transformers" / "…Transformes") apontando para
    a mesma ficha são o mesmo personagem. Sem ficha, vale o nome normalizado.

    O que continua deduplicado, para não voltarem as folhas inúteis de antes:

    - Cargos ``role_type == "extra"`` (transporte, maquiador, presença…) ficam de fora —
      mesmo filtro do painel de Figurino. Cada extra virava uma folha vazia "Sem ficha".
    - O mesmo talento duas vezes no mesmo personagem → uma folha.
    - Cargo VAGO de personagem que já tem alguém escalado → nada (seria uma folha
      anônima duplicada); personagem só com cargos vagos → uma folha anônima.
    - Dois cargos com o mesmo nome em que só um tem ficha vinculada → todos usam a
      ficha (nunca sai uma folha "Sem ficha" ao lado da folha da ficha).
    """
    from app.models import CalendarEvent

    from .drive_service import normalize_name

    event = CalendarEvent.query.get_or_404(event_id)
    roles = [r for r in sorted(event.roles, key=lambda r: r.id) if r.role_type != "extra"]

    # 1º passe: nome normalizado → ficha explícita de algum cargo. É o que deixa um cargo
    # sem vínculo herdar a ficha do colega de mesmo nome mesmo quando a ficha se chama
    # diferente do cargo (aí o lookup por norma abaixo não a encontraria).
    sheet_by_norm: dict[str, FigurinoSheet] = {}
    for role in roles:
        norm = normalize_name(role.character_name)
        if role.figurino_sheet is not None and norm not in sheet_by_norm:
            sheet_by_norm[norm] = role.figurino_sheet

    # 2º passe: agrupa por personagem e, dentro dele, uma folha por talento distinto.
    groups: dict[tuple, dict] = {}
    order: list[tuple] = []
    for role in roles:
        norm = normalize_name(role.character_name)
        sheet = (
            role.figurino_sheet
            or sheet_by_norm.get(norm)
            or FigurinoSheet.query.filter_by(character_name_norm=norm).first()
        )

        key = ("sheet", sheet.id) if sheet else ("norm", norm)
        group = groups.get(key)
        if group is None:
            group = groups[key] = {"by_talent": {}, "talent_order": [], "anon": None}
            order.append(key)

        entry = {
            "role": role,
            "sheet": sheet,
            "pieces": sheet.pieces_list if sheet else [],
            "talent": role.talent,
        }
        if role.talent is None:
            if group["anon"] is None:
                group["anon"] = entry
        elif role.talent_id not in group["by_talent"]:
            group["by_talent"][role.talent_id] = entry
            group["talent_order"].append(role.talent_id)

    items: list[dict] = []
    for key in order:
        group = groups[key]
        if group["by_talent"]:
            items.extend(group["by_talent"][tid] for tid in group["talent_order"])
        elif group["anon"] is not None:
            items.append(group["anon"])

    return render_template("figurino_print.html", items=items, event=event,
                           title=f"Figurinos — {event.title}")

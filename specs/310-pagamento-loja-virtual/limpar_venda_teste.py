"""Desfaz uma venda de TESTE da loja virtual (feature 310, R-21).

O teste real de R$ 1 cria tudo de verdade: evento com valor de venda (entra em vendas, comissão e
DRE), escala, entrega, presente 3D e o evento com sala no Google. Não existe botão para desfazer
uma venda de teste — o "Cancelar e abrir devolução" abriria uma devolução, e no teste o dono já
devolveu o Pix pelo app. Este script faz a limpeza que foi feita à mão em 20/10/2026:

- pedido fica ``cancelado`` (o histórico e os avisos de pagamento ficam);
- horário volta a ``livre``;
- saem o evento local, a escala, a entrega e o presente 3D;
- o evento do Google é apagado, respeitando ``CALENDAR_SUPPRESS_EVENT_WRITES`` (travado = só avisa);
- auditoria registra.

Só aceita pedido de campanha que NÃO está listada na vitrine, ou com ``--forcar`` — para ninguém
apagar uma venda de verdade por engano de número.

Uso (Shell do manto-backend, com OK do dono):
    MANTO_SEM_THREADS=1 python specs/310-pagamento-loja-virtual/limpar_venda_teste.py --pedido N
    MANTO_SEM_THREADS=1 python specs/310-pagamento-loja-virtual/limpar_venda_teste.py --pedido N --execute
"""

import argparse
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app import create_app, db  # noqa: E402
from app.constants import (  # noqa: E402
    VIRTUAL_ORDER_STATUS_CANCELADO,
    VIRTUAL_SLOT_STATUS_LIVRE,
)
from app.marketing import virtuais_ops as ops  # noqa: E402
from app.models import (  # noqa: E402
    CalendarEvent,
    Event3DGift,
    EventRole,
    VirtualCampaignSlot,
    VirtualMediaDelivery,
    VirtualOrder,
)
from app.utils import audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pedido", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--forcar", action="store_true",
                        help="aceita pedido de campanha listada na vitrine")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        order = db.session.get(VirtualOrder, args.pedido)
        if order is None:
            print(f"ERRO: pedido {args.pedido} não existe.")
            return 1
        campanha = order.campaign
        if campanha is not None and campanha.listada and not args.forcar:
            print(f"ERRO: a campanha '{campanha.title}' está listada na vitrine — isto parece venda "
                  "de verdade. Use --forcar só se tiver certeza.")
            return 1
        evento = db.session.get(CalendarEvent, order.event_id) if order.event_id else None
        print(f"Pedido {order.id} {order.order_nsu} · status {order.status} · "
              f"R$ {order.total_value} · campanha {campanha.title if campanha else '-'}")
        print(f"Evento: {evento.id if evento else '-'} "
              f"({evento.google_event_id if evento else '-'}) · horário {order.slot_id or '-'}")
        if not args.execute:
            print("Simulação — rode com --execute para limpar.")
            return 0

        google_id = evento.google_event_id if evento else None
        if order.slot_id:
            slot = db.session.get(VirtualCampaignSlot, order.slot_id)
            if slot is not None and slot.order_id in (order.id, None):
                slot.status = VIRTUAL_SLOT_STATUS_LIVRE
                slot.order_id = None
                slot.locked_until = None
        VirtualMediaDelivery.query.filter_by(order_id=order.id).delete()
        if evento is not None:
            from app.calendar.routes import _clear_event_side_tables

            _clear_event_side_tables(evento.id)
            Event3DGift.query.filter_by(event_id=evento.id).delete()
            EventRole.query.filter_by(event_id=evento.id).delete()
            order.event_id = None
            db.session.flush()
            db.session.delete(evento)
        order.status = VIRTUAL_ORDER_STATUS_CANCELADO
        order.locked_until = None
        audit("delete", "VirtualOrder", order.id, order.order_nsu,
              "Venda de teste desfeita (limpar_venda_teste.py, feature 310)")
        db.session.commit()
        if google_id and not google_id.startswith(ops.GOOGLE_ID_LOCAL_PREFIX):
            ops._apagar_evento_google(google_id)
        print(f"Feito: pedido {order.id} cancelado; evento e escala removidos.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

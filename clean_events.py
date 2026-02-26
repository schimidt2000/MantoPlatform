"""
Script de limpeza — remove todos os eventos e dados relacionados do banco.

Uso:
    python clean_events.py

Limpa:
    - event_logs
    - event_contracts
    - event_payments
    - event_roles
    - calendar_events

NÃO remove: talentos, usuários, configurações, histórico salarial.
"""

from app import create_app, db
from app.models import CalendarEvent, EventRole, EventLog

app = create_app()

with app.app_context():
    # Importa aqui para garantir que os modelos estejam carregados
    from app.models import EventContract, EventPayment

    logs    = EventLog.query.delete()
    contr   = EventContract.query.delete()
    pay     = EventPayment.query.delete()
    roles   = EventRole.query.delete()
    events  = CalendarEvent.query.delete()

    db.session.commit()

    print(f"✓ Removidos: {events} evento(s), {roles} role(s), {logs} log(s), {contr} contrato(s), {pay} pagamento(s).")
    print("Banco limpo. Pronto para beta.")

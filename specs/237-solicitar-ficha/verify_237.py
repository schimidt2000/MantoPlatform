"""Verificação da feature 237 (solicitar ficha) contra o manto_local.

    DATABASE_URL=$(cat .local-db-url) .venv/Scripts/python \
        specs/237-solicitar-ficha/verify_237.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

FALHAS: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  [{'ok' if cond else 'FALHOU'}] {label}")
    if not cond:
        FALHAS.append(label)


def main() -> int:
    from app import create_app
    from app.constants import (
        FIGURINO_KIND_FICHA,
        FIGURINO_KIND_LABELS,
        FIGURINO_KINDS,
        FIGURINO_PROD_EM_PRODUCAO,
        FIGURINO_PROD_FLUXOS,
        FIGURINO_PROD_PRONTO,
        FIGURINO_PROD_SOLICITADO,
        RoleName,
    )
    from app.figurino import producao_ops as ops
    from app.models import FigurinoSheet, User

    app = create_app()
    with app.app_context():
        print("1. Constantes do tipo novo")
        check(FIGURINO_KIND_FICHA in FIGURINO_KINDS, "'ficha' está nos KINDS")
        check(FIGURINO_KIND_LABELS.get(FIGURINO_KIND_FICHA) == "Ficha", "rótulo 'Ficha'")
        check(FIGURINO_PROD_FLUXOS[FIGURINO_KIND_FICHA] == [
            FIGURINO_PROD_SOLICITADO, FIGURINO_PROD_EM_PRODUCAO, FIGURINO_PROD_PRONTO,
        ], "fluxo curto sem aprovação (= manutenção)")
        check(FIGURINO_PROD_FLUXOS["producao"][1] == "aprovado"
              and FIGURINO_PROD_FLUXOS["compra"][2] == "comprado"
              and FIGURINO_PROD_FLUXOS["manutencao"] == [
                  FIGURINO_PROD_SOLICITADO, FIGURINO_PROD_EM_PRODUCAO, FIGURINO_PROD_PRONTO,
              ], "fluxos dos 3 tipos existentes intocados")

        admin = next(
            u for u in User.query.all()
            if any(r.name.upper() == RoleName.SUPERADMIN for r in u.roles)
        )

        print("2. Solicitação")
        try:
            ops.criar_solicitacao_ficha(actor=admin, personagem="   ")
            check(False, "personagem vazio deveria falhar")
        except ops.ProducaoValidationError as exc:
            check(exc.field == "title" and "personagem" in exc.message.lower(),
                  f"personagem vazio barra com a mensagem do tipo ({exc.message!r})")

        pedido, _aviso = ops.criar_solicitacao_ficha(
            actor=admin,
            personagem="TESTE VERIFY 237 - Zeca Urubu",
            observacao="Precisa para o evento do dia 30.",
            origem="/events/new",
        )
        check(pedido.kind == FIGURINO_KIND_FICHA, "pedido nasce com kind='ficha'")
        check(pedido.status == FIGURINO_PROD_SOLICITADO, "status inicial 'solicitado'")
        check(pedido.requested_by_id == admin.id, "solicitante registrado")
        check("dia 30" in (pedido.description or "")
              and "/events/new" in (pedido.description or ""),
              "observação e origem na descrição")
        check(pedido.estimated_cost is None and pedido.responsible_id is None,
              "sem custo e sem responsável na abertura")

        print("3. Fluxo e trava de conclusão")
        trans = ops.transicoes_de(pedido)
        check("aprovado" not in trans and FIGURINO_PROD_EM_PRODUCAO in trans,
              f"de 'solicitado' vai para em_producao/cancelado, nunca aprovação ({sorted(trans)})")
        ops.mudar_status(pedido, FIGURINO_PROD_EM_PRODUCAO, actor=admin)
        try:
            ops.mudar_status(pedido, FIGURINO_PROD_PRONTO, actor=admin)
            check(False, "concluir sem ficha deveria falhar")
        except ops.ProducaoValidationError as exc:
            check("vincule a ficha" in exc.message.lower(),
                  f"concluir sem ficha barra ({exc.message!r})")
        ficha = FigurinoSheet.query.first()
        pedido.figurino_sheet_id = ficha.id
        ops.mudar_status(pedido, FIGURINO_PROD_PRONTO, actor=admin)
        check(pedido.status == FIGURINO_PROD_PRONTO and pedido.done_at is not None,
              "com ficha vinculada conclui e carimba done_at")
        check(pedido.figurino_sheet_id == ficha.id, "pedido concluído aponta para a ficha")

    print()
    if FALHAS:
        print(f"FALHOU: {len(FALHAS)}:")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("VERIFY 237: tudo passou.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# 256b — O relatório da rotina de marketing não saía (500 no `POST /report`)

**Branch**: `256b-relatorio-de-marketing` · **Created**: 2026-11-17 · **Status**: Em produção (17/11 ~22h52)
(`verify_256b.py` 7/7; com o código da `main`, quebra no cenário 1) · **Migration**: nenhuma

## O pedido

Achado na 1ª rodada de marketing em produção (17/11, depois do lote das 19h): o `POST /report` do agente de
marketing respondeu 500 e o e-mail não saiu. A rotina de segunda (23/11) cairia no mesmo erro.

## O que muda

Desde a 256 (21/08), `app/api/marketing_agent.py` chama `send_audit_report_email(..., preheader=...)`, mas a
função (`app/email_service.py`, da 221) nunca teve esse parâmetro: `TypeError` antes de qualquer envio.

- `send_audit_report_email` ganha `preheader`, com o texto do auditor financeiro como padrão.
- O auditor financeiro, que chama sem o parâmetro, segue igual.

## Verificação

`verify_256b.py` no espelho do lote (`manto_lote1711`), com o envio dublado e o socket bloqueado:

1. `POST /report` → 200, um e-mail, prévia do marketing. Na `main`, quebra com o erro do parâmetro.
2. O auditor financeiro mantém a prévia dele.
3. Destinatário fora do quadro interno não recebe nada.
4. Token errado → 404.

Também roda `ruff check` nos arquivos tocados.

## Fora de escopo

- Reenviar o relatório de 17/11: foi entregue ao dono no chat.

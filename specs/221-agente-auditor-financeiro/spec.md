# Feature 221 — Agente auditor financeiro semanal

**Status**: implementada (2026-08-06) · **Migration**: nenhuma · **Branch**: `221-agente-auditor-financeiro`

> Feature construída sob demanda direta do dono (fora da esteira SDD completa); este spec é o
> registro condensado de requisitos e decisões.

## Problema

O dono não consegue revisar manualmente todas as movimentações: comprovantes anexados podem
ser falsos, duplicados ou divergentes do registrado, e não há verificação nenhuma hoje.
Descoberta durante a análise: `_save_bounded_upload` sobrescrevia uploads homônimos
(11 duplicatas reais de `file_path` em `event_payments` na base de produção).

## Solução

Rotina semanal (segunda ~06h, Claude Code local, assinatura Max — **zero API paga**) que:

1. Coleta as movimentações da janela no Postgres de produção em **modo somente leitura**
   (`scripts/auditor/collect.py`).
2. Baixa os comprovantes via `GET /api/audit-agent/<token>/file/<path>` (novo endpoint,
   token de ambiente `AUDIT_AGENT_TOKEN`, 404 para token inválido — molde do webhook
   InfinitePay) e calcula SHA-256 (dedup + integridade dali em diante).
3. Claude lê cada comprovante (visão nativa) e grava extração JSON
   (valor/data/pagador/recebedor/PIX/banco/score de aparência).
4. `checks.py` cruza extração × registro × chave PIX cadastrada do beneficiário
   (normalização em `pixnorm.py`), detecta duplicatas por hash contra o histórico
   (`data/audit_store.sqlite`) e agrega anomalias SQL.
5. `report.py` monta o HTML e envia por `POST /api/audit-agent/<token>/report`
   (destinatários restritos a usuários internos ativos).

## Requisitos funcionais (resumo)

- FR-01 Auditoria por comprovante: EventPayment, SpecialExpense, SalaryAdvance,
  EventReimbursement (NF + recibo).
- FR-02 Fluxos sem campo de anexo (cachê, comissão, recorrente, BV) entram no relatório
  como "não auditáveis" — decisão de produto de 08/2026: **não** criar campo de anexo agora.
- FR-03 Anomalias SQL: mesmo arquivo em 2+ recebimentos; recebido > venda + transporte +
  acréscimos (≤1% atenção, >1% crítico); parcela recebida sem comprovante; recorrente fora
  da faixa; divergências da loja virtual (lê `VirtualPaymentNotification`, não reconsulta).
- FR-04 Margem por evento: custo (cachês não dispensados + gastos aprovados) ≥ 85% da venda
  vira achado.
- FR-05 Idempotência: comprovante (entidade+hash) lido uma vez; anomalias históricas
  reportadas uma vez (supressão por `entity_uid` no store).
- FR-06 Relatório: números da semana (entradas × saídas × saldo), achados por severidade,
  lista dos não auditáveis; e-mail ao dono.
- FR-07 "Autenticidade" é heurística de consistência — nunca prova bancária; o relatório
  declara isso.

## Decisões e alternativas descartadas

- **Roda na máquina local** (assinatura), não como cron no Railway — vision pela API teria
  custo por token; catch-up automático se o PC estiver desligado no horário.
- Endpoint de arquivos em vez de credencial de login de serviço: token dedicado, escopo
  restrito a `payments/expenses/invoices/contracts` + allowlist de extensão.
- Store local (SQLite) em vez de tabela nova em produção: o ERP fica intocado (job 100%
  read-only); tabela `payment_audit_findings` fica como evolução futura se precisar de
  visibilidade no app.
- Skills locais (`.claude/skills/financeiro-auditor`, `financeiro`) — `.claude/` está no
  `.gitignore` deste repo; vivem só na máquina que roda o auditor.

## Segredos

`.audit-agent-token` (raiz, gitignored) = env `AUDIT_AGENT_TOKEN` no Railway. Sem o env
configurado em produção, os endpoints respondem 404 e o auditor não funciona — é o
interruptor geral.

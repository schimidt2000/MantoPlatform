# Agente auditor financeiro (feature 221)

Rotina semanal que audita as movimentações financeiras da plataforma: abre os comprovantes
anexados, cruza valor/data/beneficiário/PIX com o registro do sistema, caça duplicatas e
anomalias e envia o relatório por e-mail. Roda na máquina local via Claude Code (assinatura,
sem API) — a orquestração está na skill `.claude/skills/financeiro-auditor/`.

## Pipeline

```
collect.py  →  [Claude lê cada comprovante → runs/<id>/extracted/*.json]  →  checks.py  →  report.py --send
```

1. **`collect.py`** — lê o Postgres em modo somente leitura (produção via `.railway-db-url`,
   ou `--local` para `manto_local`), monta `runs/<id>/manifest.json` e baixa os comprovantes
   da janela (produção: endpoint `/api/audit-agent/<token>/file/...`; local: cópia de
   `instance/uploads/`). Idempotente: comprovante já lido (mesmo hash) não reprocessa.
2. **Leitura dos comprovantes** — feita pelo Claude na rodada (visão nativa em PDF/imagem).
   Para cada item `needs_extraction`, escreve `runs/<id>/extracted/<uid>.json` (formato no
   docstring de `checks.py`).
3. **`checks.py --run <id>`** — batimento determinístico + gravação dos achados na memória
   (`data/audit_store.sqlite`).
4. **`report.py --run <id> --send`** — monta o HTML e envia via
   `POST /api/audit-agent/<token>/report` (destinatários em `config.py`).

## Segredos (raiz do repo, fora do git)

- `.railway-db-url` / `.local-db-url` — já existentes.
- `.audit-agent-token` — token do agente; o MESMO valor precisa estar no env
  `AUDIT_AGENT_TOKEN` do serviço no Railway.

## Limites conhecidos

- "Autenticidade" é heurística de consistência — não há como provar autenticidade bancária
  sem consultar a instituição emissora.
- Cachês, comissões, recorrentes e BV não têm campo de anexo no sistema: entram no
  relatório como "não auditáveis" (decisão de produto de 08/2026).
- Usa o Python do venv do projeto: `.venv/Scripts/python.exe` (psycopg v3 + requests).

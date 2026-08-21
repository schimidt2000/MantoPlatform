# Quickstart — validação ponta a ponta da feature 256

Pré-requisitos: `manto_local` restaurado; `.venv`; `.marketing-agent-token` na raiz (qualquer string longa) e, para a rodada local, o Flask local sobe com `MARKETING_AGENT_TOKEN` igual ao arquivo e `FLASK_ENV=development`; `frontend/apps/internal` com `npm run dev`.

```powershell
$env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development"
$env:MARKETING_AGENT_TOKEN = (gc .marketing-agent-token -Raw).Trim()
```

## 1. Migration

`.venv\Scripts\python.exe -m flask db upgrade` → tabelas `marketing_agent_runs`, `marketing_import_files`, `marketing_post_metrics`, `marketing_campaign_metrics`, `marketing_account_metrics`, `marketing_ad_spend_batches`, `marketing_ad_spend_lines`; colunas `marketing_posts.permalink`, `clients.lead_origin/utm_source/utm_medium/utm_campaign`. `flask db downgrade` remove tudo sem erro.

## 2. Verificação automatizada (Test-First)

```powershell
.venv\Scripts\python.exe specs\256-auditor-marketing\verify_256.py
```

Cenários (cada um imprime OK/FALHA; saída final `N/N OK`):

1. **Parsers**: as 4 fixtures válidas (`fixtures/meta_conteudo.csv`, `meta_conta.csv`, `meta_ads_dia.csv`, `google_ads_dia.csv`) viram o `normalizado.json` esperado; `fixtures/invalido_colunas.csv` ⇒ `rejected: colunas faltantes`; `fixtures/google_ads_agregado.csv` ⇒ aceito como agregado com período do preâmbulo; número ambíguo ⇒ linha rejeitada.
2. **Token**: sem env ⇒ `GET /context` 404; token errado ⇒ 404; token certo ⇒ 200 com `card_holder`.
3. **Ingestão idempotente**: `POST /run` com payload das fixtures ⇒ contagens; mesmo payload ⇒ `replayed: true` e nenhuma linha nova; arquivo com mesmo sha256 em outro `run_id` ⇒ `skipped_duplicate`.
4. **Reembolso mensal**: 1ª rodada (Meta Ads agosto) ⇒ `action: created`, Gasto Extra `pendente`, categoria `Marketing`, reembolso ao titular, 3 linhas; 2ª rodada com mais dias ⇒ `updated` e valor novo; aprovar o gasto via `gastos_ops.approve_expense` ⇒ 3ª rodada com valor diferente ⇒ `frozen_divergent` + achado `gasto_divergente`; gasto manual de Marketing no mês (Google) ⇒ `skipped_manual` + achado; arquivo em USD ⇒ métricas gravadas, nenhum gasto.
5. **Sobreposição**: diário + agregado das mesmas datas ⇒ gasto do mês só com diários + achado `periodo_sobreposto`.
6. **Vínculo de post**: card `__v256_` publicado com `permalink` ⇒ `link_method: permalink`; card sem link e 1 candidato na data ⇒ `date`; 2 candidatos ⇒ `none` + `unlinked_posts` com ambos; preencher o link e rodar de novo ⇒ revinculado.
7. **Kommo**: importar `fixtures/kommo_utm.csv` ⇒ `Client.utm_campaign/lead_origin` preenchidos; export sem as colunas ⇒ importa como antes.
8. **Contexto e atribuição**: `GET /context` traz `goals` com `status` igual ao de `GET /api/marketing/goals`, `attributed_clients` casando `utm_campaign` normalizado.
9. **Tela/API**: `GET /api/marketing/desempenho?weeks=12` como MARKETING ⇒ 200 com `weekly`, `campaigns`, `posts`, `runs`, `cac`, `headline.kind == "leads"`; como CASTING ⇒ 403; `start > end` ⇒ 400; banco sem rodadas ⇒ `empty: true`.
10. **Permalink**: `PATCH /api/marketing/posts/<id>` com `"ftp://x"` ⇒ 400 com `fields.permalink`; com URL válida ⇒ 200 e `permalink` normalizado no `GET`.
11. **Serializer do gasto**: `GET` do Gasto Extra gerado ⇒ `marketing_batch.lines` com 3 itens.
12. **Limpeza**: tudo com prefixo `__v256_` removido; usuário descartável apagado (`roles.clear()` antes).

## 3. Rodada local completa (simulando a segunda-feira)

```powershell
Copy-Item specs\256-auditor-marketing\fixtures\*.csv scripts\marketing\inbox\
cd scripts\marketing
..\..\.venv\Scripts\python.exe collect.py --local      # imprime run_id; move arquivos p/ processed/
..\..\.venv\Scripts\python.exe publish.py --run <id> --local
..\..\.venv\Scripts\python.exe checks.py  --run <id> --local
..\..\.venv\Scripts\python.exe report.py  --run <id> --local --save-only
```

Esperado: `runs/<id>/relatorio.html` com manchete de leads (ou alcance com motivo), blocos na ordem do FR-020, barras CSS visíveis ao abrir no navegador; `resumo.md` em português. `--send` (com Flask local) ⇒ `enviados >= 1` para o dono.

## 4. Tela

`http://localhost:5173/marketing/desempenho` logado como superadmin (ou MARKETING): gráficos das 12 semanas, tabela de posts com título do card, tabela de campanhas com CPC/CPL, lista de rodadas com arquivos rejeitados. Trocar para 4 semanas sem piscar (placeholder). Em 375 px: sem rolagem horizontal da página (`document.documentElement.scrollWidth === 375`). Com o banco sem rodadas: estado vazio com as instruções de exportação.

## 5. Card de postagem

Abrir um card, mudar status para "Publicado" sem link ⇒ campo "Link do post publicado" em destaque com orientação; colar link inválido ⇒ erro no campo, valores preservados; link válido ⇒ salvo e visível no card.

## 6. Skill + agendamento (máquina do dono)

`.claude/skills/marketing-auditor/SKILL.md` presente; scheduled task `auditoria-marketing-semanal` listada com cron `30 6 * * 1`; executar a task manualmente uma vez com a inbox preenchida ⇒ e-mail recebido + resumo no chat.

## Portões antes de "pronto"

`npx tsc --noEmit` limpo em `frontend/apps/internal`; `ruff check app scripts/marketing specs/256-auditor-marketing`; `verify_256.py` 12/12; `docs/01`, `docs/02`, `docs/03` atualizados; `/speckit-converge` sem gaps.

# Plano de implementação: Feature 345 — marketing integrado ao sistema

**Branch**: `345-marketing-integrado` | **Data**: 2026-11-16 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/345-marketing-integrado/spec.md`

## Resumo

O ERP passa a ser o painel de comando do marketing pago. A rotina semanal do Claude (máquina do dono, conectores Meta
e Google) grava o desempenho por campanha e por anúncio pela entrada de token da 256. O sistema cruza esse gasto com
as vendas de cada frente para dar o custo por venda misto contra um teto. Os temas do catálogo ganham origem e
"liberado para anúncio", e o servidor recusa anúncio com tema não liberado. O card do Kanban vira pedido de criativo
com briefing e vínculo com o anúncio. Mudança de gasto vira proposta que só o Superadmin aprova, e toda execução cai
num diário com data de reavaliação.

Abordagem: estender a 256 (mesmo token, mesmo `_ops`, mesmas tabelas onde couber) em vez de criar um segundo agente.
Um núcleo novo, `app/marketing/comando_ops.py`, guarda frente, custo por venda, licença, propostas e diário. A
rotina deixa de depender de CSV: a skill `marketing-auditor` passa a ler pelos conectores.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no frontend

**Dependências principais**: as de sempre. Nenhuma dependência nova no `requirements.txt` nem no `package.json`.

**Armazenamento**: PostgreSQL. A verificação roda no banco próprio `manto_345`, restaurado do dump noturno de
16/11 (ver Rastreamento).

**Verificação**: `specs/345-marketing-integrado/verify_345.py` contra `manto_345`; `npm run typecheck`; telas no Browser
pane (desktop e 390 px).

**Plataforma-alvo**: web interna (staff). O dono aprova as propostas pelo celular, então a tela de propostas precisa
funcionar bem em 390 px.

**Tipo de projeto**: SPA desacoplada.

**Metas de desempenho**: o desempenho por frente sai em < 1 s com ~500 vendas por ano (uma consulta agregada por frente,
sem N+1).

**Restrições**:
- Nenhuma rota pública nova, então `BACKEND_PREFIXES` não muda.
- O agente segue sem token = 404.
- A rotina nunca ativa nem muda gasto sem proposta aprovada.

**Escala/escopo**: 1 migration; 4 colunas em `catalog_items` + 2 de autoria; 7 em `marketing_posts`; 2 em
`marketing_campaign_metrics`; 2 em `site_settings`; 6 tabelas novas; ~12 endpoints de tela e 8 de agente; 2 telas
novas (Temas e licença, Decisões); 2 telas alteradas (Desempenho, Kanban/diálogo do card).

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar | Reusa o token, o `_token_valido`, o `ingest_run`, o `_upsert` e o `_effective_campaign_rows` da 256, mais o `require_marketing_access`, o `serialize_post`/`create_post`/`update_post` do 204 e os gráficos `components/charts/`. Nada de segundo agente. |
| II. Padrões | Type hints, docstrings Google, `ruff check` nos tocados, `ruff format` só em arquivo novo. TS estrito. |
| III. Camadas | `comando_ops.py` é puro. `marketing_comando_read.py`/`_write.py` fazem só RBAC + serialização, importados em `app/api/__init__.py`. |
| IV. Não quebrar | Migration aditiva. Card antigo vira `tipo='post'`. O `POST /run` da 256 só ganha 2 campos opcionais. O payload novo do desempenho é opcional no TS (`frentes?`). |
| V. Feedback | TanStack Query, botão com loading, erro no campo, texto "Salvo." inline (o app não tem toast). |
| VI. Esteira | Nível 1 completa. As decisões do "acelerar" estão em Clarifications. |
| VII. Living spec | A spec foi ajustada (licença dupla, Superadmin aprova) antes do código. |
| VIII. Verify antes do núcleo | `verify_345.py` (17 cenários, 5 que devem falhar) escrito na fase Foundational. |
| IX. Dinheiro | `Numeric(12,2)`/`Decimal`; tela com `formatBRL`; teto editado com `MoneyInput`. |
| X. Mobile público | Não toca superfície pública. A tela de propostas é conferida em 390 px mesmo assim. |
| XI. Motion | Cards de proposta com `AnimatePresence` + `useReducedMotion`, no padrão do Kanban. |
| XII. Combobox | Responsáveis e temas pelo `Combobox` de `@manto/ui`. A frente (5 valores) usa `<select>` nativo, como a plataforma. |
| XIII. RBAC | Gates por função no início da view. Decidir proposta e liberar licenciado é só SUPERADMIN. Linhas em `docs/01` §4.3. |
| XIV. Config | Sem env nova. Usa `MARKETING_AGENT_TOKEN`, que já existe; sem ele, 404. O efeito externo (Meta/Google) mora na rotina, fora do servidor, e só com proposta aprovada. |
| XV. Texto | Superfície interna, tom operacional. Mensagens: "Este tema não está liberado para anúncio", "Esta proposta já foi decidida", "Proposta expirada". O frontend não compara texto: decide pelo `codigo`. |
| Stack | Migration à mão, `down_revision = e344a1b2c3d4`. Sem Jinja. |
| Operação e Deploy | Não toca `startCommand`. Migration aditiva, então sem ensaio destrutivo. O deploy do backend fica fora do horário da equipe. |

## Estrutura do projeto

### Documentação

```text
specs/345-marketing-integrado/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api-345.md
├── checklists/requirements.md
├── tasks.md
└── verify_345.py
```

### Código

```text
migrations/versions/f345c0a1b2d3_marketing_integrado.py
app/models.py                       # colunas novas + 6 models
app/constants.py                    # MARKETING_FRENTES, prefixos, formatos, situações
app/marketing/comando_ops.py        # NOVO: frente, custo por venda, teto, licença, pedidos, propostas, diário
app/marketing/marketing_ops.py      # tipo/frente/formato/briefing no card; regra do tema liberado; serialize
app/marketing/desempenho_ops.py     # conversations/leads na ingestão; bloco por frente no summary
app/api/marketing_comando_read.py   # NOVO (frentes, temas-licença, propostas, diário)
app/api/marketing_comando_write.py  # NOVO
app/api/marketing_write.py          # POST_FIELDS ganha os campos do briefing; 422 tema_nao_liberado
app/api/marketing_agent.py          # 8 rotas novas do agente
app/api/__init__.py                 # importar os 2 módulos novos
frontend/apps/internal/src/lib/marketing.ts            # tipos + hooks novos
frontend/apps/internal/src/pages/MarketingDesempenhoPage.tsx  # bloco "Por frente", sem frente, plataformas
frontend/apps/internal/src/pages/MarketingDecisoesPage.tsx    # NOVA: propostas + diário
frontend/apps/internal/src/pages/MarketingTemasPage.tsx       # NOVA: origem e liberado
frontend/apps/internal/src/components/MarketingPostDialog.tsx # tipo, frente, formato, briefing, anúncios
frontend/apps/internal/src/components/MarketingKanban.tsx     # selo "Anúncio"/"Rotina" no card
frontend/apps/internal/src/components/marketing/FrentesConfigDialog.tsx  # NOVO: teto + responsáveis
frontend/apps/internal/src/App.tsx · lib/navigation.tsx       # 2 rotas + 2 itens de menu
.claude/skills/marketing-auditor/SKILL.md                     # rotina pelos conectores
```

**Decisão de estrutura**: um `_ops` novo (`comando_ops`), em vez de engordar o `desempenho_ops` (902 linhas). As
regras novas atravessam catálogo, card, propostas e diário, e o `desempenho_ops` continua sendo a ingestão e o
reembolso da 256. Os endpoints de tela ficam num par `_read`/`_write` próprio, seguindo a convenção por domínio. Os do
agente ficam no `marketing_agent.py`, que já é a porta única do token.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_345`, não `manto_local` | O `manto_local` é compartilhado e pode estar numa migration do CRM (325–335, sem push) que a `main` não conhece. O padrão das worktrees é um espelho por feature. | Refazer o `manto_local` apagaria o esquema das sessões do CRM. |
| Regex Postgres (`~*`) na frente social | É a regra que gerou os números de 16/11. | `ILIKE` com várias palavras daria a mesma coisa com 5 condições. O regex é uma linha e só roda no Postgres, que é a produção. |

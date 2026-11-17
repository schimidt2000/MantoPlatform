<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 350 — base autorizada

**Branch**: `350-base-autorizada` | **Data**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/350-base-autorizada/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

Dois consentimentos com prova (histórico append-only com texto, versão, origem, referência e autor),
registrados pela equipe na ficha e na conversa, pela própria cliente na página pública de avaliação e
pela loja (344); saída automática por palavra de saída e pelo erro 131050; recusa de modelo de marketing
sem aceite; indicação e parceiro na ficha; pós-evento único (mensagem montada no backend, copiada ou
enviada pela conversa, um registro por evento) e a lista de aniversários dos próximos 60 dias.

Abordagem: quatro núcleos novos e pequenos em `app/clientes/` (`consentimento_ops`, `indicacao_ops` +
`parceiro_ops`, `aniversario_ops`, `pos_evento_ops`); dois módulos de API novos
(`clientes_base_read.py`, `clientes_base_write.py`); ganchos de uma linha nos pontos que já existem
(`aviso_ops`, `envio_ops`, `instagram_ops`, `leitura_ops`, `virtuais_ops`, `quote_ops`,
`feedback_write`, `clientes_read`). Uma migration aditiva.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`
(`apiFetch`/`assetUrl`), `@manto/money`

**Armazenamento**: PostgreSQL — produção no Render. Verificação contra o espelho **próprio**
`manto_350` (dump noturno de 17/11/2026, head `d334b2c4e6f8`), não o `manto_local` compartilhado.

**Verificação**: `specs/350-base-autorizada/verify_350.py` contra `manto_350` (login só pela API;
escrita por conexão separada; Meta em dublê + disjuntor de rede, molde `verify_325`);
`cd frontend && npm run typecheck`; telas no Browser pane com backend próprio na porta **5350** e Vite
na **6350**; página pública em 375×812.

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
equipe no celular (390 px) e no computador; cliente no celular.

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: listas (pós-evento, aniversários, parceiros) abaixo de 300 ms com a base real
(6.291 fichas; aniversários começam vazios). O gancho no aviso do WhatsApp custa uma comparação de
texto e, só no acerto, uma escrita.

**Restrições**: `/catalogo/avaliar/:token` é URL imutável (`docs/00` §6 item 20) — a página só ganha
conteúdo; o botão do Google segue `score === 5`; nada envia mensagem sozinho; nenhuma rota pública nova
fora de `/api` (o prefixo `/api` já está no proxy); campo novo do payload é opcional no React.

**Escala/escopo**: 4 tabelas novas (`parceiros`, `cliente_consentimentos`, `cliente_criancas`,
`pos_eventos`), 5 colunas novas em `clients`; 14 endpoints novos + 3 alterados; 3 telas novas
(Pós-evento, Aniversários, Parceiros), 2 cartões novos na ficha, 1 chip na conversa, 1 diálogo no evento,
1 bloco na página pública.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 (sem mudança).*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `ensure_feedback_token` (link de avaliação), `envio_ops.enviar_texto` (chave idempotente) e `janela_aberta`, `cfg_whatsapp().ligado`, `_aceite_de_novidades`/`VIRTUAL_ACEITE_VERSAO` (molde de versão), `Combobox` + `useClientSearch` (molde `AssociarDialog`), `whatsappLink`/`WHATSAPP_LOJA` do público, `strip_accents_lower`, dublê `MetaFalsa` do `verify_325`. O texto do pós-evento substitui `buildFeedbackMsg` (uma fonte só, no backend). |
| II. Padrões de código | type hints/docstrings; funções ≤ ~30 linhas; constantes em `app/constants.py`; TS estrito sem `any`; `ruff check` nos tocados, `ruff format` só nos novos |
| III. Camadas / API First | `*_ops.py` sem `flask.request` e **sem commit** (o endpoint comita; o webhook comita no `processar_aviso`); módulos novos importados em `app/api/__init__.py`; nenhuma rota fora de `/api` |
| IV. Não quebrar o que funciona | migration aditiva; ganchos só agem no acerto (palavra exata, código 131050, categoria MARKETING); a página de avaliação mantém o fluxo e o filtro da nota 5; a loja continua gravando como antes e passa a respeitar a retirada |
| V. UI/UX com feedback | TanStack Query; botões com `isPending`; erro no campo (`ApiRequestError.fields`); toasts pt-BR; remover aniversário e retirar aceite com `ConfirmDialog` |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/350-base-autorizada/` |
| VII. Living Spec | spec com Clarifications antes do código |
| VIII. Verify antes do núcleo | `verify_350.py` na fase Foundational, contra o espelho próprio (exceção registrada abaixo) |
| IX. Dinheiro BRL | não há dinheiro; a comissão do parceiro é percentual (`Numeric(5,2)`) |
| X. Mobile-first público | bloco da página de avaliação: 320–430 px, alvos ≥ 44 px, texto ≥ 12 px |
| XI. Framer Motion | bloco de consentimento entra com `motion` + `useReducedMotion` (molde do bloco do Google) |
| XII. Combobox / Maps | "Indicado por" e "Parceiro" com `Combobox` pesquisável; nenhum `<select>` > 10 itens |
| XIII. RBAC declarado | gates por endpoint em `contracts/api.md`; linha em `docs/01` §4.3; cenário 4 do verify deve falhar |
| XIV. Config / efeito externo | nenhuma env nova; o envio do pós-evento passa por `envio_ops` (trava `_suppress_whatsapp` + `ConexaoMeta.travada`) |
| XV. Texto por superfície | interno operacional; público lúdico e claro; mensagem copiada no tom da casa ("Oi, Ana! …"); glossário: "Inserir aniversário", "Remover", "Situação"; nenhum texto comparado no frontend |
| Stack | migration à mão `a350b1c2d3e4`, `down_revision = "d334b2c4e6f8"`; sem Jinja; sem segredo |
| Operação e Deploy | não toca `startCommand`; migração não destrutiva; backend em lote |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/350-base-autorizada/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/requirements.md · checklists/lgpd.md
├── tasks.md
└── verify_350.py
```

### Código

```text
migrations/versions/a350b1c2d3e4_base_autorizada.py      # aditiva
app/models.py                                            # Parceiro, ClienteConsentimento, ClienteCrianca, PosEvento; colunas em Client
app/constants.py                                         # textos e versões, origens, palavras de saída, tipos de parceiro
app/clientes/consentimento_ops.py                        # aceite/retirada, crianças, saída automática, guarda de prospecção, serialização
app/clientes/indicacao_ops.py                            # indicado por + parceiro da ficha
app/clientes/parceiro_ops.py                             # CRUD do parceiro + contagem
app/clientes/aniversario_ops.py                          # próximos N dias (29/02)
app/clientes/pos_evento_ops.py                           # mensagem única, lista, registro, envio pela conversa
app/api/clientes_base_read.py | clientes_base_write.py   # registrar em app/api/__init__.py
app/api/clientes_read.py                                 # detalhe ganha consentimentos, indicação, parceiro, flags
app/api/feedback_write.py                                # bloco de consentimento + POST público
app/conversas/aviso_ops.py, envio_ops.py, instagram_ops.py, leitura_ops.py   # ganchos
app/marketing/virtuais_ops.py                            # loja: histórico + respeita retirada
app/orcamento/quote_ops.py                               # linha do convite na mensagem
frontend/apps/internal/src/lib/baseAutorizada.ts         # tipos + hooks
frontend/apps/internal/src/components/clientes/{ConsentimentosCard,AceiteDeNovidadesDialog,CriancaDialog,IndicacaoCard}.tsx
frontend/apps/internal/src/components/conversas/AceiteNaConversa.tsx
frontend/apps/internal/src/components/EventDetail/PosEventoDialog.tsx
frontend/apps/internal/src/pages/{PosEventoPage,AniversariosPage,ParceirosPage}.tsx
frontend/apps/public/src/components/feedback/{ConsentimentoCard,IndicarAmiga}.tsx; lib/feedback.ts; pages/AvaliarPage.tsx
```

**Decisão de estrutura**: o consentimento é da **ficha** (domínio Clientes), então o núcleo mora em
`app/clientes/`; Conversas, Loja e Feedback só chamam funções dele (dependência de lá para cá, nunca o
contrário — `consentimento_ops` não importa `app.conversas`). O pós-evento também mora em Clientes: é
relacionamento com a contratante; ele importa `envio_ops` só dentro da função de envio (import tardio,
para não criar ciclo `conversas → clientes → conversas`).

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_350`, não `manto_local` (Princípio VIII) | quatro features (348–351) migram ao mesmo tempo sobre `d334b2c4e6f8`; o `manto_local` é compartilhado | migrar o `manto_local` com `a350` quebraria o `flask db upgrade` das outras sessões |
| Horários do consentimento e do pós-evento em `now_sp()` (terceiro relógio, `docs/00` §6 item 2) | o aceite da loja (344) já grava `marketing_opt_in_at` em horário de SP; aceite e retirada precisam ser comparáveis | UTC aqui obrigaria converter o legado da 344 e erraria 3 h na regra "aceite posterior à retirada" |
| `GET /api/events/<id>/pos-evento` gera o token de avaliação na primeira leitura | a prévia precisa do link; o token é idempotente e não expira | um POST só para gerar o token duplicaria o `feedback-link` |

# Plano de implementação: 349 — O comercial mede e fecha pela conversa

**Branch**: `349-comercial-mede-e-fecha` | **Data**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/349-comercial-mede-e-fecha/spec.md`

## Resumo

Sete peças sobre o CRM próprio (325–335), todas no domínio `app/conversas/`: a conversa passa a guardar a primeira
mensagem e a primeira resposta (com autor e origem, inclusive o eco sem autor), a perda com motivo, a decisão de
qualificação e o lembrete; a pontuação por regras é calculada na leitura, em lote, com os mesmos fatos que o funil já
lê. A lista ganha selos e três recortes; o funil, as colunas de primeira resposta, qualificadas e perdidas. A
calculadora e a criação de evento aprendem a vir da conversa e voltar para ela, pelo endereço. A régua de lembretes
roda na varredura das conversas e só escreve no sino. Uma migration aditiva (`a349c0e1f2a3` sobre `d334b2c4e6f8`).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack Query, Tailwind CSS,
`@manto/ui`, Framer Motion, `@manto/api-client`

**Armazenamento**: PostgreSQL. Verificação contra o espelho **`manto_349`** (dump noturno de 17/11, head
`d334b2c4e6f8`), não o `manto_local` compartilhado — ver Rastreamento de complexidade.

**Verificação**: `specs/349-comercial-mede-e-fecha/verify_349.py` contra `manto_349`; `cd frontend && npm run
typecheck`; telas no Browser pane com backend próprio na porta **5349** e Vite na **6349** (memória "conferir tela em
worktree"), em 390 px e no computador.

**Plataforma-alvo**: web; a equipe comercial usa no celular como app instalado.

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**:
- A lista de conversas (consultada a cada 5 s) ganha no máximo ~10 consultas em lote por página de 50, nunca uma por
  conversa (SC-007).
- A calculadora não ganha requisição: o nome entra no estado inicial, não num efeito.
- A varredura (60 s) ganha duas consultas indexadas por passada.

**Restrições**: 390 px sem rolagem lateral; `useReducedMotion`; campo novo do payload é opcional no React (armadilha
21); horários de `conversas` em UTC naive, com `+00:00` na API; "amanhã às 9h" pelo relógio de São Paulo (`now_sp`).

**Escala/escopo**: 13 colunas em `conversas`; 2 `kind` de aviso; 7 endpoints novos + 3 alterados; 6 telas tocadas
(Conversas, conversa aberta, envio de orçamento, Calculadora, Criar evento, Funil).

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 (sem mudança).*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `funil_ops._etapas` (etapa da lista e da pontuação), `_resposta_valida` da 328 (primeira resposta), molde `destino_ops` da 298 (motivos com `pede_frase`, lista vinda do servidor), `notificacoes_ops.emitir` + dedupe (lembrete e régua), varredura da 325, `KebabMenu`, `Badge`, `Dialog`, `EscolhaDeFicha`/`FichaDaConversaDialog`, `POST /api/events` e o prefill do orçamento (273/333) |
| II. Padrões de código | type hints, docstrings Google, constantes `UPPER_CASE` em `constantes.py`, funções curtas; TS estrito; `ruff check` nos tocados, `ruff format` só nos novos |
| III. Camadas / API First | núcleo em `app/conversas/{primeira_resposta,venda,pontuacao,parado,fechamento}_ops.py` (puro); `app/api/conversas_venda.py` só RBAC + serialização, registrado em `app/api/__init__.py`; nenhuma rota pública |
| IV. Não quebrar o que funciona | migration aditiva; `listar_conversas` e `funil` só ganham parâmetros opcionais e campos; `POST /api/events` só lê `conversa_id` se vier; ganchos novos na gravação de mensagem são condicionais e não mudam a espera da 328 |
| V. UI/UX com feedback | TanStack Query com loading nos botões, erro no campo (`fields.motivo`/`frase`), invalidação da conversa e da lista |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/349-comercial-mede-e-fecha/` |
| VII. Living Spec | clarify de 17/11 integrado antes do plano |
| VIII. Verify antes do núcleo | `verify_349.py` na fase Foundational, falhando pelos motivos certos antes do núcleo |
| IX. Dinheiro BRL | não cria valor monetário; a criação de evento segue a da 152 |
| X. Mobile-first público | não toca superfície pública; a interna nasce em 390 px (memória de UX) |
| XI. Framer Motion | selos e faixa da venda entram com `motion` curto, desligado por `useReducedMotion` |
| XII. Combobox / Maps | motivos de perda são 7 (lista de opções, não combobox); o vendedor segue o seletor da criação de evento |
| XIII. RBAC declarado | `pode_conversas` (COMERCIAL e SUPERADMIN, papel real) no início de cada view nova; `POST /api/events` mantém `_can_create_event`; linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | nenhuma env nova; nada fala com a Meta: lembrete e régua só gravam no sino e no celular da equipe (push 332, já travado pela config dele) |
| XV. Texto por superfície | superfície interna: "Marcar como perdida", "Informe o motivo", "Lembrar amanhã", "Cancelar lembrete", "Criar evento", "Fazer orçamento"; Situação não entra; nenhum texto do servidor é comparado no frontend (a tela compara `codigo`) |
| Stack | migration à mão `a349c0e1f2a3` (`down_revision = d334b2c4e6f8`); sem Jinja; sem segredo |
| Operação e Deploy | não toca `startCommand`; migração aditiva, sem ensaio destrutivo; backend cai ~1 min no deploy (vai no lote) |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/349-comercial-mede-e-fecha/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/requirements.md · checklists/<tema>.md (/speckit-checklist)
├── tasks.md
└── verify_349.py
```

### Código

```text
migrations/versions/a349c0e1f2a3_comercial_mede_e_fecha.py   # aditiva + preenchimento
app/models.py                                  # Conversa: 13 colunas
app/conversas/constantes.py                    # motivos, regras, recortes, régua, textos
app/conversas/primeira_resposta_ops.py         # NOVO — primeira mensagem e primeira resposta
app/conversas/pontuacao_ops.py                 # NOVO — etapa + sinais + pontos, em lote
app/conversas/parado_ops.py                    # NOVO — "orçamento parado" (SQL único), régua e lembrete vencido
app/conversas/venda_ops.py                     # NOVO — perda, qualificação, lembrete, painel e resumo da lista
app/conversas/fechamento_ops.py                # NOVO — o que levar ao evento + ponto único evento↔conversa
app/conversas/{aviso_ops,instagram_ops,equipe_ops}.py    # ganchos da primeira mensagem/resposta
app/conversas/{leitura_ops,funil_ops,varredura}.py       # recorte, métricas novas, rotina nova
app/notificacoes/notificacoes_ops.py           # 2 kinds no catálogo
app/api/conversas_venda.py                     # NOVO — endpoints da venda (registrar em app/api/__init__.py)
app/api/conversas_read.py                      # recorte/dias + `venda` por item
app/api/agenda_write.py                        # POST /api/events: `conversa_id`
frontend/apps/internal/src/lib/{conversas,funil,eventCreate}.ts
frontend/apps/internal/src/components/conversas/{PainelDaVenda,PerdidaDialog,SelosDaVenda}.tsx  # NOVOS
frontend/apps/internal/src/components/conversas/{ConversaAberta,CaixaDeEnvio,EnvioDoOrcamento,ListaDeConversas,FiltroDaLista}.tsx
frontend/apps/internal/src/pages/{ConversasPage,FunilPage,OrcamentoCalculadoraPage,EventCreatePage}.tsx
```

**Decisão de estrutura**: o núcleo fica todo em `app/conversas/` (a conversa é a dona dos fatos novos). O único ponto
fora é a criação de evento: `agenda_write.api_create_event` só valida o `conversa_id` antes do Google e chama
`fechamento_ops.ligar_evento_a_conversa` depois do núcleo — é ali que a 348 grava `calendar_events.conversa_id`, sem
tocar a agenda de novo. Os cinco módulos novos mantêm `equipe_ops` (399 l.) e `funil_ops` (388 l.) sem crescer além
do necessário.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_349`, não `manto_local` (Princípio VIII / CLAUDE.md §4) | quatro features (348–351) abertas ao mesmo tempo, cada uma com migration sobre `d334b2c4e6f8`; o `manto_local` é compartilhado | aplicar `a349` no `manto_local` quebraria o `flask db upgrade` das outras sessões (memória "espelho próprio por feature") |
| Segundo `commit` depois do núcleo da criação de evento | `_create_event_core` comita sozinho e fala com o Google antes; o vínculo com a conversa entra depois | pôr o vínculo dentro do núcleo da agenda tocaria `app/calendar/routes.py` (docs/00 §7: não refatorar de passagem); a ficha já entra na mesma transação pelos `clients` da tela, o segundo commit só apaga a perda (e, na 348, grava a coluna) |

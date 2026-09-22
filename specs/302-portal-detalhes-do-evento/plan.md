# Plano de implementação: O artista passa a ver quando o evento termina, quando é o ensaio e de onde sai

**Branch**: `302-portal-detalhes-do-evento` | **Data**: 2026-09-22 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/302-portal-detalhes-do-evento/spec.md`

## Resumo

Tudo o que a feature mostra **já está no banco**. O trabalho é de exposição e de texto, não de
modelagem: o serializador único do portal (`_role_summary`) ganha duas chaves — `role_type` e um
bloco `before_event` —, três telas do portal passam a desenhar o que já recebiam, a tela interna do
evento ganha um aviso, e o mesmo defeito de rótulo é corrigido nas três superfícies em que o
artista lê a sua escalação (portal, e-mail de convite e mensagem de WhatsApp).

**Nenhuma migration. Nenhum endpoint novo. Nenhum portão alterado.**

Duas decisões carregam a maior parte do risco, e as duas são sobre o que **não** fazer:

1. **Não remover a lista de passados do payload da Agenda** nesta entrega, embora a tela pare de
   usá-la (FR-013a). O `manto-backend` e o `manto-frontend` são serviços separados no `render.yaml`
   e não trocam de contêiner juntos: existe uma janela de servidor novo com bundle velho, e o
   bundle velho faz `agenda.history.map(...)` — tela branca no celular do artista.
2. **Não ler os ensaios dentro do laço de serialização.** A relação é `lazy=True`; seriam N
   consultas. O módulo já tem o padrão a copiar, no mesmo arquivo.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy 2.0) no backend; TypeScript + React 18
(Vite) no frontend.

**Dependências principais**: Flask, SQLAlchemy; React, TanStack Query, Tailwind CSS, shadcn/ui
(`@manto/ui`), `@manto/api-client`. Nada novo entra.

**Armazenamento**: PostgreSQL — `manto-postgres` no Render; verificação contra `manto_local`.
**Migration: nenhuma.**

**Verificação**: `specs/302-portal-detalhes-do-evento/verify_302.py` contra `manto_local`;
`cd frontend && npm run typecheck`; `ruff check` nos tocados; telas abertas no Browser pane, o
portal em viewport mobile 375×812.

**Plataforma-alvo**: web — Render. O portal é superfície de smartphone.

**Metas de desempenho**: o número de consultas da agenda **não pode crescer com o número de
escalações**. Alvo: uma consulta adicional para a agenda inteira, independente de N. Cenário 13b
do verify mede isso.

**Restrições**:
- `start_at`/`end_at` são horário de parede de São Paulo, naive — nunca `new Date().toISOString()`
  (incidente de 2026-08-05, `docs/03`).
- `makeup_time`/`departure_time` são `String(5)` `"HH:MM"` e passam **crus**, sem virar `Date` em
  nenhum momento.
- Campo novo de payload nasce **opcional** no TypeScript até backend e bundle estarem na mesma
  versão; campo existente **não sai** do payload no mesmo ciclo em que sai da tela.
- Alvos de toque ≥44px, nada abaixo de 12px, sem rolagem horizontal de 320 a 430px.

**Escala/escopo**: 0 tabelas, 0 colunas, 0 endpoints novos; 3 endpoints com payload ampliado;
4 telas do portal, 2 componentes novos no portal, 2 seções da tela interna do evento, 1 e-mail e
1 mensagem de WhatsApp.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — ver o fim deste arquivo.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | O padrão de consulta agregada é o de `events_with_visible_figurino` (mesmo arquivo). `formatLongDate` já existe em `format.ts:45` e **não era usada** — vai para o cabeçalho da ficha de figurino. O tradutor do local de maquiagem nasce colado em `resolve_makeup_location` e serve portal **e** e-mail. `CacheLine.tsx` é o molde dos dois componentes novos. A ordenação de ensaios copia `agenda_read.py:777`. **Rejeitado por conferência**: promover o `formatRange` do app interno — formato incompatível (`05/07/2026 12:00 — 16:00` contra `28 de jul, 20:00 às 23:00`); ver R5 |
| II. Padrões de código | Type hints e docstrings Google em tudo que é novo; `MAKEUP_LOCATION_LABELS` e `DEPARTURE_DEFAULT_LOCATION` em UPPER_CASE no topo do módulo; funções abaixo de 30 linhas; `ruff check` nos tocados, `ruff format` em nenhum (não há arquivo Python novo); TS estrito, zero `any` |
| III. Camadas / API First | A regra do bloco mora em `portal_ops.py` (núcleo) e a tradução em `calendar/event_ops.py`; `app/api/portal_agenda.py` continua só orquestrando e **não muda**. Nenhum módulo novo em `app/api/`, logo nada a registrar em `app/api/__init__.py`. Nenhuma rota pública nova, logo nada em `BACKEND_PREFIXES` |
| IV. Não quebrar o que funciona | Backend **só aditivo**: nenhuma chave sai do payload nesta entrega (FR-013a). Pontos compartilhados conferidos: `_role_summary` é usado por `get_agenda` e `get_historico` — **só esses dois**, conferido por varredura no repositório. (Atenção: a docstring de `get_agenda` e três outras do portal dizem que existe um Jinja legado com consultas próprias. **Não existe mais**: `app/talent_portal/routes.py` tem 82 linhas e serve só a foto. Ver R14.); `PortalHistoricoItem extends PortalRole`, então o `tsc` acompanha; os contadores do `PortalShell` leem `pending_invites` e `rateable_event_ids`, nunca `history` |
| V. UI/UX com feedback | Sem estado novo de carregamento: o bloco vem no mesmo payload que já enche o card. O recolher/expandir é local e instantâneo. O aviso interno é calculado do payload que a página já tem — zero requisição nova |
| VI. Esteira (Nível 1) | Esteira completa; artefatos em `specs/302-portal-detalhes-do-evento/` |
| VII. Living Spec | Spec fechada em 16/16 antes deste plano; as quatro decisões do dono estão em `## Clarifications` |
| VIII. Verify antes do núcleo | `verify_302.py` é a fase Foundational do `tasks.md`, e falha pelos motivos certos: chaves ausentes no payload e o código `"manto"` cru no JSON |
| IX. Dinheiro BRL | N/A — a feature não toca valor. `CacheLine` continua como está |
| X. Mobile-first público | **Aplica.** O portal é a superfície de smartphone do projeto. O bloco novo é recolhido por padrão justamente para não empurrar cachê e figurino para fora da primeira tela; conferência obrigatória em 375×812 e varredura de 320 a 430px |
| XI. Framer Motion | Aplica ao recolher/expandir. Usar o padrão já presente no repositório e respeitar `useReducedMotion`; se a animação complicar o alvo de toque, entrega-se sem animação — o conteúdo é que importa |
| XII. Combobox / Maps | N/A — nenhuma lista longa e nenhum endereço a geocodificar. O endereço do ensaio é exibido como texto, já resolvido na gravação |
| XIII. RBAC declarado | Nenhum portão muda. **Dívida quitada de passagem**: `app/api/portal_figurino.py` é o único dos cinco módulos do portal sem declaração de RBAC no topo — ganha a declaração, na mesma forma em prosa que os outros quatro usam. O 403 daquele endpoint fica como está, por decisão registrada do dono, e vira dívida em `docs/05` |
| XIV. Config / efeito externo | Nenhuma env nova. **Atenção do verify**: semear ensaio pelo endpoint criaria evento no Google Agenda da empresa — as travas `_suppress_*` cobrem e-mail e convite, não isso. O verify insere o evento-filho direto no banco |
| Stack | Sem migration; sem Jinja novo; sem segredo. O portal **não tem mais** Jinja a preservar — as 20 rotas foram removidas na fase 2 e só `/portal/photo` ficou (`app/talent_portal/routes.py:1-14`). O que a feature não pode fazer é criar Jinja novo, e não cria |
| Operação e Deploy | Deploy comum: não toca `startCommand`, `render.yaml`, volume nem migration; sem passo manual no Shell do Render. Vale a janela de ~1 min de 502 — publicar em lote, fora do horário |

**Resultado do gate (pré-Phase 0)**: aprovado, sem violação a justificar. A tabela de
Rastreamento de complexidade fica vazia.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/302-portal-detalhes-do-evento/
├── spec.md
├── plan.md                    # este arquivo
├── research.md                # Phase 0 — as decisões e o que foi rejeitado
├── data-model.md              # Phase 1 — nada muda no banco; o que muda é a leitura
├── quickstart.md              # Phase 1 — como provar que funciona
├── contracts/api-endpoints.md # Phase 1 — os três payloads
├── checklists/requirements.md
├── tasks.md                   # /speckit-tasks
└── verify_302.py              # Princípio VIII — antes do núcleo
```

### Código

```text
app/constants.py                                    # DEPARTURE_DEFAULT_LOCATION
app/calendar/event_ops.py                           # MAKEUP_LOCATION_LABELS + makeup_location_label
app/email_service.py                                # rótulo Função/Personagem + local traduzido
app/talent_portal/portal_ops.py                     # _antes_do_evento + _role_summary + selectinload
app/api/portal_figurino.py                          # só a declaração de RBAC (sem end_at: FR-014 pede nome e DATA)

frontend/apps/portal/src/lib/portalAgenda.ts        # tipos novos (before_event OPCIONAL)
frontend/apps/portal/src/lib/portalFigurino.ts      # (sem mudança — o tipo já bastava)
frontend/apps/portal/src/lib/format.ts              # formatDateTimeRange
frontend/apps/portal/src/components/RoleLine.tsx    # NOVO — Personagem: / Função:
frontend/apps/portal/src/components/AntesDoEvento.tsx  # NOVO — o bloco recolhível
frontend/apps/portal/src/pages/PortalAgendaPage.tsx    # faixa, bloco, rótulo, seção Histórico SAI
frontend/apps/portal/src/pages/PortalConvitesPage.tsx  # faixa, bloco, rótulo
frontend/apps/portal/src/pages/PortalHistoricoPage.tsx # rótulo
frontend/apps/portal/src/pages/PortalFigurinoPage.tsx  # nome e data do evento

frontend/apps/internal/src/components/EventDetail/ResumoSection.tsx    # chip "Logística"
frontend/apps/internal/src/components/EventDetail/LogisticaSection.tsx # aviso na seção
frontend/apps/internal/src/lib/eventDetail.ts                          # WhatsApp: rótulo + local
frontend/apps/internal/src/components/EventDetail/CastingSection.tsx   # passa o local traduzido
```

**Decisão de estrutura**: o bloco é um componente do **portal**, não de `@manto/ui` — nenhum outro
app o usa, e `@manto/ui` é para o que é genuinamente comum (foi assim que `formatRelativeDay` e
`formatShortDate` subiram na feature 197). `format.ts` continua sendo a fonte única de data do
portal, e é onde o formatador de faixa nasce.

## Rastreamento de complexidade

> Vazio: o Constitution Check passou sem violação.

## Constitution Check — reavaliação pós-Phase 1

Refeito depois de `research.md`, `data-model.md`, `contracts/` e `quickstart.md`. **Sem violação
nova.** Três pontos que a Phase 1 mudou em relação à avaliação inicial:

- **Princípio I ficou mais forte, não mais fraco.** A pesquisa encontrou três reusos que a
  avaliação inicial não tinha: a ordenação de ensaios (`agenda_read.py:777`), `formatLongDate` já
  escrita e sem uso, e o literal `"Manto Produções"` repetido em três lugares — que vira constante
  e apaga a repetição em vez de acrescentar a quarta.
- **Princípio IV ganhou uma regra escrita** que não estava no gate inicial: o par FR-013a/FR-013b
  (a janela de deploy em duas partes). Está no contrato, não só no plano.
- **Princípio XIII**: o plano quita a declaração `RBAC:` faltante e **não** mexe no 403, por
  decisão do dono. A conformidade pendente fica nomeada em `docs/05`, que é o lugar dela.

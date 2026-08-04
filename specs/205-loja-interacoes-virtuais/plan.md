# Implementation Plan: Loja de Interações Virtuais

**Branch**: `205-loja-interacoes-virtuais` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/205-loja-interacoes-virtuais/spec.md`

## Summary

Canal de e-commerce B2C self-service que vende chamadas de vídeo de 10 minutos e vídeos gravados com
Personagens do catálogo, com checkout assíncrono pela InfinitePay e entrega operacional automática.

**Abordagem técnica**: seis tabelas novas (`virtual_*`) e um núcleo de negócio puro
(`app/marketing/virtuais_ops.py`) que orquestra tudo. Nada de infraestrutura nova: o presente cai na
Fila de Impressão 3D existente, a venda vira `CalendarEvent` com escala de talento, a sala é um
Google Meet criado pela Calendar API já autenticada, o vídeo vai para o Google Drive pela conta de
serviço já usada no Figurino, e os avisos saem pelo `email_service` que já roda.

O ponto crítico não é o CRUD — é a **correção sob concorrência e reentrega**: um horário nunca pode
ser vendido duas vezes, e uma notificação de pagamento reentregue nunca pode duplicar evento, escala,
pendência de impressão ou baixa de estoque. Isso é resolvido com `with_for_update()` no slot, chaves
únicas em `order_nsu`/`transaction_nsu`, e uma regra inegociável: **o webhook não decide nada; quem
decide é a reconsulta da cobrança na operadora**.

## Technical Context

**Language/Version**: Python 3.14 (backend) · TypeScript 5 / React 18 (frontend)

**Primary Dependencies**: Flask + SQLAlchemy + Alembic · React + Vite + Tailwind + shadcn/ui +
Framer Motion + TanStack Query · `google-api-python-client` (Calendar, já no projeto) ·
`requests` (InfinitePay — sem SDK)

**Storage**: PostgreSQL (`manto_local` em dev, Railway em produção) · `app/storage.py` para capa da
campanha e para os vídeos gravados — estes servidos só por endpoint validado, nunca por URL direta

**Testing**: `specs/205-loja-interacoes-virtuais/verify_205.py` contra `manto_local` · `npx tsc
--noEmit` · `ruff check`

**Target Platform**: navegador móvel (superfície pública) e desktop (interno); backend Linux/Railway

**Project Type**: SPA desacoplada — Flask como API JSON estrita + três apps React no monorepo

**Performance Goals**: reserva confirmada em < 1s percebido; landing utilizável em 4G; a fila de
produção responde a filtro sem recarregar a página

**Constraints**: 320–430px sem rolagem horizontal · toque ≥ 44px · **dinheiro sempre `Numeric/Decimal`
no PostgreSQL e sempre `@manto/money` no React** (ver regra abaixo) · nenhum segredo no navegador ·
webhook idempotente sob reentrega ilimitada

### Regra monetária desta feature (Princípio IX — NÃO-NEGOCIÁVEL)

A InfinitePay trabalha em centavos inteiros. Isso é característica **do fornecedor**, não do nosso
domínio, e não pode vazar para dentro do sistema:

1. **Persistência**: toda coluna monetária das tabelas `virtual_*` é `Numeric(12, 2)` — preços da
   campanha, valores congelados do pedido, total e valor de devolução. Nenhuma coluna `*_cents`,
   nenhum `Integer` representando dinheiro. É o mesmo tipo que `CalendarEvent.sale_value` já usa, e
   é o que impede a feature de conviver com duas representações de dinheiro.
2. **Python**: o núcleo opera em `Decimal` de ponta a ponta. Nada de `float` para dinheiro.
3. **JSON da API**: os payloads trafegam valores decimais em reais (ex.: `190.00`), nunca centavos.
   Nenhum campo de API termina em `_cents`.
4. **Fronteira do fornecedor**: a conversão para centavos existe **exclusivamente** dentro de
   `app/integracoes/infinitepay_client.py`, na entrada e na saída — inclusive na conferência do
   `paid_amount` da reconsulta, que volta em centavos e é convertido antes de comparar com o total.
   Um único arquivo sabe que centavos existem.
5. **React**: exibição e digitação passam obrigatoriamente por `@manto/money` — `formatBRL` para
   ler, `MoneyInput` para digitar, `parseBRL` para converter de volta. Proibido formatar moeda à
   mão, usar `toFixed`, `Intl.NumberFormat` local ou qualquer máscara própria em qualquer tela desta
   feature, pública ou interna.

**Scale/Scope**: campanha sazonal — dezenas a poucas centenas de pedidos por campanha, com pico de
acesso concentrado no lançamento (é o pico que justifica o lock pessimista e o anti-abuso)

## Constitution Check

*GATE: passou antes da Fase 0 e revalidado após a Fase 1.*

| Princípio | Situação | Como o plano cumpre |
|---|---|---|
| I — Reutilizar antes de criar | ✅ | Reusa `CatalogCharacter`, `Acervo3DItem`, `Event3DGift`, `CalendarEvent`/`EventRole`, `email_service`, `storage`, `drive_service`, `calendar/service`, `impressoes3d_ops.serialize_gift`. `GoogleAddressInput` é **promovido** a `@manto/ui`, não copiado |
| II — Padrões Python/TS | ✅ | Type hints e docstrings Google style; funções ≤ 30 linhas; sem `any`; constantes em `constants.py` |
| III — Arquitetura em camadas | ✅ | Rotas só validam, chamam `virtuais_ops` e serializam. O webhook valida segredo e delega — zero regra na rota (diretriz 1 do usuário) |
| IV — Não quebrar o que funciona | ⚠️ | Toca pontos compartilhados: `insert_event`, `media.py`, escopo do Drive, agregadores financeiros. Ver Complexity Tracking |
| V — UI/UX com feedback | ✅ | TanStack Query com loading/erro/sucesso; botão de reservar nunca "morto" nem duplica pedido; validação destaca campo e preserva o digitado |
| VI — Esteira SDD completa | ✅ | specify → clarify → **plan** → checklist → tasks → analyze → implement → converge |
| VII — Living Spec | ✅ | A spec foi corrigida **antes** deste plano quando a InfinitePay contrariou duas decisões do clarify (seção "Revisões durante o `/speckit.plan`") |
| VIII — Test-First | ✅ | `verify_205.py` especificado em [quickstart.md](./quickstart.md); suas tarefas vêm antes das de implementação |
| IX — Valores em BRL | ✅ | `Numeric(12,2)` no banco, `Decimal` no Python, reais no JSON; centavos só dentro do cliente da InfinitePay; exibição e digitação exclusivamente por `@manto/money` (ver "Regra monetária desta feature") |
| X — Público é mobile-first | ✅ | 320–430px, toque ≥ 44px, sem texto < 12px, conferido em viewport antes de "pronto" |
| XI — Movimento com propósito | ✅ | Framer Motion nas etapas do checkout e na fila, respeitando `useReducedMotion()` |
| XII — Comboboxes e autocomplete | ✅ | Upsell 3D via `Combobox` + `AvatarThumb` quadrado; endereço via `GoogleAddressInput`; chave do Google só no servidor; debounce 350ms / 3 caracteres |

**Stack**: nenhuma proibição violada — sem Jinja2, sem `render_template`, sem CSS solto, sem
manipulação direta de DOM. Migration manual em Alembic. Segredos em `SiteSetting`/`.env`.

## Project Structure

### Documentation (this feature)

```text
specs/205-loja-interacoes-virtuais/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões e achados de fornecedor
├── data-model.md        # Fase 1 — 6 tabelas novas + constantes
├── quickstart.md        # Fase 1 — roteiro de verificação (V1–V6)
├── contracts/
│   └── virtuais-api.md  # Fase 1 — contrato dos endpoints
├── checklists/
│   └── requirements.md
├── spec.md
└── tasks.md             # Fase 2 (/speckit.tasks — não criado aqui)
```

### Source Code (repository root)

```text
app/
├── models.py                          # + 6 modelos virtual_* ; + campos em SiteSetting
├── constants.py                       # + EVENT_TYPE_VIRTUAL e os ciclos de vida
├── email_service.py                   # + 3 send_*_email (confirmação, vídeo pronto, cancelamento)
├── marketing/
│   └── virtuais_ops.py                # NÚCLEO — campanhas, slots, reserva, efetivação, produção
├── integracoes/
│   ├── __init__.py
│   └── infinitepay_client.py          # criar_link_pagamento / consultar_pagamento
├── calendar/service.py                # ESTENDE insert_event com conferenceData
├── calendar/event_ops.py              # sync passa a ignorar VIRTUAL/platform (FR-029a)
└── api/
    ├── virtuais_public.py             # landing, horários, reservar, pedido, verificar, vídeo
    ├── virtuais_webhook.py            # POST /api/webhooks/infinitepay/<token>
    ├── virtuais_read.py               # admin: campanhas, fila de produção, devoluções
    └── virtuais_write.py              # admin: CRUD, slots, status, upload de vídeo

migrations/versions/
└── <rev>_loja_interacoes_virtuais.py  # down_revision = "b7d4f81a6e0c"

frontend/
├── packages/ui/src/
│   └── google-address-input.tsx       # PROMOVIDO de apps/internal (fonte única)
├── apps/public/src/pages/
│   ├── CampanhaVirtualPage.tsx        # /v/:slug — landing + checkout mobile-first
│   └── PedidoVirtualPage.tsx          # /v/pedido/:token — acompanhamento
└── apps/internal/src/pages/
    ├── VirtuaisCampanhasPage.tsx      # gestão de campanhas
    ├── VirtuaisCampanhaFormPage.tsx   # textos, preços, slots, acervo liberado
    └── FilaProducaoMidiaPage.tsx      # espelha a Fila 3D (feature 200)

specs/205-loja-interacoes-virtuais/verify_205.py
```

**Structure Decision**: monorepo existente, sem estrutura nova. O núcleo vai em
`app/marketing/virtuais_ops.py` (diretriz do usuário) e o cliente da operadora fica isolado em
`app/integracoes/` — um pacote novo, porque `infinitepay_client.py` não pertence a nenhum domínio de
negócio e vai ser reusado por qualquer venda futura. A landing usa `apps/public`, servido sob
`/catalogo` em produção, então a URL real é `.../catalogo/v/<slug>` ([research.md](./research.md) R6).

## Ordem de implementação sugerida

Fatias verticais na ordem de prioridade da spec, cada uma verificável sozinha:

1. **Fundação** — constantes, modelos, migration, `verify_205.py` esqueleto.
2. **US1 (P1)** — campanhas e slots: `virtuais_ops` + admin API + telas internas. V1 verde.
3. **US2 (P2)** — landing, checkout, soft lock, criação do link. V2 verde. Aqui entram a promoção do
   `GoogleAddressInput` e o autocomplete público. **Inclui a página do pedido em versão mínima**
   (status, horário, valor), porque é para onde a família volta do checkout — ver regra abaixo.
4. **US3 (P3)** — webhook, `payment_check`, efetivação, evento + Meet + escala, e-mails, devoluções.
   V3 verde. **É a fatia mais arriscada; nada depois dela começa antes de V3 passar.** A página do
   pedido ganha aqui o estado "confirmado", a sala e a atualização automática (FR-035a).

### Rotinas de segundo plano (FR-057)

As varreduras desta feature — expiração de reservas, retentativas pendentes e alerta de prazo de
vídeo — seguem o padrão que a aplicação já usa: threads daemon iniciadas em `create_app()`, ao lado
de `_start_talent_sync`, `_start_calendar_sync` e `_start_review_cleanup`
([app/\_\_init\_\_.py:119](app/__init__.py:119)). Nada de agendador externo, nada de dependência nova.

O padrão a copiar, item por item:

- intervalo em `app.config` (ex.: `VIRTUAL_SWEEP_INTERVAL`), não hardcoded;
- guarda de dev (`FLASK_ENV == "development"` + `WERKZEUG_RUN_MAIN`) para não rodar em duplicidade
  no reloader;
- `with app.app_context()` dentro do laço;
- `except Exception` com log, **nunca deixando a thread morrer** (FR-057b);
- **claim atômico no banco antes de agir**, no modelo de `_claim_auto_sync`
  ([app/calendar/sync.py](app/calendar/sync.py)) — obrigatório aqui: o Railway roda vários workers
  gunicorn, e dois processos expirando a mesma reserva ao mesmo tempo é exatamente a corrida que o
  soft lock existe para evitar (FR-057a).

O `sync_worker.py` (cron externo) permanece como está e não é usado por esta feature.

### Timeout das chamadas à operadora (CHK050)

`10s` para conectar, `30s` para ler. Estourou qualquer um dos dois, a chamada é **indisponível** —
nunca "não pago". É esse limite que dá critério à distinção exigida por FR-027d.

### Política de retry (FR-056)

Uma implementação só, aplicada a toda chamada externa que pode falhar por indisponibilidade:
**3 tentativas nos minutos 0, 1 e 2**; falhada a terceira, a falha é definitiva, registrada e
sinalizada. Vale para `payment_check`, envio de e-mail e geração da sala.

Consequência: a tolerância na expiração do soft lock é de até 2 minutos, e o pior caso de devolução
de um horário ao estoque é de **17 minutos** (SC-005). O intervalo curto é intencional — protege
contra vender horário já pago sem prender estoque no pico da campanha.

### Regra de sequenciamento da página do pedido

A página do pedido (`/v/pedido/:token`) é construída em **três incrementos**, e a rota só é
registrada junto com o componente — registrar rota apontando para componente inexistente quebra o
build do `apps/public`:

| Fase | O que a página tem |
|---|---|
| US2 | rota + componente mínimo: status, horário, valor, contador do soft lock. É o destino do retorno do checkout (`redirect_url`) desde a primeira venda |
| US3 | estado "confirmado", link da sala, atualização automática enquanto a confirmação não chega (FR-035a) |
| US5 | validação dupla por telefone (FR-044a–c) e player do vídeo (FR-038e) |

Motivo: a família volta do pagamento a partir da **primeira** venda da US2. Deixar a página inteira
para a US5 significaria que, durante duas fases, quem paga cai no vazio.
5. **US4 (P4)** — upsell 3D e injeção na Fila de Impressão. V4 verde.
6. **US5 (P5)** — Fila de Produção e upload no Drive. V5 verde.
7. **Financeiro** — segregação de canal nos agregadores. V6 verde.
8. **Fechamento** — docs vivos, `tsc`, `ruff`, `/speckit.converge`.

## Complexity Tracking

Pontos compartilhados que este plano toca — cada um exige verificar todos os dependentes antes de
declarar pronto (Princípio IV).

| Mudança | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Estender `calendar/service.insert_event` com `conferenceData` | Diretriz proíbe Zoom/Twilio/Daily; a sala tem que sair da Calendar API | Criar `insert_event_with_meet` paralelo duplicaria autenticação e tratamento de erro (Princípio I) |
| Excluir `VIRTUAL`/`platform` de todos os caminhos da sincronização | Sem isso a sincronização corrompe evento já pago (FR-029a) | Filtrar só na importação deixaria atualização e remoção reescrevendo a venda |
| Servir o vídeo por endpoint validado em vez da URL do storage | FR-038e — dado de criança não pode depender de o link não vazar | `save_file` + URL pública é o caminho padrão do repo, mas aqui expõe o vídeo a quem tiver a URL |
| Endpoint público de autocomplete de endereço | O existente exige login; o checkout é anônimo | Abrir o endpoint atual removeria a proteção de quem já usa; a variante nasce com throttle próprio |
| Promover `GoogleAddressInput` para `@manto/ui` | `apps/public` não alcança `apps/internal` | Copiar o componente violaria o Princípio I frontalmente |
| Filtrar `event_type='VIRTUAL'` nos agregadores financeiros | FR-054 exige KPIs e comissão intactos | Não segregar distorceria ticket médio e geraria comissão indevida |
| Pacote novo `app/integracoes/` | Isola o contrato de um fornecedor com documentação incompleta | Espalhar chamadas HTTP pelo `virtuais_ops` deixaria a mudança de contrato difusa |

## Desvios conscientes das diretrizes recebidas

Duas instruções da mensagem original foram implementadas em espírito, não ao pé da letra. Ambas
estão detalhadas em [research.md](./research.md).

**1. `google_html_link` não é o link entregue à família (R2).**
A diretriz pede persistir `google_html_link` e disponibilizá-lo na página de acompanhamento. Esse
campo já existe e já significa outra coisa — "link do evento no site do Google Calendar", capturado
na sincronização ([models.py:215](app/models.py:215)) e usado pelo botão "Editar no Google Agenda"
(feature 117). Além disso, ele **abre o Google Calendar e exige login com acesso ao calendário**,
que a família não tem. O plano persiste os dois: `google_html_link` segue como sempre foi, e o link
da sala (`hangoutLink`) vai em `VirtualOrder.meet_url`, que é o exposto à família. A fonte continua
sendo a Calendar API, como pedido.

**2. "Estorno automático" não é implementável com a InfinitePay (R1).**
A documentação pública da operadora descreve criação de link, webhook e `payment_check`, mas **não
publica API de estorno** — e também **não assina os webhooks**, o que inviabiliza a metade
"validar assinatura" da decisão tomada no `/speckit.clarify`. A spec foi corrigida antes deste plano
(Princípio VII). O que fica:

- confiança vem da reconsulta obrigatória via `payment_check`, com o webhook rebaixado a gatilho e o
  endereço protegido por segredo revogável no path;
- a devolução é aberta, rastreada e cobrada até a conclusão, mas executada por uma pessoa;
- o conflito passa a ser **prevenido**: antes de devolver um slot expirado ao estoque, o sistema
  reconsulta a cobrança e efetiva a venda se ela tiver sido paga (FR-041a).

Se a InfinitePay expuser estorno por API mediante contrato, o único ponto a mudar é
`infinitepay_client.py` — o resto do fluxo já está preparado para marcar a devolução como concluída.

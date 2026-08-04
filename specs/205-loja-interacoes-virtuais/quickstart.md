# Quickstart — Loja de Interações Virtuais (feature 205)

Como rodar e **provar** que a feature funciona. Conforme o Princípio VIII (Test-First), o roteiro de
verificação existe antes do código: as tarefas de `verify_205.py` vêm antes das de implementação em
`tasks.md`.

Toda verificação roda contra a cópia local do banco de produção (`manto_local`), **nunca** contra o
SQLite vazio de `instance/`.

## Pré-requisitos

```bash
python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
```

Banco local de produção:

```bash
.\scripts\db\run-local.ps1
```

Configuração necessária (via `SiteSetting` ou `.env` — nunca no código):

| Chave | Para quê |
|---|---|
| `infinitepay_handle` | criar links e reconsultar cobranças |
| `infinitepay_webhook_token` | segredo do path do webhook |
| Google OAuth conectado | criação do evento e da sala do Meet (`/google/connect`) |

## Migration

```bash
flask db upgrade
```

Confere as seis tabelas novas:

```bash
python -c "from app import create_app, db; app=create_app(); ctx=app.app_context(); ctx.push(); print([t for t in db.inspect(db.engine).get_table_names() if t.startswith('virtual_')])"
```

## Subir para conferir na tela

Dev server pelo `.claude/launch.json` (nunca por `Bash`). O app público roda em `/` no dev e sob
`/catalogo` em produção — a landing fica em `/v/<slug>`.

```bash
npx tsc --noEmit
```

Precisa passar limpo em `apps/internal` e `apps/public` (Portão de Qualidade).

---

## Roteiro de verificação — `specs/205-loja-interacoes-virtuais/verify_205.py`

Script de verificação funcional da API contra `manto_local`, no padrão dos `verify_*.py`
anteriores. Cada cenário abaixo é um caso do script.

### V1 — Campanha (US1)

1. Cria campanha a partir de um `CatalogCharacter` ativo → nasce `rascunho`, invisível no público.
2. Gera horários `14:00–18:00` → 24 slots de 10 min. **Reexecuta o mesmo comando** → `created: 0`,
   `skipped: 24` (FR-004 é idempotente).
3. Publica → landing pública responde `200`.
4. Tenta remover slot vendido → `409`.

### V2 — Reserva e soft lock (US2)

1. Reserva um horário → `201`, `locked_until ≈ agora + 15min`; o slot some de `/horarios`.
2. **Concorrência**: duas reservas simultâneas no mesmo slot → exatamente uma `201`, outra `409`.
   Este é o caso que justifica `with_for_update()`; rodar com duas conexões de verdade, não em
   sequência.
3. Segunda reserva com o mesmo telefone → `429` com `existing_order_token` (FR-020a).
4. Estourar o teto por origem → `429` (FR-020b), e o slot continua disponível para os outros.
5. Forçar `locked_until` para o passado e ler `/horarios` → o slot reaparece sem varredura ter
   rodado (expiração preguiçosa).

### V3 — Efetivação idempotente (US3) — **o caso mais importante**

1. Pedido `aguardando`; dispara o webhook com `payment_check` respondendo `paid: true`.
   → pedido `pago`; `CalendarEvent` com `event_type='VIRTUAL'` e `sale_value`; `EventRole`
   pré-escalado; `VirtualMediaDelivery` `pendente`; e-mail de confirmação registrado.
2. **Dispara o mesmo webhook mais 4 vezes** → nada duplica (contagens de evento, escala, presente
   3D e `recorded_sold` idênticas) e todas respondem `200`. SC-006.
3. Webhook com token errado → `404`; nada criado; notificação registrada com `secret_ok=False`.
4. Webhook autêntico com `payment_check` devolvendo `paid: false` → venda **não** efetivada,
   `recheck_result='unpaid'`, equipe sinalizada (FR-027c).
5. `payment_check` devolvendo valor divergente do `total_value` → `recheck_result='divergent'`,
   nada criado.
6. `payment_check` indisponível (timeout) → `outcome='retido'`, pedido intacto para nova tentativa
   (FR-027d). **Não** pode virar venda nem cancelamento.
7. Slot já vendido a outro pedido → pedido `cancelado`, `VirtualRefundRequest` `pendente`, e-mail de
   cancelamento, **zero** evento e **zero** pendência 3D (SC-012).
8. Expiração com cobrança paga → antes de liberar o slot, a reconsulta detecta o pagamento e a
   venda é efetivada (FR-041a). É o que mantém o conflito raro.

### V4 — Presente 3D (US4)

1. Pedido com `gift_item_id` → após efetivar, existe `Event3DGift` `pendente` ligado ao evento.
2. O presente aparece na Fila de Impressão 3D existente sem alteração naquela tela.
3. Campanha sem acervo liberado → payload público sem `gift_items`; enviar `gift_item_id` → `400`.

### V5 — Produção e entrega (US5)

1. `/api/virtuais/producao` traz, na mesma linha, horário/modalidade, nome, dicas e status do
   presente (FR-046).
2. `finalizado` sem vídeo numa entrega gravada → `400` no campo `video`. Enviar qualquer status fora
   de `pendente`/`gravando`/`finalizado` → `400` (FR-048a).
3. Upload do vídeo → guardado no storage, entrega `finalizado`, e-mail disparado, vídeo assistível
   na página do pedido após a validação dupla.
4. Falha simulada ao guardar → entrega **não** finaliza, `last_upload_error` preenchido, nenhum
   e-mail à família (FR-038c).

### V6 — Privacidade e validação dupla (CHK070 / FR-038e, FR-044a–c)

1. `GET /pedidos/<token>` sem validar → devolve só status, horário e valor. **Nenhum** nome de
   criança, endereço, sala ou vídeo no payload.
2. `POST /verificar` com telefone errado → `401` com `attempts_left`; repetir até o limite → `429`
   com `blocked_until` (FR-044b).
3. `POST /verificar` com telefone certo → dados completos e sessão de acesso aberta.
4. `GET /video` sem sessão → `401`. Com sessão → o vídeo toca, com `Range` funcionando.
5. **Varredura de vazamento**: nenhum payload da API pode conter o caminho do arquivo no storage, e
   o `subfolder` dos vídeos não pode ser alcançável pelo servidor estático. É este passo que separa
   privacidade real de privacidade aparente.
6. Sessão expirada após 30 min de inatividade → `/video` volta a `401` (FR-044c).
7. Vídeo acima de **250 MB** ou com extensão não suportada → `400` explicando o motivo (FR-038d).

### V7 — Sincronização não toca em evento virtual (CHK062 / FR-029a, FR-029b)

1. Efetiva vendas virtuais; guarda id, título, horário e vínculos dos eventos gerados.
2. Roda a sincronização **completa** com a agenda externa.
3. Nenhum evento `VIRTUAL` foi alterado, duplicado ou removido; contagens e campos idênticos (SC-019).
4. Remove o evento direto na agenda externa e sincroniza de novo → o pedido pago segue intacto e a
   equipe é sinalizada (FR-029b).

Rodar contra **todos** os caminhos da sincronização, não só o de importação — um caminho esquecido
passa despercebido justamente por não fazer nada visível.

### V8 — Tolerância e idempotência de aviso (CHK017 / CHK027)

1. Simula operadora indisponível na expiração → horário retido enquanto as **3 tentativas** (minutos
   0, 1 e 2) acontecem (FR-018a, FR-056); só então liberado, com `expired_unverified` marcado
   (FR-018b). Conferir que a quarta tentativa não existe.
2. Operadora volta a responder na 2ª ou 3ª tentativa confirmando pagamento → venda efetivada,
   horário não liberado.
3. Reentrega o aviso de pagamento 5 vezes → **um** e-mail de confirmação registrado e enviado
   (SC-020). Este é o caso que a restrição `UNIQUE(order_id, kind)` sustenta.
4. Falha no meio da efetivação após gravar o aviso → transação desfeita, registro do aviso também
   desfeito, e a nova tentativa consegue enviar (FR-028b).

### V9 — Financeiro segregado (US1 / FR-052–055)

1. Antes: guarda volume de eventos, ticket médio e base de comissão do mês.
2. Efetiva 10 vendas virtuais.
3. Depois: os três indicadores **não mudaram**; o DRE do período subiu exatamente a soma das vendas;
   o painel da campanha bate com o DRE (SC-014).

Este é o caso que pega agregador esquecido — se algum painel não filtrar `'VIRTUAL'`, V9 falha.

---

## Conferência manual (mobile-first, Princípio X)

Na Browser pane, viewport 375px e depois 320px:

- landing → formulário → horário → upsell → checkout, sem rolagem horizontal;
- alvos de toque ≥ 44px nas ações principais; nenhum texto informativo < 12px;
- contador do soft lock visível durante o checkout (FR-019);
- erro de validação destaca o campo, leva o foco e **não** apaga o que foi digitado (FR-025);
- preços em `R$ 1.234,56` em toda tela (Princípio IX);
- transições do Framer Motion entre etapas, respeitando `useReducedMotion()` (Princípio XI).

## Portões de qualidade (antes de "pronto")

- [ ] `npx tsc --noEmit` limpo em `apps/internal` e `apps/public`
- [ ] `ruff check app/` limpo
- [ ] `verify_205.py` verde contra `manto_local`
- [ ] Migration manual criada e aplicada
- [ ] `docs/01_SISTEMA_E_BANCO.md`, `docs/02_MAPA_DE_PAGINAS_E_UX.md` e `docs/03_HISTORICO_MUTACOES.md` atualizados
- [ ] `/speckit.converge` executado

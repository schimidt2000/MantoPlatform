<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 323 — a nota pedida chega ao Superadmin

**Branch**: `323-nota-pedida-ao-superadmin` | **Data**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/323-nota-pedida-ao-superadmin/spec.md`

## Resumo

Ligar "Precisa de nota fiscal" passa a pedir a nota em **todas** as portas da venda (criação,
"Editar tudo", card Comercial), com quem pediu e quando. A venda guarda os dados que a emissão
precisa (documento do tomador, ISS retido, município, referência, observações). O Superadmin vê o
painel **Notas a emitir** na tela inicial (urgente), copia a discriminação montada e insere o PDF ali
mesmo; cada Superadmin recebe um e-mail por nota, no formato da 319. Núcleo novo em
`app/calendar/pedido_de_nota_ops.py`; nenhuma rota nova.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, react-hook-form + zod (formulário do evento), Tailwind CSS, `@manto/ui` (`SectorPanel`,
`CopyButton`, `Button`), `@manto/api-client`, `@manto/money`

**Armazenamento**: PostgreSQL; 5 colunas em `calendar_events`, 3 em `event_invoices` (aditiva)

**Verificação**: `specs/323-nota-pedida-ao-superadmin/verify_323.py` contra `manto_local`;
`cd frontend && npm run typecheck`; tela aberta (criação, "Editar tudo", card Comercial, Home do
Superadmin) em desktop e 375×812

**Plataforma-alvo**: app interno (staff); o dono usa a Home no celular

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o bloco da Home é uma consulta (notas a emitir + evento + cliente
contratante + parcelas, carregados juntos); dezenas de linhas no máximo

**Restrições**: campo novo do payload opcional no React; e-mail depois do commit, nunca com a trava
do evento na mão; Jinja não muda

**Escala/escopo**: 1 migration (8 colunas), 1 módulo `_ops` novo, 3 portas de escrita com a chave
`nota`, 1 bloco novo no dashboard, 1 e-mail novo, 3 telas React tocadas + 1 painel novo

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 — sem violação.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `EventInvoice` e o PATCH de nota da 069/251 (inserir PDF); `travar_evento` via `estado_da_venda`; `SectorPanel`, `CopyButton`, padrão de upload de `SemComprovante`; e-mail sobre `_info_row`/`_info_box`/`_btn`/`_html_wrap` da 319; `useUpdateNotaFiscal` (existe sem uso) |
| II. Padrões de código | type hints/docstrings; funções ≤ ~30 linhas; constantes no topo; `ruff check` nos tocados, `ruff format` só no `_ops` novo e no verify |
| III. Camadas / API First | regra em `pedido_de_nota_ops.py` (sem `flask.request`); views só leem `body["nota"]`, validam pelo `_ops` e serializam; sem rota nova, sem `BACKEND_PREFIXES` |
| IV. Não quebrar o que funciona | aditiva; chave `nota` opcional (ausente = não mexe); legado sem "pedida por" nunca dispara e-mail; 069 (card do Financeiro, PATCH de nota) intactos |
| V. UI/UX com feedback | `Button loading` no "Inserir nota"; erro do campo via `ApiRequestError.fields` (`nota_tomador_doc`, `nota_municipio`) sem apagar o formulário |
| VI. Esteira (Nível 1) | migration + 2 domínios (agenda, dashboard/e-mail): esteira completa |
| VII. Living Spec | spec ajustada nesta fase (FR-005 e premissa da discriminação, research R4/R6) |
| VIII. Verify antes do núcleo | `verify_323.py` na fase Foundational; cenários 2–3 falham no código atual |
| IX. Dinheiro BRL | `formatBRL` no painel; `format_brl` (`app/money.py`) no e-mail; `Numeric` no banco |
| X. Mobile-first público | não toca superfície pública; a Home é conferida em 375×812 porque o dono a usa no celular |
| XI. Framer Motion | os campos da nota abrem com o mesmo `AnimatePresence` + `useReducedMotion` do `ValoresBlock` |
| XII. Combobox / Maps | município é texto livre (nenhuma lista de municípios no sistema; 5.570 opções não cabem num select) |
| XIII. RBAC declarado | sem endpoint novo; bloco `notas_a_emitir` só Superadmin real sem "Ver como"; portas da venda mantêm `_can_create_event`; inserir PDF mantém `_can_manage_sale`; linha em `docs/01` §4.3 |
| XIV. Config / efeito externo | `NOTA_DADOS_BANCARIOS` em `app/config.py` com default real; e-mail pelo `_send` (travas `_emails_enabled` e 269b); link pelo `PLATFORM_BASE_URL` como a 319 |
| XV. Texto por superfície | interno operacional: "Dados da nota", "CNPJ ou CPF do tomador", "ISS retido pelo tomador", "Município da prestação", "Referência do cliente", "Observações para a nota", "Inserir nota", "Copiar discriminação", estado vazio "Nenhuma nota a emitir."; e-mail no tom da 319 |
| Stack | migration à mão, `down_revision = c322a7e1b9d4`; sem Jinja novo; sem segredo |
| Operação e Deploy | não toca `startCommand`; migração aditiva (sem ensaio destrutivo) |

## Desenho

### Backend

1. **Migration** `d323b5a1c0e7_nota_pedida.py` + colunas em `app/models.py` (data-model.md).
2. **`app/calendar/pedido_de_nota_ops.py`** (novo):
   - `DadosDaNota` (dataclass) e `NotaInvalida(fields)`; `ler_dados_da_nota(raw) -> DadosDaNota | None`
     (normaliza dígitos, valida 11/14, exige município com ISS retido, corta tamanhos).
   - `gravar_dados_da_nota(event, dados)` — grava as 5 colunas e completa o documento do cliente
     contratante se vazio.
   - `dados_mudariam(event, dados) -> bool` — para o 409 do cancelado no PATCH em bloco.
   - `acompanhar_pedido(event, *, pedida_por_id)` — chamado com o evento travado: cria a nota a
     emitir se ligado e sem nenhuma nota; exclui as a emitir se desligado; nada no cancelado/satélite.
   - `carimbar_pedido_da_criacao(event, *, pedida_por_id)` — na criação, carimba a nota que
     `_create_event_row` já criou.
   - `avisar_notas_pedidas(event_id)` — reivindica (`UPDATE … RETURNING`), commita e chama
     `send_async(send_nota_pedida_email, nota, superadmins)`; nunca levanta (loga).
   - `discriminacao(event, nota)`, `vencimento(event)`, `tomador(event)`, `painel()`,
     `serializar_dados(event)`.
3. **Núcleos** (`event_ops.py`, `routes.py`): `update_event_core` / `_gravar_venda_da_edicao` e
   `update_event_comercial` recebem `dados_nota` e `pedida_por_id`; gravam os dados e chamam
   `acompanhar_pedido` depois de `with_invoice`; depois do commit, `avisar_notas_pedidas`.
   `_create_event_core` grava os dados (via `_create_event_row`), carimba e avisa depois do commit.
4. **Views** (`agenda_write.py`): `ler_dados_da_nota(body.get("nota"))` antes do resto
   (`NotaInvalida` → 400 com `fields`); na criação, antes do Google; no PATCH em bloco do cancelado,
   `dados_mudariam` entra no 409.
5. **Leitura** (`agenda_read.py`): `venda.nota` e `pedida_por`/`pedida_em` em `notas_fiscais`.
6. **Home** (`dashboard_service.py`): `notas_a_emitir = _bloco("notas_a_emitir", painel) if
   is_superadmin else None`.
7. **E-mail** (`email_service.py`): `send_nota_pedida_email(nota, users)` (contracts §5).
8. **Config** (`app/config.py`): `NOTA_DADOS_BANCARIOS`.

### Frontend (`frontend/apps/internal/src`)

1. `lib/eventFormSchema.ts`: campos `nota_*` (zod) + refine "município com ISS retido" + defaults +
   `SERVER_FIELD_MAP`/`FIELD_ORDER`.
2. `components/EventFormBlocks/ValoresBlock.tsx`: sob o chip, `DadosDaNotaCampos` (animado) quando
   ligado.
3. `lib/eventCreate.ts` + `EventCreatePage`/`EventEditPage`: `nota` no corpo; hidratação do edit a
   partir de `venda.nota`.
4. `lib/eventInline.ts` + `ComercialSection.tsx`: `nota` no `EventComercialInput`; campos sob o
   checkbox; erros pelos `fields`; leitura em `VendaPanel` (documento, ISS, referência).
5. `lib/types.ts`: `DashboardSummary.notas_a_emitir?: NotasAEmitirSummary | null`.
6. `components/home/PainelNotasAEmitir.tsx` (novo): linhas com valor, tomador, evento, quem pediu,
   ISS, discriminação em `<pre>` com `CopyButton`, "Inserir nota" (input oculto + `Button loading`,
   padrão `SemComprovante`), "Ver evento".
7. `pages/DashboardPage.tsx`: `SectionKey` `"notas"`, card no resumo (`urgent = total`), painel, e
   o "Tudo em dia" conhecendo o bloco.

## Estrutura do projeto

```text
specs/323-nota-pedida-ao-superadmin/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/
├── tasks.md
└── verify_323.py

migrations/versions/d323b5a1c0e7_nota_pedida.py
app/models.py · app/config.py · app/email_service.py
app/calendar/pedido_de_nota_ops.py   (novo)
app/calendar/event_ops.py · app/calendar/routes.py
app/api/agenda_write.py · app/api/agenda_read.py · app/api/dashboard_service.py
frontend/apps/internal/src/lib/{eventFormSchema,eventCreate,eventInline,agenda,types}.ts
frontend/apps/internal/src/components/EventFormBlocks/{ValoresBlock,DadosDaNotaCampos}.tsx
frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx
frontend/apps/internal/src/components/home/PainelNotasAEmitir.tsx   (novo)
frontend/apps/internal/src/pages/{DashboardPage,EventCreatePage,EventEditPage}.tsx
```

**Decisão de estrutura**: o núcleo mora em `app/calendar/` porque a nota é da venda do evento e os
helpers da 069 (`comercial_ops`) já estão lá; módulo próprio para não engordar `comercial_ops`
(1.000+ linhas). O bloco da Home segue o padrão de `_bloco` do `dashboard_service`.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| `_ops` chama `send_async` (efeito externo no núcleo) | o aviso tem de sair depois do commit que só o núcleo faz (os três núcleos commitam por dentro) | aviso na view: duplicaria em três views e o Jinja da criação ficaria sem; precedente em `gastos_ops.create_expense` |

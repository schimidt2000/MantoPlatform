<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 348 — Origem completa

**Branch**: `348-origem-completa` | **Data**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/348-origem-completa/spec.md`

## Resumo

Gravar a origem de cada venda do clique ao evento, sem mudar nada na Meta, no Google ou no WhatsApp de produção:

1. **Meta**: o `ctwa_clid` do `referral` passa a ser guardado no contato pelo anúncio (334), com preenchimento
   retroativo na migration a partir de `conversa_mensagens.dados`; a consulta do anúncio pede também o conjunto.
2. **Site**: o app público guarda os marcadores do clique (`gclid`/`gbraid`/`wbraid`/`fbclid`/`gad_campaignid`/`utm_*`)
   e pede ao servidor um código curto (`POST /api/origem/codigo`); a mensagem pronta da lista de desejos e dos
   formulários leva "Código do site: #XXXXX"; o aviso do WhatsApp lê o código e cria um contato de origem `site`.
3. **Venda ↔ conversa**: `conversa_id` + `origem_contato_id` (o contato congelado) no orçamento e no evento. O
   orçamento liga no primeiro envio pela conversa; o evento herda do orçamento ou recebe a conversa na criação
   (contrato da 349). Nunca pela ficha.
4. **Frente**: `calendar_events.frente` (FK `marketing_frentes.slug`), escolhida na aba Comercial; a regra de 16/11
   vira sugestão; uma função única de leitura (`frente_ops`), Python e SQL, que a 345 passa a usar e a 351 consome.
5. **Desempenho**: `clients.utm_campaign_id`; as campanhas agrupam por (plataforma, id) e o lead casa pelo id.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite) no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migration à mão), Flask-Limiter; React, TanStack Query,
Tailwind, `@manto/ui`, `@manto/api-client`. Nenhuma dependência nova.

**Armazenamento**: PostgreSQL. Verificação contra o espelho próprio `manto_348` (dump noturno de 17/11), não contra
o `manto_local` compartilhado — ver Rastreamento de complexidade.

**Verificação**: `specs/348-origem-completa/verify_348.py` (Meta, Google Agenda e rede simulados, molde do
`verify_334.py`); `ruff check` nos arquivos tocados; `cd frontend && npm run typecheck`; telas no Browser pane com
backend na porta 5348 e Vite na 6348 (lista de desejos e formulário em 390 px; aba Comercial em desktop e 390 px).

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: a leitura do código no aviso é uma regex sobre o texto e um `UPDATE` condicional por
código encontrado; a criação do código é uma chamada por clique novo, sem bloquear a página.

**Restrições**:
- Nenhuma chamada nova à Meta além do campo `adset{id,name}` na consulta que já existe.
- A rota pública nova mora em `/api/*` (já no proxy; `BACKEND_PREFIXES` não muda).
- Campo novo do payload é opcional no React (armadilha 21).
- Calendar é domínio onde as convenções não valem (`docs/00` §7): as mudanças lá são uma chamada de linha a módulo
  novo (`frente_ops`, `origem_ops`) no ponto que já existe, sem refatorar.

**Escala/escopo**: 1 tabela nova (`origem_codigos`); 10 colunas novas em 6 tabelas; 1 endpoint novo; 4 endpoints com
campo novo; 2 módulos novos de núcleo + 1 de leitura da frente; 3 telas (lista de desejos, formulário, aba Comercial).

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `ConversaAnuncio` (334) vira o registro único de "contato de origem" (ganha o tipo `site`) em vez de tabela paralela; `anuncio_ops.aplicar_na_ficha` estendido; `marketing_frentes` (345) é a lista de frentes; o skeleton do `verify_334.py` (dublês e disjuntor de rede) é reusado |
| II. Padrões de código | type hints e docstrings; constantes no `conversas/constantes.py` e `app/constants.py`; `ruff check` nos tocados, `ruff format` só nos novos |
| III. Camadas / API First | núcleo em `app/conversas/codigo_ops.py`, `app/conversas/origem_ops.py`, `app/calendar/frente_ops.py` (sem `flask.request`); `app/api/origem_public.py` só valida e serializa e é importado em `app/api/__init__.py` |
| IV. Não quebrar o que funciona | migration aditiva; colunas nulas; o bundle antigo (sem `frente`) salva a aba Comercial como hoje; `frente_venda_sql` da 345 continua existindo e devolve o mesmo para todo evento sem frente gravada |
| V. UI/UX com feedback | o "Salvar venda" já tem loading/erro; o 400 da frente aparece no campo; o envio público nunca espera o código |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/348-origem-completa/` |
| VII. Living Spec | spec e clarify atualizados antes do código |
| VIII. Verify antes do núcleo | `verify_348.py` escrito na fase Foundational e rodado vermelho antes do núcleo |
| IX. Dinheiro BRL | não toca dinheiro |
| X. Mobile-first público | lista de desejos e formulário conferidos em 390×844; nada visual muda além da mensagem |
| XI. Framer Motion | não cria animação |
| XII. Combobox / Maps | o select da frente tem 5 itens (< 10) |
| XIII. RBAC declarado | `POST /api/origem/codigo` público com limite; os demais mantêm o gate; origem e frente só no bloco comercial; linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | nenhuma env nova; o único efeito externo novo é o campo `adset` na consulta que já existe, sob a mesma trava (`conexao_dos_anuncios`) |
| XV. Texto por superfície | interno: "Frente", "Selecione a frente da venda.", "Sugestão pelo título: …", "Origem da venda"; público: a linha "Código do site: #XXXXX" na mensagem que a cliente envia (curta e clara) |
| Stack | migration à mão `a348c0d1e2f3`, `down_revision = d334b2c4e6f8`; sem Jinja novo; sem segredo |
| Operação e Deploy | não toca `startCommand`; migration aditiva (sem ensaio destrutivo); deploy de backend agrupado no lote da sessão principal (a 349, a 350 e a 351 também encadeiam em `d334b2c4e6f8`: o reencadeamento é do lote de merge) |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/348-origem-completa/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md          # endpoints públicos e internos tocados
├── contracts/consumidores.md # o contrato que a 349 e a 351 usam (conversa_id, contato de origem, frente)
├── checklists/ · tasks.md
└── verify_348.py
```

### Código

```text
migrations/versions/a348c0d1e2f3_origem_completa.py   # nova
app/models.py                                       # OrigemCodigo; colunas novas
app/conversas/constantes.py                         # código: alfabeto, tamanho, validade, regex, textos
app/conversas/codigo_ops.py                         # novo: criar, validar, anexar à mensagem, ler no aviso
app/conversas/origem_ops.py                         # novo: contato de origem, ligar orçamento/evento, leitura
app/conversas/anuncio_ops.py                        # ctwa_clid; conjunto; utm_campaign_id; ficha pelo site
app/conversas/aviso_ops.py                          # chama codigo_ops.ler_na_mensagem
app/conversas/costura_ops.py                        # chama origem_ops.ligar_orcamento no primeiro envio
app/integracoes/meta_anuncios_client.py             # adset{id,name}
app/calendar/frente_ops.py                          # novo: sugestão, frente_do_evento, frente_sql, validar
app/calendar/routes.py                              # _create_event_core: uma chamada a frente_ops e origem_ops
app/calendar/event_ops.py                           # update_event_comercial grava a frente
app/calendar/orcamento_evento_ops.py                # set_event_orcamento acompanha a conversa do orçamento
app/marketing/comando_ops.py                        # frente_venda_sql delega a frente_ops
app/marketing/desempenho_ops.py                     # campanha por id; lead por id
app/api/origem_public.py                            # novo: POST /api/origem/codigo
app/api/__init__.py                                 # import do módulo novo
app/api/agenda_write.py                             # frente/conversa_id na criação; frente na aba Comercial
app/api/agenda_read.py                              # venda.frente e venda.origem no detalhe
app/api/formularios_write.py                        # origem_codigo → linha na mensagem e vínculo
frontend/apps/public/src/lib/origem.ts              # novo: captura e código guardado
frontend/apps/public/src/App.tsx                    # captura no carregamento
frontend/apps/public/src/lib/wishlist.ts            # linha do código na mensagem
frontend/apps/public/src/components/formularios/DynamicForm.tsx  # origem_codigo no envio
frontend/apps/internal/src/lib/agenda.ts            # tipos venda.frente / venda.origem
frontend/apps/internal/src/lib/eventInline.ts       # EventComercialInput.frente
frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx  # campo Frente + Origem da venda
```

**Decisão de estrutura**:
- O código do site e a ligação venda ↔ conversa moram em `app/conversas/` (o contato de origem é da conversa). Dois
  módulos, porque o código tem superfície pública e a ligação é interna.
- A leitura da frente mora em `app/calendar/frente_ops.py`, ao lado do evento, e não em `app/marketing/`: quem grava a
  frente é a aba Comercial, quem lê é o marketing (345, 351). Calendar → marketing já não é dependência; o
  `comando_ops` importa a função.
- Nos dois domínios frágeis (`calendar/routes.py`, `event_ops.py`) entra só a chamada; a regra fica nos módulos novos.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify contra `manto_348`, não `manto_local` (Princípio VIII) | quatro features (348–351) com migrations sobre a mesma head rodam ao mesmo tempo; o `manto_local` compartilhado ficaria com a migration de uma e quebraria as outras | refazer o `manto_local` apagaria o esquema das outras sessões (memória "espelho próprio por feature") |
| Import tardio de `app.conversas.origem_ops` dentro de `calendar/routes.py` e `orcamento_evento_ops.py` | a ligação venda ↔ conversa precisa acontecer no ponto em que o evento nasce e em que o orçamento é ligado, e esses pontos moram no domínio Calendar | mover a criação do evento para `*_ops` é a refatoração que `docs/00` §7 manda não fazer de passagem |

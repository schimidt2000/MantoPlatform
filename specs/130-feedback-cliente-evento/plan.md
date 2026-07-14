# Implementation Plan: Feedback do Cliente por Evento (130)

**Branch**: `130-feedback-cliente-evento` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

## Summary

Novo blueprint `feedback_bp` com três rotas: uma interna (gera/retorna o link, lazy, chamada
via fetch pelo botão do menu de ferramentas) e duas públicas, sem login (`GET`/`POST
/avaliar/<token>`). Nova tabela `client_feedbacks` (nota, cards em JSON, comentário, data) e
nova coluna `calendar_events.feedback_token` (aleatória, única — nunca o id sequencial).
Página pública em template próprio, mobile-first, com revelação progressiva via JS puro
(sem framework, segue o resto do projeto). Painel de leitura na página do evento, no mesmo
estilo do já existente "⭐ Avaliações dos Artistas".

## Technical Context

**Stack**: Flask + SQLAlchemy + Jinja2 + JS vanilla (igual ao resto do projeto).
**Storage**: 2 mudanças de schema — tabela nova `client_feedbacks`; coluna nova
`calendar_events.feedback_token` (`String(43)`, `unique=True`, `nullable=True`, gerada só
quando pedida pela primeira vez).

**Arquivos**:
- `app/models.py` — `ClientFeedback` (novo model) + `CalendarEvent.feedback_token` (nova
  coluna).
- `migrations/versions/<hash>_client_feedback.py` — cria `client_feedbacks` + adiciona
  `feedback_token` em `calendar_events` (índice único).
- `app/feedback/__init__.py`, `app/feedback/routes.py` (novo blueprint `feedback_bp`):
  - `POST /events/<int:event_id>/gerar-link-feedback` — `eff_has_role('COMERCIAL',
    'SUPERADMIN')`; gera `feedback_token` com `secrets.token_urlsafe(32)` se ainda não
    existir, devolve `{"url": ...}` (JSON) com `url_for(_external=True)`.
  - `GET /avaliar/<token>` — público; busca evento por `feedback_token`; 404 amigável
    (template próprio) se não achar.
  - `POST /avaliar/<token>` — público, `@limiter.limit("10 per hour")` (mesma família de
    proteção de `/f/pre-contrato`); valida nota (1–5, obrigatória), lê lista de cards e
    comentário (opcionais), salva `ClientFeedback`, renderiza a mesma página em estado de
    agradecimento (sem redirect — mantém simples, uma view só).
- `app/templates/feedback/public.html` (novo) — página mobile-first: pergunta + 5 estrelas
  grandes; JS revela o bloco de cards certo (elogio/atenção) conforme a nota escolhida,
  troca de nota reseta a seleção anterior; textarea opcional; botão de envio; estado de
  agradecimento pós-envio; estado de link inválido.
- `app/templates/event_detail.html` — `page_actions`: novo item "💬 Pedir feedback da
  cliente" no bloco já existente `{% if eff_has_role('COMERCIAL', 'SUPERADMIN') %}` do
  menu de ferramentas, ao lado de Cobrança; JS reaproveita a função `copiar()` já definida
  no arquivo (busca a URL via fetch, depois chama `copiar(url, btn)`). Novo painel "💬
  Feedback da Cliente" na área de conteúdo, mesmo grupo de permissão e mesmo estilo visual
  do painel "⭐ Avaliações dos Artistas" já existente (nota em estrelas, cards marcados,
  comentário, data; estado vazio quando não há nenhum).
- `app/calendar/routes.py` — `_clear_event_side_tables()` (feature 122) ganha mais uma
  linha: `ClientFeedback.query.filter_by(event_id=event_id).delete()` — sem isso, excluir
  um evento com feedback já recebido quebraria por chave estrangeira, mesmo padrão já
  usado para `EventRating`/`EventPayment`/etc.
- `app/__init__.py` — `app.register_blueprint(feedback_bp)`.

**Testing**: verificação funcional vs `manto_local` — fluxo completo: gerar link (cria
token na 1ª vez, reaproveita na 2ª), abrir página pública com token válido, submeter com
nota 5 (cards de elogio) e com nota 3 (cards de atenção), confirmar troca de cards ao mudar
nota antes de enviar (via inspeção do HTML/JS, já que é client-side), token inválido
devolve página amigável (não 500), rate limit não quebra o fluxo normal, painel interno
mostra os feedbacks salvos e o estado vazio quando não há nenhum, exclusão de evento com
feedback não quebra (via `_clear_event_side_tables`).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Estrutura de blueprint público sem login copiada de `formularios_bp` (`/f/pre-contrato`): mesmo `limiter.limit("10 per hour")`, mesmo estilo de `_render_public_form`. Layout mobile-first (`.portal-wrap`, estrelas grandes) copiado de `portal/rate.html` (já testado em produção). Painel de leitura interno copia o estilo do já existente "⭐ Avaliações dos Artistas". Botão "copiar" reaproveita a função `copiar()` já definida em `event_detail.html`, sem duplicar lógica. Limpeza de tabela sem cascade segue o padrão já estabelecido em `_clear_event_side_tables` (feature 122), em vez de inventar `cascade="all, delete-orphan"` novo. |
| II. Não adivinhável | ✅ FR-003: `feedback_token` aleatório (`secrets.token_urlsafe(32)`), nunca o id sequencial do evento — decisão de segurança explícita no spec. |
| IV. Não quebrar | ✅ Feature aditiva: nova tabela, nova coluna opcional, novo blueprint, um item a mais no menu já existente (feature 129) — nenhuma rota/comportamento existente muda. `_clear_event_side_tables` só ganha uma linha a mais. |
| V. Feedback visível | ✅ Botão de copiar segue o mesmo padrão visual de confirmação (`✅ Copiado!`) já usado em Confirmar/Cobrança. Botão de envio da avaliação segue o guard global de feedback ao clicar (feature 124), por ser um `<form>` comum. |
| VI. Planejar | ✅ Este plano, levantado depois de ler `EventRating`/`portal/rate.html`/`formularios/routes.py`/`event_detail.html` para confirmar o que já existe e o que é genuinamente novo. |
| VIII. Mobile-first | ✅ **Aplica-se diretamente** — a página pública `/avaliar/<token>` é a superfície de uso real da cliente, sempre pelo celular (link recebido no WhatsApp). Layout mobile-first desde o início (mesma base de `portal/rate.html`), estrelas e cards grandes o bastante para toque. |

**Gate: PASS.**

## Decisões

1. **Sem edição/reenvio da mesma avaliação**: ao contrário do portal do talento (que
   permite atualizar uma avaliação já enviada, porque há login), aqui não há como
   identificar "quem" está respondendo — cada envio é uma avaliação nova e independente
   (documentado no spec, Assumptions). Mantém a implementação simples e evita inventar um
   mecanismo de identidade anônima que a feature não pediu.
2. **Uma view só para GET e POST do formulário público**, sem redirect pós-envio: mostra
   direto o estado de agradecimento na resposta do POST. Mais simples que fazer
   POST-redirect-GET, e como não há re-submissão acidental grave aqui (não é uma cobrança,
   é uma avaliação — reenviar não causa duplicidade de dados sensíveis), o guard global de
   duplo-clique da feature 124 já cobre o caso comum (F5 logo após o clique).
3. **`feedback_token` fica em `CalendarEvent`, não numa tabela própria de "links"**: um
   único link por evento é suficiente para o pedido ("link para a página de avaliação
   específica desse evento"); criar uma tabela separada só para guardar um token seria
   complexidade sem necessidade concreta ainda.
4. **Painel de leitura entra na própria `event_detail.html`**, não num dashboard agregado
   novo: o pedido original é sobre a ferramenta no evento; um painel global de todos os
   feedbacks fica fora de escopo (ver spec, Assumptions) até que apareça necessidade real.

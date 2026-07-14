# Tasks — Feedback do Cliente por Evento (130)

- [X] T001 `app/models.py`: `ClientFeedback` (event_id, score, tags JSON-em-texto,
      comment, submitted_at) + `CalendarEvent.feedback_token` (String(43), unique,
      nullable)
- [X] T002 Migration manual (`down_revision` = head atual) — cria `client_feedbacks`,
      adiciona `feedback_token` a `calendar_events` com índice único; checar colisão de
      revision-id antes de finalizar
- [X] T003 `app/feedback/routes.py` (blueprint novo `feedback_bp`): rota interna
      `POST /events/<id>/gerar-link-feedback` (gera token lazy, devolve JSON com URL
      absoluta), rotas públicas `GET`/`POST /avaliar/<token>` (sem login, rate limit
      "10 per hour" no POST, valida nota 1–5 obrigatória, cards e comentário opcionais,
      404 amigável para token inválido, tela de agradecimento pós-envio na mesma view)
- [X] T004 `app/templates/feedback/public.html`: pergunta única + 5 estrelas grandes;
      revelação progressiva via JS (cards de elogio para nota 5, cards de atenção para
      1–4; trocar nota reseta seleção); textarea opcional; botão grande de enviar;
      mobile-first (base `.portal-wrap` de `portal/rate.html`)
- [X] T005 `app/templates/feedback/invalid.html` (ou branch dentro do mesmo template):
      estado amigável para token que não corresponde a nenhum evento
- [X] T006 `app/__init__.py`: registrar `feedback_bp`
- [X] T007 `app/templates/event_detail.html`: item "💬 Pedir feedback da cliente" no
      menu de ferramentas (bloco `COMERCIAL`/`SUPERADMIN`, ao lado de Cobrança) com JS
      (fetch + reaproveita `copiar()` já existente no arquivo); painel "💬 Feedback da
      Cliente" na área de conteúdo (mesmo estilo de "⭐ Avaliações dos Artistas": nota,
      cards, comentário, data; estado vazio quando não há nenhum)
- [X] T008 `app/calendar/routes.py`: `_clear_event_side_tables()` ganha
      `ClientFeedback.query.filter_by(event_id=event_id).delete()`
- [X] T009 Verificação funcional vs `manto_local`: gerar link (cria na 1ª vez, reaproveita
      na 2ª); GET com token válido/; POST nota 5 (cards de elogio) e nota 3 (cards de
      atenção) salvam certo; token inválido não quebra (404 amigável, não 500); rate limit
      não atrapalha uso normal; painel interno mostra os feedbacks e o estado vazio;
      excluir evento com feedback recebido não quebra
- [X] T010 `ruff check` nos arquivos tocados; changelog (`docs/changelog.html`,
      republicar no link já existente); commit, merge em `main`, push

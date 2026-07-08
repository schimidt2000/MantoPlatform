# Tasks — Formulários de Pré-Contrato (118)

- [X] T001 Migration (tabela `form_responses` + `site_settings.whatsapp_form_number`),
      `down_revision = "d0e1f2a3b4c5"`, conferir unicidade do revision, upgrade no
      manto_local
- [X] T002 `app/models.py`: modelo `FormResponse` + coluna `whatsapp_form_number` em
      `SiteSetting`
- [X] T003 Blueprint `app/formularios/` (routes + validação + formatação da mensagem
      WhatsApp) registrado em `app/__init__.py`
- [X] T004 Templates públicos mobile-first: `_public_base.html`, `pre_contrato.html`
      (formulario_comum.md), `corporativo.html` (formulario_corporativo.md),
      `enviado.html` (botão + auto-open WhatsApp); máscaras JS leves + condicional
      "Outros" + ViaCEP
- [X] T005 Área interna: `/formularios/` (links copiáveis + listagem de respostas),
      `/formularios/respostas/<id>` (detalhe + sugestão por telefone + associar/criar
      cliente), delete só SUPERADMIN com confirm()
- [X] T006 Home: alerta "pré-contratos sem cliente" no painel comercial
      (`app/__init__.py` + `home.html`)
- [X] T007 `/events/new`: buscador de respostas (`form_response_picker.js` + endpoint
      `/formularios/respostas/search` sem acento) + vínculo `response.event_id` no POST +
      troca do placeholder whatsform; link "Ver pré-contrato" na página do evento
- [X] T008 Campo `whatsapp_form_number` em `admin_settings.html` + parsing na view
- [X] T009 Verificação funcional vs manto_local (12 cenários do plano) + ruff + viewport
      mobile dos formulários públicos
- [X] T010 Commit, merge em main, push

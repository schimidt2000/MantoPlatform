# Tasks — Menu de Ferramentas na Página do Evento (129)

- [X] T001 `app/static/style.css`: componente `.action-menu`/`.action-menu-trigger`/
      `.action-menu-panel` (dropdown, mesmo padrão de `.fp`/`.fp-panel` de
      `talents_list.html`)
- [X] T002 `app/templates/event_detail.html`: `page_actions` reestruturado — os 7 itens
      (sincronizar, exportar elenco, editar no Google, confirmar dados, marcar
      confirmado, cobrança, excluir) movidos para dentro de `.action-menu-panel`, atrás
      do botão `⋯ Ferramentas`, com os `eff_has_role`/condições originais intocados;
      variável `show_tools_menu` esconde o botão quando nenhum item bate (FR-006);
      "Voltar para Agenda" continua fora do menu
- [X] T003 `app/templates/event_detail.html`: JS `toggleActionMenu()` + fechar ao clicar
      fora + fechar com Esc
- [X] T004 Verificação funcional vs manto_local (16/16): SUPERADMIN vê os 7 itens no
      menu; usuário CASTING puro não vê os itens comerciais (confirmar/cobrança/marcar
      confirmado) nem excluir, mas continua vendo exportar elenco; cada ação preserva
      exatamente a mesma action/href/onclick de antes; um só botão de reticências (sem
      duplicar). Nenhum arquivo Python tocado — sem necessidade de ruff.
- [X] T005 Commit, merge em main, push

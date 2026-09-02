# Tarefas — Feature 272

- [x] T01 `Notification` em `models.py` + migration `b7d2e4f1a9c3` (ensaio `upgrade → downgrade → upgrade` no `manto_local`)
- [x] T02 `app/notificacoes/notificacoes_ops.py` — catálogo, `emitir` (SELECT + SAVEPOINT), produtores, caixa, retenção
- [x] T03 `notificacoes_read.py` / `notificacoes_write.py` + registro em `app/api/__init__.py`
- [x] T04 Produtor 1: `_notificar_comercial` (regime B); `send_form_response_email` e imports removidos
- [x] T05 Produtor 2: `feedback_write` (regime A, `urgent` com nota ≤ 2)
- [x] T06 Produtor 3: `reject_invite` com guarda real + notificação no mesmo commit
- [x] T07 Efeitos colaterais: detalhe da resposta marca lida (para quem abriu); `delete_response` apaga as dela
- [x] T08 Retenção no laço do review-cleanup + `flask notificacoes-limpar`
- [x] T09 `verify_272.py` 13/13 contra `manto_local` (escrita conferida por conexão separada)
- [x] T10 `AppLayout.headerActions`; hooks; `NotificacoesBell`/`Panel`/`Item`; `NotificacoesPage`; rota; `AppShell`
- [x] T11 `npm run typecheck` limpo nos três apps; `ruff` no baseline
- [x] T12 Conferência em tela: desktop (badge 3 → clique navega e decrementa), mobile 375 px (sino na barra, fora do drawer, sem rolagem horizontal), `/notificacoes` (abas, "Marcar todas" zera e desabilita)
- [x] T13 docs 00 (§2, §4, §6), 01 (§2, §3.13.5, §4.3, cabeçalho), 02 (AppShell, `/notificacoes`), 03 (entrada 272 + ponteiro na 266), 04 (§7, §8)
- [ ] T14 Pós-deploy: `GET /api/notificacoes/nao-lidas` autenticado responde; primeira resposta de formulário real aparece no sino; conferir que nenhum e-mail de formulário sai

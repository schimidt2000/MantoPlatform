# Plano — Feature 272: notificações internas

**Spec**: `spec.md` · **Branch**: `272-notificacoes-internas` (empilhada sobre `270-miniaturas-catalogo`)
**Migration**: `b7d2e4f1a9c3_notifications.py` (`down_revision = a1c7d3e59b02`; aditiva — uma tabela)

## Resumo técnico

Uma tabela (`notifications`, uma linha por destinatário), um módulo puro (`app/notificacoes/
notificacoes_ops.py`: catálogo de `kind`, destinatários por papel, `emitir()` que não comita, leitura
da caixa, retenção), quatro endpoints sem gate de papel (escopo por dono) e um sino no shell via
slot `headerActions` do `AppLayout`. Três produtores na v1; o e-mail de resposta de formulário da
266 sai do código.

## Backend

| Onde | O quê |
|---|---|
| `app/models.py` | `Notification` ao lado de `AuditLog`: `user_id` FK CASCADE, `kind`, `severity`, `title`, `body`, `link_path`, `entity_type`/`entity_id` (sem FK), `dedupe_key`, `created_at` (`now_sp`), `read_at`; `UNIQUE(user_id, dedupe_key)`; índice parcial `(user_id, id) WHERE read_at IS NULL` declarado no modelo E na migration |
| `migrations/versions/b7d2e4f1a9c3_notifications.py` | `create_table` + 3 índices; `downgrade` = drop; ensaiada `upgrade → downgrade → upgrade` |
| `app/notificacoes/notificacoes_ops.py` | `KIND_FORM_RESPONSE/AVALIACAO/CONVITE_RECUSADO`, `DESTINATARIOS_POR_KIND`, `resolver_destinatarios`, `emitir` (SELECT prévio + SAVEPOINT por inserção), `notificar_resposta_formulario/avaliacao_recebida/convite_recusado`, `contar_nao_lidas`, `listar` (keyset), `marcar_lida`, `marcar_lidas_ate`, `marcar_lidas_por_objeto`, `apagar_por_entidade`, `contar_antigas`, `limpar_antigas`, `serializar` |
| `app/api/notificacoes_read.py` / `_write.py` | `GET /nao-lidas`, `GET /notificacoes`, `POST /<id>/lida`, `POST /lidas` (`ate_id` obrigatório); registrados em `app/api/__init__.py` |
| `app/api/formularios_write.py` | `_avisar_comercial` → `_notificar_comercial` (regime B, `rollback` no `except`); imports de e-mail e de `Role/User` saem |
| `app/email_service.py` | `send_form_response_email` removida (única chamadora era a de cima) |
| `app/api/feedback_write.py` | `flush` + `notificar_avaliacao_recebida` antes do commit existente (regime A) |
| `app/talent_portal/portal_ops.py` | `reject_invite`: guarda `already rejected` + `notificar_convite_recusado` no mesmo commit |
| `app/api/formularios_admin_read.py` | detalhe da resposta marca lidas as notificações dela para quem abriu |
| `app/formularios/formularios_ops.py` | `delete_response` apaga as notificações da resposta |
| `app/__init__.py` | laço do review-cleanup ganha `limpar_antigas()` (sem thread nova, sem claim) |
| `app/cli.py` | `flask notificacoes-limpar [--execute]` |

## Frontend

| Onde | O quê |
|---|---|
| `packages/ui/src/components/app-layout.tsx` | prop `headerActions` renderizada na linha da marca (desktop) e na barra superior do mobile; `sidebarInner(comAcoes)` para o drawer não duplicar |
| `apps/internal/src/lib/notificacoes.ts` | tipos, `useNaoLidas` (poll 60 s, `refetchOnWindowFocus`, sem retry), `useNotificacoes` (infinite, keyset), `useMarcarLida` (otimista), `useMarcarTodasLidas`, `agruparPorDia` |
| `apps/internal/src/components/notificacoes/` | `NotificacoesBell` (badge, `aria-live` só ao subir, Esc/clique fora), `NotificacoesPanel` (popover `z-30`, estados, "Marcar todas", "Ver todas"), `NotificacaoItem` (ícone por `kind`, `urgent` em vermelho) |
| `apps/internal/src/pages/NotificacoesPage.tsx` | abas Não lidas/Todas, "Carregar mais", saída animada da linha lida |
| `AppShell.tsx` / `App.tsx` | `headerActions={<NotificacoesBell />}` (não para revendedor); rota `/notificacoes` sem item de menu |

## Ordem de execução

1. Modelo + migration (ensaio local) → 2. `notificacoes_ops` → 3. endpoints → 4. produtores + remoção
do e-mail → 5. `verify_272.py` 13/13 → 6. `AppLayout` + hooks + componentes + página → 7. typecheck nos
três apps → 8. conferência em tela (desktop e 375 px) → 9. docs 00/01/02/03 (+ ponteiro na 266)/04.

## Deploy

Migration roda no `startCommand` (`flask db upgrade`) na janela normal de ~45 s. Como a branch está
empilhada sobre a 270, o merge da 272 leva a 270 junto — um deploy só. Depois do deploy: conferir
`GET /api/notificacoes/nao-lidas` autenticado (não `/health`) e rodar `flask warm-thumbnails` (270).

## Riscos e mitigação

- **Aviso derrubando o fato** → `emitir` com SAVEPOINT; regime B com `rollback`; verify 3 e 5.
- **"Marcar todas" engolindo lead novo** → `ate_id` obrigatório; verify 7.
- **Polling pesando** → COUNT no índice parcial, zero join; pausado em aba oculta; verify 12 registra o plano.
- **Drift modelo × migration** (índice parcial) → declarado nos dois lados; `flask db check` sem item novo.
- **Sino duplicado no drawer do mobile** → `sidebarInner(false)` no drawer; conferido em 375 px.

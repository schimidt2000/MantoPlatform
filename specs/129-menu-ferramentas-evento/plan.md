# Implementation Plan: Menu de Ferramentas na Página do Evento (129)

**Branch**: `129-menu-ferramentas-evento` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

## Summary

`event_detail.html`'s `{% block page_actions %}` (linhas 37-94) hoje lista 7 botões/
links soltos (sincronizar, exportar elenco, editar no Google, confirmar dados, marcar
confirmado, cobrança, excluir) + o link "Voltar para Agenda". Substitui os 7 itens por
um único botão de reticências (`⋯ Ferramentas`) que abre um painel dropdown com a mesma
lista, na mesma ordem, com as mesmas condições de `eff_has_role`/disponibilidade —
**zero mudança de comportamento**, só de organização visual. "Voltar para Agenda"
continua fora do menu (navegação, não ferramenta).

## Technical Context

**Stack**: o existente (Jinja2 + JS vanilla). **Storage**: N/A — nenhuma rota, permissão
ou dado muda.

**Arquivos**:
- `app/templates/event_detail.html` — `page_actions` reestruturado: os 7 itens (com seus
  `{% if eff_has_role(...) %}` originais intocados) passam a viver dentro de um wrapper
  `.action-menu` / `.action-menu-panel`, atrás do botão `⋯ Ferramentas`. Variável Jinja
  `has_any_tool` (ou equivalente) calcula se pelo menos uma condição de acesso bate, para
  decidir se o botão de reticências aparece (FR-006).
- `app/static/style.css` — componente novo `.action-menu`/`.action-menu-trigger`/
  `.action-menu-panel` (dropdown posicionado, mesmo padrão de interação já usado no
  `.fp`/`.fp-panel` de `talents_list.html`: `position:absolute`, toggle por classe
  `.open`, fecha ao clicar fora).
- Script inline em `event_detail.html` (ou `extra_scripts`) — `toggleActionMenu()`,
  listener de clique fora e de tecla Esc.

**Testing**: verificação funcional vs `manto_local` — cada uma das 7 ações continua
funcionando via o mesmo endpoint/comportamento de antes (submits de formulário, links,
`onclick` de modal), testado por role (ex.: SUPERADMIN vê todos os 7; um papel sem
COMERCIAL não vê os 4 itens comerciais); botão de reticências some quando nenhuma
condição bate.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Padrão de dropdown (`position:absolute`, classe `.open`, fecha ao clicar fora) copiado do `.fp`/`.fp-panel` já existente em `talents_list.html` — não inventa um mecanismo novo. Nenhuma rota/lógica de backend nova (zero duplicação, porque nada muda no lado do servidor). |
| IV. Não quebrar | ✅ Cada `{% if eff_has_role(...) %}` original é preservado literalmente, só movido de lugar — nenhuma regra de acesso muda (FR-003). As 7 ações mantêm exatamente a mesma `action`/`onclick`/`href` de hoje (FR-004). |
| V. UI/UX | ✅ Reduz a poluição visual pedida; ação destrutiva (excluir) continua exigindo confirmação via modal, agora um passo mais protegida (dentro do menu) em vez de menos. Botão de reticências segue o guard global de feedback ao clicar (feature 124) por ser parte de um fluxo de UI padrão. |
| VI. Planejar | ✅ Este plano, escopo levantado por leitura completa do template antes de qualquer código. |
| VIII. Mobile-first | N/A — tela interna do painel, não superfície pública listada no Princípio VIII (mesmo critério já usado nas demais telas internas desta sessão). |

**Gate: PASS.**

## Decisões

1. **Só os 7 botões do `page_actions`, não os botões de seção**: confirmado no spec
   (Assumption) — botões dentro de casting/figurino/comercial estão ligados a um item
   específico daquela seção, um menu genérico no topo os deixaria mais difíceis de achar,
   não mais fáceis.
2. **Reaproveitar o padrão `.fp`/`.fp-panel` de `talents_list.html`**: já testado no
   sistema (mesma técnica de posicionamento/abertura/fechamento), só renomeado para
   `.action-menu` por semântica (não é mais um filtro, é um menu de ações) — evita
   inventar uma segunda forma de fazer a mesma coisa (Princípio I).
3. **Voltar para Agenda fica fora do menu**: é navegação para outra tela, não uma ação
   sobre o evento atual — mantê-lo visível e imediato segue a convenção já usada em
   outras páginas do sistema (botão "voltar" sempre solto, nunca dentro de um menu).

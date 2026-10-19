# 308 — Compromisso interno não vira pendência de casting; dispensar direto da Home

**Branch**: `308-casting-sem-compromisso-interno` (da `main`) · **Created**: 2026-10-19
**Status**: Pronto, aguardando push · **Migration**: nenhuma

## O pedido, nas palavras do dono

"Pensar em uma lógica para retirar todas essas coisas, porque a maioria delas, por exemplo,
gravação de voz e uma aventura animal, não teve um coordenador necessariamente. Era mais uma
marcação de data na agenda [...] empréstimo de figurino também não deveria entrar aqui. [...] Ou que
eu consiga remover aqui de forma definitiva." (print do painel Casting da Home: 292 pendentes,
15 urgentes, quase todos marcações de agenda.)

## Causa

1. Todo evento ganha uma vaga de Coordenador sem talento (`_ensure_coordinator`,
   `app/calendar/routes.py`), inclusive marcação de agenda.
2. Título sem "+" vira personagem: "EMPRESTIMO FIGURINO DAY JONES - PIRATA" é lido como papel.
   Cada marcação gera **duas** pendências (personagem + Coordenador).
3. O filtro de ensaio da Home é `title LIKE '🟧 ENSAIO%'` (`app/api/dashboard_service.py`,
   `_base_filters`). A equipe escreve `🟧 - ENSAIO EDUCAMANTO`; o hífen escapa do filtro.

A convenção do laranja já existe: `MARCADORES_COMPROMISSO_INTERNO = ("🟧", "🟠")`
(`app/constants.py`, decisão do dono na 299), hoje respeitada só pela cobrança
(`cobranca_ops.compromisso_interno`). O casting a ignora.

## Decisões do dono (19/10/2026)

- **Regra A aprovada**: título que começa com 🟧/🟠 não gera pendência de casting na Home. As vagas
  continuam sendo criadas (sync intocado).
- **Botão Dispensar só para o SUPERADMIN.** O time de Casting NÃO dispensa — o RBAC atual do
  endpoint (só superadmin) fica como está.
- **Empréstimo de figurino** é troca com empresa parceira, sem cliente e sem cobrança: a equipe marca
  com 🟠 e a regra A cobre. Nenhuma regra por palavra-chave.
- **Pendências de eventos passados continuam na lista** (o corte segue o `release_date`): o
  pagamento depende delas estarem registradas.

## O que muda

**A. Backend — `app/api/dashboard_service.py`.** `_base_filters` ganha `not_compromisso_interno`:
título (sem espaço à esquerda) não começa com nenhum marcador de `MARCADORES_COMPROMISSO_INTERNO`.
Entra em `compute_casting_tasks` — `pending`, `rejected_invites`, `total` e `done` — e em
`compute_dismissed_casting_tasks`. A contagem de urgentes do frontend sai de `pending`, então
acompanha sozinha. Marcadores lidos da constante, nunca repetidos no código.

**B. Frontend — `DashboardPage.tsx` (painel Casting).**
- Linha de "A escalar": botão **Dispensar** ao lado do "Abrir", **só se `user.is_superadmin`**. Chama
  o `POST /api/roles/<id>/dismiss` que já existe (108/148) e invalida o dashboard.
- O card "Cargos dispensados" (hoje só "N cargos") vira lista com **Restaurar**
  (`POST /api/roles/<id>/restore`, já existe), também só superadmin.
- Hooks: os de `lib/casting.ts` invalidam o detalhe do evento; a Home precisa invalidar a query do
  dashboard — conferir antes de reaproveitar.

Nenhum endpoint novo, nenhuma migration, nenhuma mudança de RBAC.

## Verificação

`verify_308.py` contra o `manto_local` (role existente com `talent_id IS NULL`, nunca role
inventada):
- evento 🟧/🟠 (inclusive `🟧 - ENSAIO`) não aparece em `casting.pending` nem em `rejected_invites`;
- evento sem marcador continua aparecendo;
- dismiss como superadmin tira a role da lista; restore a devolve (conferido por conexão separada);
- **deve falhar**: usuário CASTING chamando dismiss recebe 403.
Medir antes/depois quantos dos pendentes a regra A remove. `npm run typecheck`, `ruff check`, tela
aberta pela skill `manto-conferir-tela` (botão visível como superadmin, ausente como casting).

## Fora de escopo

- Parar de criar a vaga de Coordenador em marcação de agenda (mexe no sync, que manda e-mail de
  remoção a artista).
- Painel "Confirmações" (`escalacoes_sem_confirmacao`): quem foi escalado num compromisso interno
  ainda precisa confirmar.
- Painéis de figurino e ensaio.
- Mudar o corte de data (`release_date`).

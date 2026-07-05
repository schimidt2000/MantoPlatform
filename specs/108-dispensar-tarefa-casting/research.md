# Research — Dispensar Tarefa de Casting (108)

## R1. Causa raiz do cargo "fantasma"

`app/calendar/routes.py`, função de sincronização (~linha 1893):

```python
characters = parse_characters(title)
existing = {r.character_name: r for r in event.roles if r.role_type != "extra"}
...
for name, role in list(existing.items()):
    if strip_role_prefix(name) not in characters:
        ...
        db.session.delete(role)          # apaga cargo cujo personagem sumiu do título
for char in characters:
    if char in existing:
        pass                              # já existe → não mexe
    elif char in existing_norm:
        ...                                # renomeia preservando assignment
    else:
        db.session.add(EventRole(event_id=event.id, character_name=char))  # cria novo
```

Excluir manualmente um cargo o remove de `existing`. Na sync seguinte, o personagem continua
no título → cai no ramo `else` → cargo recriado do zero (sem talento, sem histórico).

**Decision**: não mexer nessa função. Um cargo **dispensado permanece no banco** — continua
aparecendo em `event.roles` e em `existing`, então cai sempre no ramo `if char in existing:
pass`. A sync passa a tratá-lo exatamente como trataria um cargo pendente comum: não apaga,
não recria. É a característica que faz a solução funcionar sem tocar no sync.

**Alternatives considered**: fazer a sync "pular" nomes de personagens dispensados (ignorá-los
no parse do título) — mais frágil (dependeria de casar texto do título com estado do banco a
cada sync) e tocaria a função mais sensível do sistema. Rejeitado — Princípio IV.

## R2. Onde a dispensa deve poder ser acionada

Cenário relatado: usuário está na lista de tarefas pendentes da home, quer resolver vários
cargos obsoletos sem abrir cada evento. Rotas HTTP dedicadas (fora do dispatch genérico de
`event_detail`, que sempre redireciona para a página do evento) permitem acionar direto da
home e voltar para ela.

**Decision**: `POST /roles/<int:role_id>/dismiss` e `POST /roles/<int:role_id>/restore` em
`calendar_bp`, redirecionando para `request.referrer` (fallback: `url_for("home")`).

## R3. Escopo do RBAC

Spec FR-006 é explícita: só SUPERADMIN. Difere do padrão de exclusão de cargo
(`_handle_delete_role`, que aceita CASTING+SUPERADMIN) porque dispensar é uma decisão sobre o
que conta como "tarefa" do time inteiro, não uma correção pontual de casting.

**Decision**: reusar `_is_superadmin()` já definido no módulo (linha 933); as rotas abortam
com 403 fora desse papel — sem exceção para CASTING.

## R4. Onde e como listar os cargos dispensados (US2)

Precisa ser reversível e auditável (spec FR-007, SC-004) sem virar uma tela nova. A home já
usa o padrão `sector-panel`/`sector-body` com `toggleSector()` para seções recolhíveis
(Casting, Ensaio, etc.).

**Decision**: dentro do próprio `sector-panel` de Casting, um sub-bloco "🗂 N dispensada(s)"
— só renderizado quando `is_superadmin` — com lista simples (personagem, evento, quem/quando
dispensou, botão Restaurar). Reusa o CSS de `task-row` existente. Sem toggle próprio
(a seção Casting já é recolhível); o sub-bloco fica sempre visível dentro dela quando há
itens, evitando esconder uma ação de reversão dentro de mais uma camada de clique.

## R5. Migration

Duas colunas nullable em `event_roles`:

| Coluna | Tipo | Regra |
|---|---|---|
| `dismissed_at` | DateTime | nullable — momento da dispensa; `NULL` = pendente normal |
| `dismissed_by` | Integer FK `users.id` | nullable — quem dispensou |

`down_revision` = head atual `a3b4c5d6e7f8` (feature 105). Sem backfill necessário — todos os
cargos existentes ficam com `dismissed_at IS NULL` (comportamento idêntico ao atual).

## R6. Contagem dos setores

`total_casting`/`done_casting`/`pending_casting` hoje somam TODOS os cargos (com e sem
talento) do escopo. Cargo dispensado deve sair de todas as três contagens — a spec trata o
cargo dispensado como algo que "não existe de verdade" para fins de casting (não é "feito",
nem "pendente", nem parte do "total"). Cada uma das três queries em `app/__init__.py` ganha
`EventRole.dismissed_at.is_(None)` no filtro.

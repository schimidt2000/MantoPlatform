# Implementation Plan: Salvar talento e cachê do casting de forma confiável

**Branch**: `138-salvar-cache-talento-evento` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/138-salvar-cache-talento-evento/spec.md`

## Summary

O usuário pediu para "reformular a arquitetura" da escalação de casting porque, às vezes,
salvar um personagem grava a pessoa mas não o cachê, ou vice-versa. Investigação do código
atual (`app/calendar/routes.py::_handle_assign_casting`, `app/templates/event_detail.html`
componente `.ts-wrap`) mostrou que a rota de salvamento já é atômica — talento e cachê são
persistidos juntos, na mesma requisição e no mesmo `db.session.commit()`. A causa real está
na interface, em dois pontos concretos:

1. O campo de busca de talento (`.ts-input`) é só um texto livre; o campo que realmente
   viaja no formulário (`talent_id`, hidden) só é atualizado dentro da função `pick()`,
   disparada exclusivamente pelo clique/Enter numa sugestão da lista. Se o usuário digita
   um nome e clica direto em "Salvar" sem confirmar a sugestão (ex.: a lista fechou, ou ele
   não reparou que precisava clicar), o texto na tela muda mas o `talent_id` enviado é o
   antigo (ou vazio) — o formulário parece preenchido, mas não está.
2. Não existe nenhum aviso/feedback de sucesso após salvar (`_handle_assign_casting` só
   grava `EventLog`, nunca chama `flash()`) — o usuário não tem confirmação textual do que
   foi realmente salvo, só a suposição visual.

Não é preciso mudar como o dado é modelado ou persistido (não há limitação de arquitetura
de dados). A correção é uma validação/feedback de interface: bloquear o salvamento quando o
texto do campo de busca não corresponde a uma seleção confirmada (com mensagem clara e sem
apagar o que foi digitado, mesmo padrão já usado na validação de `event_create.html`,
feature 134), e adicionar `flash()` de sucesso confirmando exatamente o que foi salvo
(nome + cachê).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy (backend inalterado na sua forma);
JavaScript vanilla (sem framework) no template

**Primary Dependencies**: nenhuma nova — reaproveita o componente `.ts-wrap` já existente
(`initSearch()` em `event_detail.html`) e o padrão de banner de erro/flash já usado no
projeto

**Storage**: nenhuma mudança de schema — `EventRole.talent_id`/`cache_value` continuam
como estão

**Testing**: script de verificação funcional com Flask test client contra `manto_local`
(padrão do projeto) simulando exatamente o POST que o formulário envia hoje, com e sem
`talent_id` preenchido, para confirmar que o backend já é atômico; validação da interface
(bloqueio de submit) é coberta por um teste de sintaxe/lógica do JS extraído (`node
--check`) e por revisão manual do fluxo, já que não há navegador automatizado no projeto

**Target Platform**: aplicação web server-side (Flask + Jinja2), componente reused em duas
seções de `event_detail.html` (Elenco/personagens e Equipe de Apoio)

**Project Type**: web application (monolito Flask existente)

**Performance Goals**: N/A — mudança é validação client-side + uma chamada `flash()`
extra, sem impacto de performance

**Constraints**: não pode mudar a regra de teto de cachê (cap) nem o fluxo de convite por
e-mail — ambos continuam exatamente como hoje; a correção deve valer igualmente para a
seção "Elenco" (personagens) e "Equipe de Apoio" (extras), que reaproveitam o mesmo
componente `.ts-wrap`

**Scale/Scope**: um componente JS (`initSearch`), um handler de rota
(`_handle_assign_casting`) e os dois pontos do template que o usam

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: a correção estende o componente `.ts-wrap`/`initSearch`
  já existente (usado em 3+ lugares do arquivo) em vez de criar um componente de busca
  novo; o padrão de erro visível reaproveita o mesmo estilo (`.field-error`/shake) já usado
  em `event_create.html` (feature 134) — não inventa um padrão de validação novo.
- **II. Padrões de código Python**: `_handle_assign_casting` ganha uma chamada `flash()`
  adicional, sem crescer além do limite de função (já teria que ser quebrada se
  crescesse muito — hoje está em ~85 linhas; verificar no Phase 1 se cabe sem refatorar,
  ou extrair uma pequena helper de mensagem se necessário).
- **III. Arquitetura em camadas**: nenhuma mudança de camada — a rota continua só
  orquestrando; a validação nova é de interface (client-side), não regra de negócio nova.
- **IV. Não quebrar o que funciona**: a rota de salvamento em si NÃO muda de
  comportamento para requisições já válidas (talent_id+cache_value corretos) — só passa a
  bloquear ANTES de enviar quando a seleção não foi confirmada. Verificação funcional cobre
  o caminho feliz (sem regressão) e o caminho de bloqueio.
- **V. UI/UX consistente e com feedback (NÃO-NEGOCIÁVEL)**: esta feature é, no fundo, uma
  aplicação direta do princípio V — "falha de validação sempre tem feedback visível no
  campo" e "nunca limpar o que o usuário preencheu". A correção implementa exatamente isso
  para o campo de busca de talento, que hoje viola os dois.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/138-salvar-cache-talento-evento/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`/`quickstart.md`: causa raiz já identificada
por investigação direta do código existente (não há incógnita técnica a pesquisar), sem
entidade nova, sem interface externa nova.

### Source Code (repository root)

```text
app/
├── calendar/
│   └── routes.py        # _handle_assign_casting(): flash() de sucesso confirmando
│                         #   nome + cachê salvos
└── templates/
    └── event_detail.html # initSearch(): rastreia texto "confirmado" (nome do talento
                          #   selecionado via pick()/clear()); handler de submit no form
                          #   bloqueia e mostra erro inline se o texto não bate com uma
                          #   seleção confirmada, sem apagar os campos já preenchidos
```

## Design Decisions

1. **`initSearch()` passa a rastrear a seleção confirmada** — variável `confirmedName`
   inicializada com o nome do talento atualmente salvo (mesmo valor que já preenche
   `text.value` no carregamento da página), atualizada só dentro de `pick()` (nome do
   talento escolhido) e `clear()` (string vazia). Isso dá uma fonte única de verdade para
   "o que está realmente confirmado" versus "o que está só digitado".

2. **Guard de submit no `<form>` de cada vaga** — listener `submit` no formulário que
   engloba o `.ts-wrap`: compara `text.value.trim()` com `confirmedName`. Se diferentes:
   - `e.preventDefault()` (não envia, não perde nada digitado);
   - mostra uma mensagem inline pequena (reaproveitando o padrão visual `.field-error`
     de `event_create.html`) logo abaixo do campo de busca — texto adaptado ao caso:
     - texto não vazio sem selecionar: "Selecione um talento da lista de sugestões (ou
       apague o campo para deixar sem talento)."
     - texto apagado manualmente sem clicar no ×, mas ainda havia talento salvo:
       "Confirme: clique no × para remover o talento, ou selecione um novo da lista."
   - foca o campo de busca (mesmo padrão de "scroll até o erro" da feature 134, aqui
     mais simples por ser um campo só).
   - Estado válido para submeter continua sendo: texto vazio + hidden vazio (sem
     talento), OU texto igual ao `confirmedName` + hidden preenchido (talento
     confirmado) — exatamente os dois casos que hoje já funcionam certo.

3. **`_handle_assign_casting` ganha feedback de sucesso** — depois do commit, `flash()`
   com uma mensagem curta reaproveitando os dados já calculados para o `EventLog` (nome do
   talento + cachê, ou só "vaga atualizada" quando não há talento) — sem duplicar lógica,
   só formatando a mesma informação que já era logada. Isso fecha o FR-004 (resultado do
   salvamento visível de imediato) sem depender só da leitura visual do card recarregado.

4. **Nenhuma mudança em `_handle_assign_casting` além do `flash()`** — o cálculo de
   `new_cache`/aplicação de cap/envio de convite/e-mail continuam idênticos; a atomicidade
   já existia (mesmo commit para talent_id e cache_value), então FR-001/FR-002 já são
   satisfeitos pelo backend assim que o frontend passa a garantir que só envia dados
   confirmados (item 1/2 acima).

5. **Verificação funcional (T00x)**: script novo (`scripts/db/verify_138_*.py`, gitignored)
   confirmando pelo test client que uma request de `assign_casting` com `talent_id` e
   `cache_value` preenchidos salva os dois juntos (comportamento já correto hoje — serve
   de teste de regressão), que enviar só `cache_value` (talent_id ausente/vazio) preserva
   o talento anterior sem apagá-lo, e vice-versa. A parte de bloqueio de submit (JS) é
   verificada via `node --check` no trecho extraído + inspeção do fluxo, já que é
   comportamento client-side puro sem servidor envolvido.

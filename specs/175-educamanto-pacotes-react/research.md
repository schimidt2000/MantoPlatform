# Research: EducaManto — Pacotes e Conteúdos em React

Nenhum `NEEDS CLARIFICATION` restou no Technical Context — o domínio já está implementado e
testado no Jinja legado e na calculadora React (feature 171); esta fatia é migração de UI +
extração de núcleo de negócio, não decisão tecnológica nova.

## Decisão: reaproveitar `pricing_ops.py`/`pdf.py` sem alteração

- **Decisão**: os dois módulos que fazem cálculo e geração de PDF do orçamento continuam
  exatamente como estão; a API só os chama.
- **Racional**: já são funções puras (sem `flask.request`/`render_template`), já usadas pela
  calculadora React da feature 171 — reescrevê-los violaria o Princípio I (reutilizar antes de
  criar).
- **Alternativas consideradas**: nenhuma — não há necessidade de mudança.

## Decisão: extrair `package_ops.py` das views Jinja de CRUD

- **Decisão**: mover a lógica de criar/editar/duplicar/excluir pacote (hoje só dentro de
  `create_package`/`edit_package`/`duplicate_package`/`delete_package` em
  `app/educamanto/routes.py`) para `app/educamanto/package_ops.py`; a view Jinja passa a chamar
  essas funções.
- **Racional**: mesmo padrão de todas as fatias anteriores (145-174) — regra de negócio nunca
  duplicada entre Jinja e API (Princípio I/III). Hoje a lógica só existe uma vez (na view), então
  a extração é estritamente uma refatoração sem mudança de comportamento.
- **Alternativas consideradas**: duplicar a lógica direto na API — rejeitado (violaria a
  constituição e o padrão já estabelecido).

## Decisão: download de PDF via `apiFetchBlob`

- **Decisão**: o botão "Gerar orçamento" na calculadora chama `apiFetchBlob` (já existente em
  `@manto/api-client` desde a feature 160) para baixar o PDF, em vez de navegação de página cheia.
- **Racional**: é o padrão já estabelecido no projeto para downloads binários autenticados via
  cookie de sessão; evita reinventar.
- **Alternativas consideradas**: `<a href>` direto para a rota — rejeitado, pois a API não deve
  responder HTML/redirecionamento e o download precisa do cookie de sessão + tratamento de erro
  padrão (`ApiRequestError`).

## Decisão: formulário de pacote com react-hook-form + zod

- **Decisão**: o formulário de criar/editar pacote (nome, margens, dias de desconto, comissão,
  itens) usa `react-hook-form` + `zod`, mesmo padrão de outras telas de CRUD do painel interno.
- **Racional**: consistência com o resto do app; validação de campo com feedback visível
  (Princípio V) já vem pronta com esse par de bibliotecas, já em uso no projeto.
- **Alternativas considerados**: estado manual com `useState` por campo — rejeitado por gerar
  mais código repetido do que o padrão já adotado.

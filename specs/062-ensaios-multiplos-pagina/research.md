# Research: Múltiplos ensaios + página de ensaio simplificada (062)

Decisões técnicas. Sem `NEEDS CLARIFICATION`.

## 1. Múltiplos ensaios por evento — estado atual

- O vínculo já é **um-para-muitos**: `CalendarEvent.parent`/`backref ensaios`
  (`models.py`). `create_ensaio` cria um ENSAIO novo apontando `parent_event_id` ao show — **não
  bloqueia** um segundo. A página do evento (`event_detail.html`) mostra o form "Marcar Ensaio"
  para qualquer show (gate `event_type != 'ENSAIO'`, **sem** `not event.ensaios`).
- **Gap real**: na home, um show com ensaio sai de "falta agendar" para "agendados", e o card de
  agendados só oferece editar/cancelar — não há "marcar **outro** ensaio".
- **Decisões**:
  - Adicionar na home, no card de "Ensaios agendados", um form inline **"+ Marcar outro
    ensaio"** que posta em `/events/<show_id>/create-ensaio` com `redirect_to=home`.
  - `create_ensaio` passa a honrar `redirect_to` (`"home"` → volta à home; senão → página do
    show), espelhando o que `edit_ensaio` já faz.
  - (Opcional/clareza) o `summary` do form na página do show vira "Marcar outro ensaio" quando já
    houver ensaios.

## 2. Página de ensaio simplificada

- **Problema**: `event_detail` renderiza `event_detail.html` com flags **por papel**
  (`show_casting`, `show_figurino`, `show_comercial`...), então um ENSAIO aberto por
  casting/admin mostra todos os painéis do show.
- **Decisão**: em `event_detail`, **branch antecipado** — se `event.event_type == "ENSAIO"`,
  renderizar um template dedicado **`ensaio_detail.html`** e retornar, **antes** das consultas
  pesadas (talentos, contratos, pagamentos, figurino, conflitos, agrupáveis). Calcular só:
  `show_ensaio` (via `_CAN_ENSAIO`), `event.parent`, `logs` (já montados), `settings`.
- **Rationale**: Princípio I/III — evita carregar/expor o que não é do ensaio; mais leve; isola a
  visão. Alternativa rejeitada: condicionar dezenas de painéis dentro de `event_detail.html`
  (frágil e mantém o custo das queries).
- **Conteúdo da página**: cabeçalho (título + selo ENSAIO), card com data/hora, local,
  descrição; bloco "Show de origem" (link para o show se `parent`, ou aviso de órfão);
  ações **editar** (form inline → `edit-ensaio`, `redirect_to=ensaio`) e **cancelar**
  (`delete-ensaio`) para `show_ensaio`; histórico (logs) opcional.

## 3. Navegação pós-ação

- **edit_ensaio**: adicionar `redirect_to == "ensaio"` → volta para a própria página do ensaio
  (`event_detail(ensaio_id)`, que agora renderiza a versão simplificada). Mantém `"event"` e o
  default home.
- **delete_ensaio**: já redireciona para o show pai (ou home se órfão) — adequado, pois o ensaio
  deixa de existir. Sem mudança.

## 4. Permissões

- Editar/cancelar ensaio seguem `_CAN_ENSAIO` (ENSAIO/CASTING/SUPERADMIN), como hoje. Demais
  usuários veem a página simplificada em leitura.

## 5. Sem mudança de modelo / migration

- **Decisão**: nenhuma. Tudo já existe no modelo; mudança é de rota/exibição.

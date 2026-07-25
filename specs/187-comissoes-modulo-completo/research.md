# Research: Reestruturação do Módulo de Comissões

## 1. Confirmação de pagamento em lote: `window.confirm()` vs. `Dialog` novo

**Decision**: construir um componente `Dialog` mínimo em `@manto/ui` (baseado em
`<dialog>`/portal + Framer Motion, sem dependência nova de pacote) e usá-lo na confirmação de
"Pagar Mês".

**Rationale**: a Constituição v2.0.0, Princípio V, é explícita — "Ações destrutivas (deletar,
remover) exigem confirmação via modal/dialog do `shadcn/ui`" — e a liquidação em lote é uma
ação financeira irreversível na prática (não há "desfazer" na spec). A nota em `CLAUDE.md`
sobre `window.confirm()` ser "o padrão já usado no projeto" é anterior à migração 2.0.0 da
constituição e descreve um débito técnico, não uma regra a seguir. Além disso `window.confirm()`
não permite exibir o valor formatado (`R$ X.XXX,XX`) com ênfase visual nem o nome do vendedor
em negrito — a spec (FR-011) pede uma mensagem estruturada.

**Alternatives considered**:
- Manter `window.confirm()`: rejeitado — viola Princípio V e a UX pedida na spec (FR-011) não é
  atingível com uma caixa de texto puro do navegador.
- Instalar Radix UI/shadcn CLI completo: rejeitado por ora — nenhum outro componente do design
  system usa Radix hoje; adicionar a dependência só para um `Dialog` é desproporcional. Um
  `Dialog` local (foco preso, `Escape` fecha, clique fora fecha, animação de entrada/saída via
  Framer Motion) cobre o que a spec pede sem nova dependência de build.

## 2. Onde extrair a lógica de negócio (evitar 3ª duplicação)

**Decision**: novo módulo `app/financeiro/comissoes_ops.py`, com funções puras (sem
`flask.request`), consumidas apenas pelos endpoints de API (`app/api/financeiro_read.py` e
`financeiro_write.py`). A view Jinja (`app/financeiro/routes.py`) e sua cópia de
`_bulk_set_commission_period` **não são alteradas nem redirecionadas** para o novo módulo —
ficam exatamente como estão hoje, por instrução explícita do usuário de não tocar o Jinja
legado, mesmo sabendo que isso mantém uma duplicação pré-existente fora do escopo desta feature.

**Rationale**: segue o padrão já estabelecido no projeto (`<blueprint>/<dominio>_ops.py`
reusado só pela API quando a view legada não pode ser tocada — ver precedente em
`app/figurino/*_ops.py` reusado só por API em blueprints já 100% migrados). Resolve o Princípio
I para o código *novo* sem expandir o escopo da mudança para arquivos fora do combinado.

**Alternatives considered**:
- Refatorar `app/financeiro/routes.py` para importar de `comissoes_ops.py` também: rejeitado —
  o usuário pediu explicitamente para não tocar o Jinja legado nesta feature; fica registrado
  como débito técnico pré-existente, não como algo a resolver aqui.

## 3. Tipo de `paid_at` (Date vs. DateTime) para atender "NOW()"

**Decision**: manter `CommissionPayment.paid_at` como `db.Date` (sem migração). A liquidação em
lote grava `date.today()` (fuso `America/Sao_Paulo`), igual ao comportamento já existente em
`_bulk_set_commission_period` e em `set_commission_status`.

**Rationale**: a spec pede "pago_em=NOW()" no sentido de negócio ("registrar quando foi pago
agora"), não literalmente timestamp com hora/minuto — nenhum requisito funcional ou critério de
sucesso depende de granularidade de segundos, e o resto do sistema financeiro (`SalaryPayment`,
`EventRole.payment_status`) usa a mesma convenção de `date.today()`. Evita migração de schema,
que o usuário pediu para evitar quando possível.

**Alternatives considered**:
- Migrar `paid_at` para `db.DateTime`: rejeitado — sem requisito funcional que dependa disso, e
  toda a mudança de schema exigiria migration manual + validação em `manto_local`, custo não
  justificado pelo ganho.

## 4. Atomicidade real da liquidação em lote

**Decision**: `comissoes_ops.pay_seller_month(seller_id, month, actor_id) -> PayoutResult` faz
um único `SELECT ... FOR UPDATE`-like (via `with_for_update()` do SQLAlchemy) dos registros
elegíveis, aplica as mudanças em memória, e um único `db.session.commit()` no final — dentro do
mesmo request/transação Flask-SQLAlchemy (uma transação por request já é o padrão do projeto).
Se qualquer exceção ocorrer antes do commit, `db.session.rollback()` garante que nada é
persistido parcialmente.

**Rationale**: corrige a causa raiz do bug relatado — hoje `_bulk_set_commission_period` itera e
muta objetos em memória sem lock, e o commit acontece no chamador (`api_bulk_payment_action`)
misturado com outras entidades (cachês, salários, gastos) na mesma transação, o que por si só já
é atômico a nível de banco mas não é *isolado* nem *auditável* como uma operação de negócio
própria — duas requisições concorrentes podem ler o mesmo conjunto "elegível" antes de qualquer
commit e processar os mesmos registros duas vezes (ambas decidem pagar, ambas fazem
`UPDATE ... SET status='pago'`, sem erro, mas o segundo commit é redundante e não é reportado
ao usuário como "nada mudou"). O `with_for_update()` fecha essa janela: a segunda transação
concorrente bloqueia até a primeira commitar, então relê o estado e encontra 0 registros
`a_pagar` elegíveis, retornando `changed=0`.

**Alternatives considered**:
- Só um loop simples com commit único (sem lock): resolve a atomicidade "tudo ou nada" mas não
  a corrida entre duas requisições simultâneas (edge case da spec) — insuficiente.
- Lock otimista por `updated_at`/versão: mais complexidade que o necessário para o volume de
  dados desta feature (dezenas de vendedores); `with_for_update()` já é suportado nativamente
  pelo Postgres em produção e por `manto_local`.

## 5. Exportação CSV — client-side vs. endpoint novo

**Decision**: gerar o CSV no cliente (`frontend/apps/internal`), a partir dos dados já
carregados pela mesma query de resumo por vendedor (sem endpoint novo).

**Rationale**: não há regra de negócio no CSV — é uma serialização direta do que já está na
tela (mesmos números que os KPIs, garantindo SC-004 "bate centavo a centavo" por construção,
já que é o mesmo payload). Evita superfície de API nova só para download, e evita duplicar a
formatação de números entre backend e frontend.

**Alternatives considered**:
- Endpoint `GET /api/financeiro/comissoes/export.csv`: rejeitado por ora — adicionaria
  serialização CSV no backend (Content-Type texto, não JSON, quebrando a convenção "backend só
  responde JSON" do Princípio III sem necessidade real) para um dado que o cliente já tem.

# Research: Transporte explícito por dias no EducaManto + calculadora em React

## 1. Onde aplicar o multiplicador de dias no transporte

**Decision**: Multiplicar o `total` já calculado (tarifa por km ida/volta + adicional por pessoa,
`vt + afsp`) pelo número total de dias do pacote (`d1 + d2`, mínimo 1), tanto na tela Jinja
(`calcTransporte()` em `templates/educamanto/index.html`) quanto no novo `pricing_ops.py` usado pela
API/React.

**Rationale**: O pedido do usuário ("a depender da quantidade de dias, já faça essa multiplicação
para o valor total") e o cenário de negócio (apresentações fora de SP em múltiplos dias exigem uma
ida e volta por dia) apontam para multiplicar o TOTAL da viagem, não só a tarifa por km — o adicional
por pessoa também se repete a cada viagem. Manter a fórmula de uma viagem intacta (reusada de
`app/orcamento/transport.py`) e só multiplicar o resultado final evita duplicar/alterar a fórmula
original, que continua sendo usada sem alteração pela calculadora de orçamento (que não tem conceito
de múltiplos dias).

**Alternatives considered**:
- Multiplicar só a tarifa por km (`vt`), mantendo o adicional por pessoa (`afsp`) fixo por evento →
  rejeitado: não reflete o custo real (a equipe também precisa do adicional por pessoa a cada
  viagem/dia).
- Criar um novo campo de configuração ("multiplicador de dias") editável pelo super admin →
  rejeitado por over-engineering; o total de dias já é um dado de entrada existente do pacote
  (`d1 + d2`), sem necessidade de configuração adicional.

## 2. Formato do endpoint de cálculo para a tela React

**Decision**: `POST /api/educamanto/calcular` recebendo `{ package_id, d1, d2, ensemble, acrescimo,
transporte: { km_ida, tipo, carretinha, num_carros, pessoas } }` e devolvendo o breakdown completo
(itens, valor base, desconto, transporte com multiplicador de dias, totais sem/com nota). Vive em
`app/api/educamanto_read.py` (é uma operação de leitura/cálculo, não persiste nada), mas usa POST por
causa do corpo aninhado (convenção já aceita no projeto para "ações" de cálculo que não cabem em
query string).

**Rationale**: A Constituição (Princípio III) proíbe lógica de negócio no frontend — a fórmula
completa de precificação do pacote (itens × custo × margem, desconto por dias, ensemble) e a de
transporte com multiplicador de dias precisam existir em Python para servir a tela React. Um único
endpoint de cálculo evita expor múltiplas regras de negócio fragmentadas em vários endpoints
pequenos, e mantém a tela React simples (um POST a cada mudança relevante de input, com debounce).

**Alternatives considered**:
- Devolver só os dados crus do pacote (itens/margens) via GET e recalcular tudo em TypeScript no
  React → rejeitado: duplicaria a fórmula de precificação em TS, violando Princípio I (fonte única)
  e III (lógica de negócio fora do backend).
- GET com todos os parâmetros em query string → rejeitado: o objeto `transporte` aninhado e a lista
  de parâmetros tornam a query string difícil de manter; POST é mais claro para este payload,
  seguindo o mesmo raciocínio já usado em `/educamanto/orcamento/gerar` (também um POST que não
  persiste "recurso" no sentido REST estrito, e sim dispara um cálculo/ação).

## 3. Escopo da tela React: só a calculadora

**Decision**: A tela React cobre exclusivamente pacote + dias + ensemble + transporte + totais +
detalhamento (o que o usuário confirmou como "calculadora completa"). Geração de PDF, histórico de
orçamentos e CRUD de pacotes continuam só na tela Jinja, com um link de saída visível na tela React.

**Rationale**: Decisão confirmada interativamente com o usuário antes da redação do spec — evita que
esta fatia vire uma migração completa do módulo EducaManto (que nunca foi atribuída a nenhuma das 6
User Stories da migração 144), mantendo o escopo do pedido original (mostrar/multiplicar transporte)
com a adição pontual da tela React.

**Alternatives considered**:
- Migrar o módulo EducaManto inteiro (PDF, histórico, CRUD de pacotes) nesta mesma fatia → rejeitado
  por escopo desproporcional ao pedido original; vira uma iniciativa própria se o usuário quiser no
  futuro.
- Criar só um componente isolado de transporte em React, sem replicar o resto da calculadora →
  rejeitado pelo usuário na pergunta de esclarecimento (não entrega valor sozinho, pois o transporte
  só faz sentido somado ao valor final do pacote).

## 4. Reuso da fórmula de transporte entre `app/orcamento` e `app/educamanto`

**Decision**: `app/educamanto/pricing_ops.py` importa `calcular_van`/`calcular_carro` de
`app.orcamento.transport` e só adiciona o multiplicador de dias por fora (sem tocar no módulo do
orçamento).

**Rationale**: Mesma fonte de configuração de transporte (`SiteSetting` via `app.orcamento.settings`)
já é reusada desde a feature 076; o multiplicador de dias é um conceito exclusivo do EducaManto
(pacotes multi-dia), então fica encapsulado no módulo do EducaManto, sem introduzir um parâmetro
`dias` estranho à API do orçamento (que é sempre de um evento/dia só).

**Alternatives considered**:
- Adicionar um parâmetro `dias: int = 1` diretamente em `calcular_van`/`calcular_carro` no orçamento
  → rejeitado: contamina uma função genérica e usada pelo orçamento (que não tem esse conceito) com
  um parâmetro que só o EducaManto usa.

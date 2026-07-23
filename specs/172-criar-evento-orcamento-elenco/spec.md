# Feature Specification: Corrigir elenco incompleto ao criar evento a partir de orçamento

**Feature Branch**: `172-criar-evento-orcamento-elenco`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "tem um problema ao clicar em criar evento a partir de um orçamento. Ele não está puxando todas informações como antes. Isso na arquitetura Jinja, na react não testei ainda."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Elenco completo ao criar evento a partir de um orçamento salvo (Priority: P1)

Um usuário Comercial/Superadmin salva um orçamento na calculadora (com vários personagens,
coordenador(es), técnico de som e/ou maquiador) e depois clica em "Criar evento" a partir do
histórico de orçamentos. A tela de criação de evento deve abrir já com **todo o elenco** do
orçamento pré-preenchido — não apenas parte dele — assim como já preenche hoje data, horário,
local, cliente e valores financeiros.

**Why this priority**: É o problema relatado diretamente pelo usuário — hoje a tela de criação
de evento (fluxo Jinja, `/events/new?orcamento_id=<id>`) não está trazendo o elenco completo do
orçamento como trazia antes, obrigando o usuário a digitar novamente personagens que já haviam
sido definidos na calculadora. Isso é retrabalho e risco de divergência entre o que foi
orçado/vendido e o que é efetivamente escalado no evento.

**Independent Test**: Salvar um orçamento com pelo menos 3 personagens de tipos diferentes
(ator, cantor, especial) + coordenador + técnico de som (evento com show), depois abrir
"Criar evento" a partir desse orçamento e conferir que todas as linhas de elenco aparecem
corretamente (nome, cachê aplicado por duração, sinalização de maquiagem/cantor quando
aplicável) — sem precisar consultar a calculadora de novo.

**Acceptance Scenarios**:

1. **Given** um orçamento salvo com N personagens (atores/cantores/especiais) + coordenador(es)
   + técnico de som, **When** o usuário clica em "Criar evento" a partir desse orçamento,
   **Then** a tela de criação de evento mostra as N linhas de personagem MAIS as linhas de
   equipe (coordenador, técnico, maquiador quando aplicável) — mesma quantidade e mesmos nomes
   do orçamento original.
2. **Given** a tela de criação de evento aberta a partir de um orçamento, **When** o usuário
   seleciona uma duração (1h/2h/3h/4h) diferente da pré-selecionada, **Then** o cachê aplicado
   a cada linha de elenco (usado ao salvar o evento) reflete a duração escolhida, na mesma
   proporção definida na calculadora.
3. **Given** um orçamento sem transporte fora de SP e sem acréscimos, **When** o evento é criado
   a partir dele, **Then** os campos financeiros (venda bruta/líquida, transporte, acréscimo)
   continuam sendo preenchidos como hoje (esse comportamento já funciona e não deve regredir).

---

### Edge Cases

- Orçamento antigo cujo snapshot salvo não tem a estrutura atual de `performers` (formato
  anterior a mudanças na calculadora): a tela de criação de evento deve abrir sem erro, mesmo
  que o elenco venha vazio nesse caso raro (paridade com o comportamento silencioso já existente
  para orçamento inexistente/id inválido).
- Orçamento sem nenhum personagem cadastrado (raro, mas possível): tela abre com uma única linha
  de personagem em branco, como no fluxo manual (sem orçamento) — não deve travar nem mostrar
  erro.
- Orçamento com show (técnico de som incluído) vs. sem show (sem técnico): a linha de "Técnico
  de Som" só deve aparecer quando o orçamento tiver show, como já ocorre na calculadora.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao abrir a tela de criação de evento a partir de um orçamento
  (`/events/new?orcamento_id=<id>`, fluxo Jinja), o sistema DEVE pré-preencher uma linha de
  elenco para cada personagem (ator, cantor, especial) presente no orçamento salvo, com nome e
  cachê aplicável por duração.
- **FR-002**: O sistema DEVE também pré-preencher as linhas de equipe do orçamento — coordenador
  (na quantidade orçada), técnico de som (quando o orçamento tiver show) e maquiador (quando
  houver personagem com maquiagem) — na mesma tela.
- **FR-003**: Ao salvar o evento criado a partir de um orçamento, o cachê de cada personagem/
  vaga de equipe gravado DEVE corresponder à duração selecionada pelo usuário na tela de
  criação (1h/2h/3h/4h ou duração customizada), usando os valores originalmente calculados no
  orçamento.
- **FR-004**: O comportamento hoje já funcional (data, horário, local, nome do cliente, valores
  financeiros — venda, transporte, acréscimo, indicação de nota fiscal) NÃO deve regredir com
  esta correção.
- **FR-005**: Caso o orçamento referenciado não exista ou o snapshot esteja incompleto/antigo, a
  tela de criação de evento DEVE abrir normalmente (sem elenco pré-preenchido nesse caso), sem
  erro para o usuário — mesma paridade silenciosa já usada hoje para orçamento inexistente.
- **FR-006**: A correção é escopo do fluxo Jinja (`/events/new`) usado a partir do histórico de
  orçamentos hoje em produção. A tela React equivalente (`EventCreatePage`, ainda não testada
  pelo usuário nesse fluxo) deve ser conferida à parte — se o mesmo problema for reproduzido lá,
  vira um FR adicional só depois de confirmado (ver Assumptions).

### Key Entities

- **OrcamentoHistory**: registro do orçamento salvo (snapshot congelado usado como fonte do
  pré-preenchimento); já existe, não é alterado por esta correção.
- **Elenco do orçamento (personagens + equipe)**: lista derivada do snapshot do orçamento —
  cada item tem nome, tipo (personagem/coordenador/técnico/maquiador), cachê por duração e
  flags de maquiagem/canto. É essa lista que precisa chegar completa na tela de criação de
  evento.
- **EventRole**: vaga de elenco do evento sendo criado; recebe o cachê vindo do orçamento no
  momento em que o evento é salvo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das linhas de elenco (personagens + equipe) presentes em um orçamento salvo
  aparecem na tela de criação de evento aberta a partir dele — verificado com pelo menos 3
  orçamentos reais existentes (variando quantidade e tipos de personagem, com e sem show).
- **SC-002**: Um usuário Comercial consegue criar um evento a partir de um orçamento sem
  precisar redigitar manualmente nenhum personagem/cachê que já constava no orçamento.
- **SC-003**: Nenhum campo hoje funcional (data, local, cliente, financeiro) deixa de ser
  preenchido após a correção — comparado por paridade antes/depois do fix.

## Assumptions

- O relato do usuário é sobre o fluxo **Jinja** (`/events/new?orcamento_id=<id>`, acessado pelo
  histórico de orçamentos em `/orcamento/historico`); o fluxo React (`EventCreatePage`, feature
  152) ainda não foi testado pelo usuário para esse cenário e fica fora do escopo desta correção
  até ser confirmado como afetado.
- Investigação inicial (leitura de código + teste direto contra `manto_local` com orçamentos
  reais recentes) mostrou que a função que monta o elenco a partir do orçamento
  (`_build_orcamento_prefill`/`_compute_performer_caches` em `app/calendar/routes.py`) devolve
  a lista de elenco completa e correta para os orçamentos testados — ou seja, a causa raiz
  provavelmente não está no cálculo em si, e sim em algum ponto entre esse dado e o que
  efetivamente aparece pré-preenchido na tela para o usuário (ex.: renderização/JS da tela,
  ou um orçamento específico com snapshot em formato diferente do testado). O `/speckit-plan`
  deve investigar tecnicamente onde exatamente a informação se perde antes de propor a mudança.
- Nenhuma mudança de schema é esperada — é uma correção de comportamento, reusando
  `OrcamentoHistory`/`EventRole` como já existem.

# Specification Quality Checklist: O artista passa a ver quando o evento termina, quando é o ensaio e de onde sai

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Iteração 1 (2026-09-22)** — **15 de 16 passam**. O único item aberto é o dos marcadores, e são
**dois**, ambos deliberados e endereçados ao `/speckit-clarify`:

1. **Ensaio marcado em show sem elenco** (Casos de borda). Dos 10 ensaios futuros do espelho, 2
   estão em shows sem ninguém escalado — ninguém os verá. As duas leituras levam a features de
   tamanho diferente: "aceitável, é estado normal de um show que ainda vai ser escalado" não custa
   nada; "a produção também precisa ser avisada" acrescenta uma segunda condição ao aviso interno
   da História 4 e um cenário ao verify.
2. **403 × 404 na ficha de figurino** (Premissas). O endpoint recusa com 403 e a mensagem "Você
   não está escalado neste evento", o que confirma a um estranho que o evento existe; o Princípio
   XIII manda 404. Não dá para trocar em silêncio: muda o texto que a tela mostra hoje. É
   pergunta de conformidade, não de escopo, e o dono decide se entra aqui ou vira dívida.

Nenhum dos dois bloqueia as Histórias 1 e 2 (o MVP).

**Sobre "No implementation details" e "Written for non-technical stakeholders"** — marcados como
atendidos, com a leitura que o template da Manto impõe:

- O `spec-template.md` adaptado **exige** a seção `### RBAC` com método e rota e a seção
  `Verificação (verify_NNN.py)` com caminho de arquivo (constituição, Princípios VIII e XIII).
  Rota e caminho aparecem **só** nessas duas seções, que são contrato do repositório.
- A seção "O pedido" descreve o que o levantamento achou em termos do que a pessoa vê na tela:
  "o horário final chega ao navegador e é descartado", "o ensaio é invisível para quem vai
  ensaiar". Os números vêm do espelho, não do código.
- As Histórias, os Critérios de Sucesso e FR-001 a FR-016 falam de pessoa, tela, ação e recusa.
  As duas exceções aparentes são **regras de negócio disfarçadas de detalhe técnico**, e estão
  ali porque mudam o que a pessoa vê: FR-006a (o horário é que faz a linha existir, não o local) e
  FR-013a/FR-013b (a janela em que servidor e site estão em versões diferentes — é literalmente
  "a tela do artista fica branca", não uma preferência de arquitetura).

**Itens que passaram e por quê (os que costumam falhar)**

- *Success criteria measurable*: SC-002 ("hoje encontra em 0% dos casos"), SC-005 ("nenhuma das
  289 escalações que não são de personagem") e SC-007 ("hoje, em 11 eventos, ninguém é") são
  conferíveis sem abrir código.
- *Scope bounded*: "Fora de escopo" nomeia os nove vizinhos que escapam por engano, incluindo os
  três que um implementador faria por conta própria — criar tela de detalhe, remover a lista de
  passados do payload e promover o formatador de horário do app interno.
- *Edge cases*: sete, todos com número medido atrás. Dois deles — logística pela metade e evento
  que deixa de ser show — só apareceram porque a medição foi feita antes da spec, e não depois.

**Correções de fato aplicadas antes de fechar a iteração 1** (achadas por uma passada adversarial
contra o código e o espelho, não pela leitura cruzada dos artefatos):

1. A spec afirmava que o espelho **não tinha** nenhum show com dois ensaios. Tem: 52 pais com um,
   **1 com dois**. Eram 54 filhos para 53 pais — a aritmética não fechava e ninguém a conferiu. O
   cenário 3 continua semeando os dois ensaios, mas agora pelo motivo certo (não depender de uma
   linha de produção), não por uma ausência que não existe.
2. Faltava a regra de **qual campo faz a linha existir**. O formulário interno já nasce com "Manto
   Produções" no local de saída, então 7 eventos têm local sem horário (mais 1 na maquiagem).
   Sem FR-006a, a feature mostraria "Saída: Manto Produções" sem hora em 8 cards — ruído com cara
   de informação.
3. Faltava a trava de **deploy em duas partes**. O site e a API sobem como serviços separados: um
   servidor novo que parasse de enviar a lista de passados deixaria a tela velha chamando um
   método sobre nada, e o card do artista viraria tela branca no celular. Virou FR-013a, e o par
   simétrico virou FR-013b.

**Iteração 2 (2026-09-22, `/speckit-clarify`)** — **16/16**. Quatro perguntas feitas, quatro
respondidas, nenhuma pendência nova aberta. O que mudou na spec:

1. *O bloco também nos Convites?* → **sim** (FR-009a, FR-009b, SC-005a, cenário 6c, História 2
   cenário 5). A pergunta nasceu de uma medição: há **4 convites pendentes** em eventos futuros e
   **2 são de eventos que já têm ensaio marcado** — a pessoa aceita sem saber que vai ter de
   ensaiar. O card de convite é o único lugar da plataforma onde a informação muda uma decisão que
   ainda não foi tomada; é o mesmo argumento que fez o cachê descer para lá na feature 230.
2. *Avisar quando há ensaio sem elenco?* → **não**. Marcar ensaio antes de escalar é ordem normal
   de trabalho. O marcador do caso de borda virou afirmação, com a decisão e o motivo.
3. *403 → 404 na ficha de figurino?* → **não agora**; dívida registrada, com o motivo escrito
   (mudaria o texto que o artista lê e não tem relação com o pedido). Saiu do corpo da spec, entrou
   em Fora de escopo e na lista do `docs/05`.
4. *Consertar "Personagem" também no e-mail e no WhatsApp?* → **sim** (FR-012a, FR-012b, SC-004,
   SC-005, cenário 6b). Esta cresceu a feature de propósito, e cresceu o **defeito** junto: ao
   abrir o código para escrever o requisito, apareceu que a mensagem de WhatsApp passa o local de
   maquiagem **cru** para o texto — ela manda `Local: manto` exatamente como o e-mail. Era a
   terceira superfície do mesmo defeito, e nenhuma pergunta a tinha achado.

Uma decisão **tomada sem gastar pergunta**, registrada nas Premissas: a linha de maquiagem mostra
`Manto Produções` sem o endereço, por simetria com a linha de saída. Anexar o endereço só numa das
duas faria as duas parecerem lugares diferentes, quando são o mesmo prédio.

Contagem ao fim da iteração 2: 23 requisitos funcionais, 7 histórias, 18 cenários de verify.
**Pronta para `/speckit-plan`.**

**Iteração 3 (2026-09-22, `/speckit-checklist`)** — **16/16 mantido**, e a spec cresceu de 23 para
**28 requisitos** e de 18 para **21 cenários** de verify (o 22º, de sessão ausente, veio depois, no
`/speckit-analyze`). Os dois checklists novos
([ux.md](./ux.md), [regressao.md](./regressao.md)) acharam **três gaps reais** que nem a spec, nem
o clarify, nem o plano tinham visto:

- **evento que termina em outro dia** (34 no espelho, 4 futuros) → FR-002a;
- **ensaio que já aconteceu num show que ainda vem** — janela garantida por construção, porque o
  ensaio cai 2 a 4 dias antes → FR-004a;
- **o verify toca eventos reais do espelho**, não só descartáveis, e a linha de limpeza não mandava
  restaurá-los.

Mais três de forma: ordem dentro do bloco (FR-009c), um nome só para o bloco (FR-009d) e os
não-funcionais de toque e leitura (FR-009e).

**Iteração 4 (2026-09-22, `/speckit-analyze` + refutação contra o código)** — **16/16 mantido**,
22 cenários, 28 requisitos. O `/speckit-analyze` cruzou os artefatos e achou 8 inconsistências
(3 HIGH); uma passada separada, que abria cada arquivo citado para **refutar**, achou outras 13 —
e é a diferença entre as duas que interessa registrar.

**O que só a refutação acharia** (o analyze não abre código; ver [[speckit_analyze_nao_confere_codigo]]):

1. **O "portal Jinja legado" não existe mais.** Quatro artefatos justificavam uma regressão com
   "o Jinja legado tem consultas próprias". `app/talent_portal/routes.py` tem **82 linhas** e serve
   só a foto; as 20 rotas saíram na fase 2. A **conclusão** era certa (só duas funções chamam o
   serializador) e a **razão**, falsa — copiada de uma docstring desatualizada. É o mesmo padrão da
   feature 301: documento velho, obedecido com fidelidade. Virou R14 e três itens de dívida.
2. **O primeiro preenchimento de logística não avisa ninguém.** A spec prometia que mudanças de
   maquiagem e saída "já entram no aviso com o botão Ciente". Entram — mas só quando o valor
   anterior **existia** (`and old_makeup_time is not None`). Como **0 dos 64** eventos futuros têm
   logística, todo preenchimento que esta feature provoca é um primeiro preenchimento, e nenhum
   deles avisa. A promessa foi trocada por uma descrição honesta, e o caso virou dívida.
3. **Três redações para o mesmo valor.** `"Local do evento"` (formulário interno), `"No local do
   evento"` (contrato) e uma terceira na spec. Decidido: as duas primeiras são de contextos
   diferentes e ficam; a terceira foi alinhada.
4. **`portal_auth.py` também não declara RBAC** — eram "os outros três módulos", são quatro, e um
   deles declara de passagem.
5. **`end_at` na ficha de figurino não tinha consumidor**: FR-014 pede nome e data, e a tarefa
   mandava usar um formatador sem hora. A mudança de payload foi **removida** — a ficha não muda no
   servidor.
6. **`noUnusedLocals` não pega o que prometemos que pegaria** na remoção da seção Histórico.
7. Um checkpoint apontava para o cenário **9**, que é um dos que **devem falhar**.
8. SC-002 dizia "10 ensaios futuros com elenco"; a própria spec diz **8** duas vezes.

**O que a refutação conferiu e estava certo**: as cinco citações `arquivo:linha` do `portal_ops.py`,
o backref `lazy=True` do N+1, a ausência de `order_by` em `ensaios`, o `insert_event` no endpoint de
ensaio (o risco de sujar o Google Agenda), o nome exato da flag de permissão do aviso interno, os
tipos de todas as colunas do data-model, e as três superfícies do defeito de rótulo. A aritmética de
`27 − 24 ≠ 7` que a refutação questionou **estava certa**: 4 eventos têm horário sem local, e
20 + 7 = 27.

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`

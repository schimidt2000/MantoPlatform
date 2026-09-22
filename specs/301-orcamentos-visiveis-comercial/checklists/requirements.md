# Specification Quality Checklist: Todo o comercial volta a ver e abrir o orçamento de qualquer colega

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-21
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

**Iteração 1 (2026-09-21)** — 1 item aberto: **FR-011** nasceu com marcador
(vincular/trocar/desvincular em um evento o orçamento de outra pessoa). É escrita, não leitura, e
encosta em valor de venda e comissão (features 267/273) — as duas leituras possíveis levavam a
features de tamanho diferente, e o pedido do dono ("ver e abrir") não decidia.

**Iteração 2 (2026-09-21)** — **todos os itens passam**. O dono respondeu: *vincular sim, trocar
não* — qualquer pessoa do comercial amarra o orçamento de um colega a um evento que ainda não tem
orçamento; trocar ou soltar um já amarrado continua sendo do autor ou do superadmin, e a recusa
passa a nomear quem pode. A decisão foi propagada para **FR-011**, para a **História 3** (três
cenários de aceite, incluindo o caminho feliz do autor), para os **cenários 7 e 8** do
`verify_301.py` (um que passa, um que **deve falhar**), para a linha do
`PATCH /api/events/<id>/orcamento` na tabela de RBAC e para o novo **SC-007**.

**Sobre "No implementation details" e "Written for non-technical stakeholders"** — marcados como
atendidos, com a leitura que o template da Manto impõe:

- O `spec-template.md` adaptado **exige** a seção `### RBAC` com método e rota, e a seção
  `Verificação (verify_NNN.py)` com caminho de arquivo (constituição, Princípios VIII e XIII).
  Endpoint e caminho aparecem **só** nessas duas seções, que são contrato do repositório, não
  vazamento.
- A seção "O pedido" cita commits e datas de propósito: o pedido do dono é *"alguma mudança deve ter
  mudado isso"*, e nomear qual mudança **é** a resposta a ele. Cada afirmação técnica ali vem
  acompanhada da consequência que a pessoa vê na tela.
- As Histórias, os Critérios de Sucesso e FR-001 a FR-011 estão em linguagem de negócio: falam de
  pessoa, tela, ação e recusa — nenhum cita tecnologia, tabela ou framework.

**Itens que passaram e por quê (os que costumam falhar)**

- *Success criteria measurable*: SC-002 ("contagem igual à do superadmin com os mesmos filtros") e
  SC-004 ("hoje aparece em 0% dos casos") são conferíveis sem abrir código.
- *Scope bounded*: a seção "Fora de escopo" nomeia os quatro vizinhos que escapam por engano —
  EducaManto (já aberto), FINANCEIRO (o pedido diz "comercial"), Gastos/Comissões/Dashboard
  (escopam por pessoa **por decisão registrada**, não por regressão) e a paginação do histórico.
- *Dependencies and assumptions*: as Premissas registram as três escolhas que o pedido não fez —
  o que conta como "setor comercial", o que conta como "abrir", e por que **excluir** continua com
  o dono (decisão tomada no mesmo commit `6b191e4` que liberou a visualização).

**Iteração 3 (2026-09-21, `/speckit-clarify`)** — **16/16 → 16/16**, nenhum item mudou de estado.
Três perguntas feitas e respondidas; a spec ficou mais apertada sem abrir nenhuma pendência nova:

1. *A lista abre com quem?* → **com o time inteiro**, sem filtro pré-aplicado (FR-012). Medi o
   espelho antes de perguntar: **1.809 orçamentos, 4 vendedores, 1.631 de uma pessoa só**. O caso
   de borda do teto de 300 passou a carregar esses números, e "filtro 'meus orçamentos' por padrão"
   entrou explicitamente em Fora de escopo para o implement não reintroduzir por conta própria.
2. *Quem re-aplica valores de orçamento alheio?* → **só o autor e o superadmin**. Esta veio de um
   vão encontrado relendo o endpoint: `PATCH /api/events/<id>/orcamento` amarra o vínculo **e**
   aplica valores/`sale_date` na mesma chamada, e a trava de "trocar/soltar" não pegava o caso em
   que o vínculo não muda — dava para reescrever o valor e o mês da comissão de uma venda alheia.
   FR-011 foi reescrito, a tabela de RBAC ganhou a ressalva e o verify ganhou o cenário 9 (deve
   falhar).
3. *Precisa registrar?* → **só o reenvio de e-mail de orçamento alheio** (FR-013), em `AuditLog`,
   sem migration. Abrir e baixar PDF não geram registro.

Duas dúvidas candidatas **morreram na leitura do código**, sem gastar pergunta: o e-mail de
orçamento é institucional (assina "Manto Produções", não o vendedor), então reenviar o de um colega
não falsifica remetente; e o seletor de vendedor não vai poluir, porque só **5 pessoas** têm
COMERCIAL ou SUPERADMIN.

Achado registrado na spec: **a Fatima é COMERCIAL e tem zero orçamentos** — hoje ela abre o
Histórico e vê uma tela vazia. Virou SC-009.

**Iteração 4 (2026-09-21, pós-`/speckit-analyze` + revisão adversarial)** — **16/16 mantido**, mas
com uma correção de **fato**, não de forma:

A spec, o contrato, o quickstart e a T005 afirmavam que, no `DELETE` do histórico, a guarda 409 da
feature 273 vinha **antes** da checagem de dono. O código faz o inverso — em
`app/api/orcamento_write.py` o dono é resolvido em `:115` (404) e `outro_evento_vivo_do_orcamento`
só em `:124`, então quem não é autor leva 404 e nunca chega no 409. Os quatro textos foram
corrigidos para descrever a ordem real, com a instrução explícita de **não reordenar** o endpoint:
antecipar o 409 confirmaria a existência do orçamento e do evento para quem não é autor, contra o
Princípio XIII (404, não 403).

**Por que o `/speckit-analyze` não pegou**: ele cruza os artefatos entre si. As quatro cópias
concordavam, então a coerência era total — e era justamente ela que escondia o erro. Quem achou foi
uma passada que mandava abrir os arquivos citados e **refutar** contra o código.

Outras correções da mesma rodada, todas já aplicadas: a T005 apontava o endpoint de detalhe para o
arquivo errado (mora em `orcamento_read.py`, não no de escrita) e duas das **sete** referências a
`_get_entry_or_none` não tinham tarefa dona (o import de `orcamento_write.py:16` e um comentário em
`agenda_read.py:157-159` que ainda ensina a regra removida); a asserção do cenário 9 nasceria vazia,
porque aplicar é idempotente — o arranjo do cenário passou a ser obrigatório na spec; `aplicar_equipe`
entrou no contrato; e a chave do payload virou `venda.orcamento.autor`, porque `venda.seller` já
existe no mesmo bloco e é o vendedor **do evento**, outra pessoa.

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`

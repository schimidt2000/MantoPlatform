# Pesquisa (Phase 0) — Feature 301

**Spec**: [spec.md](./spec.md) · **Data**: 2026-09-21

Nenhum `NEEDS CLARIFICATION` entrou nesta fase: a spec saiu do `/speckit-clarify` com os três
pontos abertos fechados. A pesquisa aqui é de **código** — onde a trava mora, quem mais depende
dela, e o que já existe para reusar (Princípio I).

---

## R1 — A checagem de dono tem um ponto único de leitura e um de lista

**Decisão**: matar a trava em **dois** lugares no módulo de Orçamento, não em cinco.

- `app/api/orcamento_read.py:219` — `_get_entry_or_none(entry_id, is_sa)` é o funil de **quatro**
  endpoints: detalhe (`orcamento_read.py:236` — mora no módulo de LEITURA, não no de escrita), PDF,
  enviar-e-mail e DELETE (`orcamento_write.py:66`, `:88`, `:115`). Mudar a função resolve os quatro
  de uma vez — mas são **7** referências ao nome no total: somam-se o **import** de
  `orcamento_write.py:16` (sem o qual o módulo cai logo no import) e um **comentário** em
  `agenda_read.py:157-159`, que ainda ensina a regra que esta feature remove.
- `app/api/orcamento_read.py:150` — `if not is_sa: query = query.filter_by(user_id=...)` é a trava
  da listagem.

**Consequência que exige cuidado**: o `DELETE` **continua** com a trava (FR-006). Então
`_get_entry_or_none` não pode simplesmente perder o parâmetro — ficariam os três endpoints de
leitura certos e o DELETE errado. A função se divide em duas, com nomes que dizem a regra:
`_get_entry(entry_id)` (só existência, para leitura) e `_get_entry_para_excluir(entry_id, is_sa)`
(existência + dono). Nome que declara a intenção é o que a constituição cobra em §XIII ("ler o nome
do gate não basta") e é o que teria evitado esta regressão.

**Alternativas rejeitadas**:
- *Manter uma função com flag `checar_dono: bool`* — é o desenho atual em outra roupa; o próximo
  que ler `_get_entry_or_none(id, is_sa)` numa chamada de PDF continua sem saber se ali cabe dono.
- *Filtrar no `_ops`* — `quote_ops` é puro e não conhece `current_user`; RBAC é da view (Princípio III).

---

## R2 — A trava do vínculo deve olhar o orçamento **já vinculado**, não o alvo

**Decisão**: em `PATCH /api/events/<id>/orcamento`, o 404-por-dono sobre o orçamento **alvo**
(`agenda_write.py:1185`) **cai inteiro**; a única checagem de dono que sobra é sobre o orçamento
**atualmente vinculado** (`agenda_write.py:1207`), e ela passa a cobrir os três verbos: trocar,
desvincular e re-aplicar.

Regra final, em uma frase: **quem manda é o autor do orçamento que já está no evento.**

| Estado do evento | Ação | Depois |
|---|---|---|
| sem orçamento vinculado | vincular qualquer orçamento | **permitido** a COMERCIAL e SUPERADMIN — FINANCEIRO passa no gate, mas segue no 404 |
| vinculado a orçamento **meu** | trocar / soltar / re-aplicar | permitido (inalterado) |
| vinculado a orçamento **de outro** | trocar / soltar / **re-aplicar** | **409**, nomeando o autor |

**Por que o alvo não precisa mais de checagem**: com FR-001 a pessoa **vê** o orçamento; negar o
vínculo com "não encontrado" passaria a ser mentira sobre algo visível na tela (FR-010).

**O vão que esta decisão fecha**: hoje o caso `raw == atual_id` (re-aplicar sem trocar o vínculo)
nunca chega na guarda de 409 — ele só não passa porque o 404 do alvo vem antes. Ao derrubar o 404,
re-aplicar ficaria **aberto** e reescreveria `sale_value` e `sale_date` de uma venda alheia — e
`sale_date` decide o mês da comissão (hotfix 267b). Por isso a guarda tem de ser reescrita, não só
relaxada. É o único ponto desta feature onde "tirar uma trava" exige **apertar** outra.

**Alternativas rejeitadas**:
- *Travar pelo alvo em vez do atual* — bloquearia B de vincular o orçamento de A, que é justamente
  o que o dono liberou.
- *Deixar re-aplicar aberto* — foi apresentado ao dono como opção B e recusado.

---

## R3 — O frontend não pode continuar deduzindo RBAC do silêncio do payload

**Decisão**: o servidor passa a mandar **flags explícitas**; o React para de inferir.

Dois lugares inferem hoje, e os dois quebram com esta feature:

1. `ComercialSection.tsx:580` — `orcamentoDeOutro = !orc && venda.tem_orcamento`, ou seja "o
   payload não me deu o orçamento, logo é de outro". Depois de FR-009 o payload **sempre** dá o
   orçamento para o comercial, então essa variável vira `false` para sempre — e o aviso "só ele ou
   o superadmin podem trocar" **sumiria exatamente quando o servidor passa a recusar**. O usuário
   veria os botões, clicaria e levaria erro.
   → o payload de `GET /api/events/<id>` ganha `venda.orcamento.pode_gerir` (bool) e
   `venda.orcamento.autor` (nome). O `pode_gerir` nasce **na view** (é RBAC); o `autor` vem do
   `_ops` (R7). A chave **não** se chama `vendedor`: `venda.seller` já existe no mesmo bloco e é
   o vendedor **do evento**, outra pessoa.
2. `OrcamentoHistoricoPage.tsx:299` — "Excluir" é renderizado em **toda** linha. Com a lista
   compartilhada ele apareceria sobre orçamento alheio e só falharia depois do `window.confirm()`.
   → cada linha de `GET /api/orcamento/historico` ganha `pode_excluir` (bool).

**Por que flag e não comparar ids no cliente**: Princípio XIII é explícito — *"o frontend nunca
decide RBAC: ou o payload traz a chave ou traz `flags.*`"*. Comparar `entry.user_id === me.id` no
React exigiria expor o id do usuário logado e duplicaria a regra em dois lugares, que é como ela
diverge.

**Alternativas rejeitadas**:
- *Desabilitar o botão em vez de escondê-lo* — mostra ao usuário uma ação que nunca será dele; o
  aviso já está no bloco do evento, onde a pessoa realmente precisa agir.
- *Manter `is_superadmin` como proxy* — é o campo que carregou a regressão de tela; some daqui
  (ver R5).

---

## R4 — Auditoria: reusar `app/utils.py:audit()`, e **commitar**

**Decisão**: FR-013 usa `audit(action, entity_type, entity_id, entity_name, detail)` de
`app/utils.py:46`, com `entity_type="orcamento"`. Nada de model, helper ou migration novos —
`AuditLog` já tem ator, papel, tipo, id, nome e detalhe livre.

**A armadilha, nomeada**: o docstring de `audit()` diz que **não persiste sozinha** — o chamador
commita. E `api_orcamento_historico_enviar_email` hoje **não commita nada**: é um endpoint de
leitura + envio. Sem um `db.session.commit()` explícito, a linha de auditoria nasce e morre no fim
da requisição, e o verify passaria na mesma sessão sem ver o defeito. É o mesmo defeito do
**hotfix 257** (anexos do evento sumiam: POST sem commit), e é por isso que o cenário 5 do
`verify_301.py` confere a linha **por conexão separada** (Princípio VIII).

**Ordem importa**: gravar a auditoria **depois** do envio dar certo. Registrar um e-mail que falhou
seria pior que não registrar.

**Alternativas rejeitadas**:
- *`EventLog`* — é preso a evento; orçamento do histórico pode não ter evento.
- *Registrar também abrir e baixar* — recusado pelo dono; o histórico é tela de uso diário e o log
  cresceria sem responder pergunta nenhuma.

---

## R5 — `is_superadmin` sai do payload do histórico

**Decisão**: remover a chave `is_superadmin` de `GET /api/orcamento/historico` e do tipo
`OrcamentoHistoricoResponse`, e sempre popular `users`.

Ela existe só para três `if` no React — o seletor de vendedor (`:174`) e a coluna "Vendedor"
(`:232`, `:257`) — e os três passam a ser incondicionais (FR-004, FR-005). Deixar a chave viva,
sem uso, é deixar no lugar a exata alavanca que espalhou esta regressão: o próximo a mexer na tela
acha um `is_superadmin` no payload e conclui que há algo a esconder.

**Confirmado por varredura**: o endpoint `/api/orcamento/historico` tem **três** consumidores —
`OrcamentoHistoricoPage.tsx` (via `useOrcamentoHistorico`), `OrcamentoPicker.tsx:29` e
`OrcamentoCalculadoraPage.tsx:120` (selo de contagem no link do histórico). Da **chave**
`is_superadmin`, porém, o leitor é **um só**: a página do histórico. Remoção segura (Princípio IV),
e o `npm run typecheck` é a segunda prova, porque a chave sai do tipo `OrcamentoHistoricoResponse`.
O terceiro consumidor tem consequência própria, aceita e registrada nos Casos de borda da spec: o
selo passa a contar o time e satura em 300.

**Alternativa rejeitada**: *manter a chave e só parar de ramificar* — menos diff, mais dívida.

---

## R6 — A busca de orçamento do evento é consertada de graça (e precisa mostrar o vendedor)

**Achado**: `OrcamentoPicker.tsx` — a busca que a aba Comercial usa para escolher o orçamento a
vincular — chama `GET /api/orcamento/historico?q=`. Ou seja, **é o mesmo endpoint da lista**. Hoje
um comercial só encontra ali os próprios orçamentos, e é por isso que FR-011 ("vincular o orçamento
de um colega") está bloqueado já na tela, antes de chegar no 404 do servidor.

**Decisão**: FR-001 conserta o picker sem código próprio. Mas duas coisas precisam ir junto:

1. a linha do resultado passa a mostrar **o vendedor** — escolher o orçamento de um colega sem
   saber que é de um colega é como a pessoa vai vincular errado;
2. o docstring do componente (linhas 12-15) afirma hoje *"já respeita o dono: comercial só vê os
   próprios, superadmin vê todos"*. Essa frase vira **mentira** com esta feature. Corrigir não é
   capricho: foi um texto desatualizado descrevendo a regra errada
   (`specs/177-.../contracts/api-endpoints.md:119`) que trouxe a restrição de volta em julho.

---

## R7 — `resumo_do_orcamento` precisa do nome do vendedor

**Decisão**: `app/calendar/orcamento_evento_ops.py:70` passa a incluir `autor` (nome de quem fez o orçamento)
no resumo. É dado **do orçamento**, então cabe no `_ops` puro. O `pode_gerir` de R3, esse sim é
RBAC e fica na view (`agenda_read.py`), nunca no `_ops` (Princípio III).

Sem o nome, a recusa de FR-011 não consegue cumprir FR-010 ("dizer quem pode agir") — a mensagem
ficaria em "outro vendedor", que é o que a tela já diz hoje e não ajuda ninguém a resolver.

---

## R8 — O teto de 300 fica, e a pesquisa diz o preço

**Decisão**: nada de paginação (decidido no `/speckit-clarify`). Registrado aqui o número medido no
espelho (dump de 27/08/2026), que é o que torna a decisão informada e não distraída:

| | |
|---|---|
| Orçamentos no histórico | **1.809** |
| Vendedores com orçamento | 4 |
| Concentração | **1.631 (90%) de uma pessoa só** |
| Criados nos últimos 3 meses | 884 |
| Pessoas com papel COMERCIAL | 3 (uma delas com **zero** orçamentos) |

**Efeito aceito**: a primeira tela fica dominada por um vendedor; os filtros viram o caminho normal.
**Efeito bom, que sozinho já paga a feature**: a pessoa do comercial com zero orçamentos hoje abre
uma tela vazia e passa a ver o histórico da empresa (SC-009).

**Alternativa rejeitada**: *abrir filtrada em "meus orçamentos"* — recusada pelo dono; a spec
registra a recusa em "Fora de escopo" para o `/speckit-implement` não reintroduzir por conta própria.

---

## R9 — O e-mail é institucional (dúvida que morreu na leitura)

`app/email_service.py:665` — `send_quote_email(to, client_name, pdf_bytes)` assina **"Manto
Produções"** com o telefone da empresa e pede resposta no próprio e-mail. Não há nome, assinatura
nem contato do vendedor.

**Consequência**: reenviar o orçamento de um colega **não** falsifica remetente e não confunde o
cliente. FR-003 libera sem ressalva; FR-013 registra o fato por rastreabilidade, não para corrigir
autoria. Nada a implementar — anotado para que a revisão não levante isso como risco.

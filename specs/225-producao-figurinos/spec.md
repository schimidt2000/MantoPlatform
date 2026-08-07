# 225 — Produção de Figurinos

## Problema

Figurino é **70% de todo o gasto extra da Manto** — R$ 47.969,81 de R$ 68.149,66 no banco de
produção, em 40 lançamentos. E é a única parte da operação que não tem lugar no sistema.

O que existe hoje é um **catálogo**: `FigurinoSheet` (616 fichas) descreve o figurino pronto de um
personagem — foto, lista de peças em JSON, observações. Serve para separar e imprimir. Não serve
para produzir: a peça é uma string dentro de um JSON, sem identidade, sem responsável, sem prazo,
sem custo e sem estado.

O trabalho de produzir, então, não mora em lugar nenhum. Ele aparece só depois, espalhado em
lançamentos soltos de Gasto Extra. Exemplo real do evento das Cartas (Alice, Cuiabá):

| Lançamento | Valor |
|---|---|
| FITAS DE GORGURÃO ( corpetes das cartas ) | R$ 82,20 |
| Pedraria ALICE NO PAÍS DAS MARAVILHAS | R$ 59,10 |
| AVIAMENTOS RAINHA DE COPAS | R$ 55,00 |
| Sapato Vermelho MENINAS CARTAS | R$ 64,99 |
| BOTA Chapeleiro MALUCO | R$ 179,99 |
| Pedrarias VERMELHAS | R$ 413,13 |
| Lentes de contato | R$ 100,00 |
| FIGURINOS CARTAS ALICE (CUIABÁ) PARTE FINAL | R$ 4.800,00 |

Oito linhas que são **um trabalho só**. Ninguém consegue responder, a partir do sistema, "quanto
custou o figurino das Cartas", "quem estava fazendo", "ficou pronto a tempo" ou "o que ainda falta
produzir para o evento do dia 11/11".

## Resultado pretendido

Um pedido de produção com identidade própria, que junta num lugar só: o que precisa ser feito,
para qual evento, quem é o responsável, até quando, quanto se esperava gastar, quanto se gastou de
verdade, as fotos da evolução, os orçamentos dos fornecedores e o histórico do que aconteceu.

E que **cobre a pessoa responsável**: convite na agenda dela e destaque na tela inicial.

## Não faz parte

- Reescrever `FigurinoSheet`. O catálogo continua o que é; o pedido **aponta** para a ficha.
- Controle de estoque de tecido/aviamento.
- Ordem de compra ou pagamento a fornecedor: quem paga continua sendo Gasto Extra, com a
  aprovação e a planilha de pagamentos que já existem.

## Decisões tomadas com o cliente (07/08/2026)

1. **Convite de verdade no Google.** A pessoa responsável recebe o compromisso na agenda dela.
2. **Qualquer pessoa da equipe abre o pedido.** Figurino e Superadmin executam e movem o status.
3. **Fluxo com aprovação:** `solicitado → aprovado → em_producao → pronto`.

## Requisitos

### Pedido

- **FR-001** Um pedido tem título obrigatório e descrição livre do que precisa ser feito.
- **FR-002** O vínculo com evento é **opcional**. Cinco dos 40 gastos de figurino de hoje não têm
  evento ("Mascotes Copa 4/4", "SAPATO GABBY HUMANA") — é produção de acervo, não de show.
- **FR-003** O vínculo com uma ficha de figurino (`FigurinoSheet`) é opcional e serve para dizer de
  qual personagem é a peça.
- **FR-004** Prazo (`due_date`) é opcional; quando o pedido tem evento e não tem prazo, o prazo
  assumido é a data do evento.
- **FR-005** Custo previsto é opcional e serve para comparar com o gasto real.
- **FR-006** Excluir o evento **não** apaga o pedido: o trabalho existiu e o dinheiro saiu. O
  vínculo vira nulo (mesma regra do Gasto Extra na feature 224).

### Fluxo

- **FR-010** Estados: `solicitado`, `aprovado`, `em_producao`, `pronto`, mais `cancelado` como
  saída (um pedido pode ser recusado ou desistido — aprovação sem recusa não é aprovação).
- **FR-011** Só SUPERADMIN aprova. Figurino e Superadmin movem de `aprovado` em diante.
- **FR-012** Qualquer papel interno (menos REVENDEDOR_EDUCAMANTO) abre um pedido.
- **FR-013** Toda mudança de estado grava uma linha no histórico com autor, papel e data.
- **FR-014** Cancelar exige motivo.

### Responsável e agenda

- **FR-020** O pedido tem um responsável (usuário interno), definido na aprovação ou depois.
- **FR-021** Ao ser designada, a pessoa recebe e-mail.
- **FR-022** Ao ser designada, e havendo prazo, o sistema cria um compromisso no Google Agenda
  **com a pessoa como convidada**, para o prazo entrar na agenda pessoal dela.
- **FR-023** Esse compromisso é marcado com `extendedProperties.private.manto_kind =
  "figurino_producao"` e **a sincronização de agenda o ignora**. Sem isso ele viraria um evento
  fantasma na plataforma — `sync_events` importa tudo que encontra no calendário.
- **FR-024** Trocar de responsável troca o convidado; mudar o prazo move o compromisso; concluir
  ou cancelar o pedido remove o compromisso.
- **FR-025** Falha do Google **nunca** impede a operação: o pedido é salvo, e o aviso volta como
  `warning` no payload (mesma política de `event_ops.update_event_core`).

### Dinheiro

- **FR-030** Um Gasto Extra pode apontar para um pedido de produção (`figurino_producao_id`).
- **FR-031** O pedido mostra o total gasto (só gastos **aprovados**, para bater com a DRE), a
  contagem de lançamentos e a diferença contra o custo previsto.
- **FR-032** Dá para vincular gasto **já existente** — os 40 lançamentos de hoje precisam poder ser
  organizados sem serem recriados.
- **FR-033** Criar um gasto a partir do pedido já vem com categoria "Figurino" e o evento do
  pedido preenchidos.

### Anexos

- **FR-040** N fotos por pedido (evolução do trabalho).
- **FR-041** N orçamentos por pedido, cada um com fornecedor e valor, para comparar propostas.
  Orçamento aceita PDF além de imagem.
- **FR-042** Uma linha do histórico pode carregar uma foto — é o "mini histórico de evolução".

### Destaque na tela inicial

- **FR-050** Quem é responsável por pedido em aberto vê um painel próprio na home, com os pedidos
  ordenados por prazo.
- **FR-051** Pedido vencido ou vencendo em ≤2 dias aparece em vermelho, como as tarefas urgentes
  de casting já fazem (`SectorPanel.getUrgency`).
- **FR-052** Este é o **primeiro painel pessoal** da home — todos os outros são por papel. O gate é
  `responsible_id == user.id`, e SUPERADMIN "vendo como FIGURINO" continua vendo os próprios
  pedidos, não os de outra pessoa.

## 225b — Manutenção de figurino

Extensão pedida depois da primeira entrega: boa parte do trabalho da oficina não é produzir peça
nova, é **mexer no que já existe**. O caso relatado: "recebemos um feedback do evento e a pessoa
falou que dentro do boneco tem uma peça solta". Hoje isso se combina por voz e some. E o segundo
caso: "para esse evento nesse dia, fazer esse reparo específico" — trabalho manual, **sem compra
nenhuma**, que também precisa ficar escrito.

- **FR-060** O pedido ganha um tipo: `producao` (peça nova) ou `manutencao` (conserto, ajuste,
  adaptação do que já existe).
- **FR-061** Manutenção **não passa por aprovação**: `solicitado → em_producao → pronto`. Exigir
  um super admin para liberar uma costura mataria o registro, que é o que se quer ganhar. As
  transições válidas saem de `FIGURINO_PROD_FLUXOS` e o servidor manda para a tela.
- **FR-062** Manutenção exige **ficha de figurino** (é sempre sobre uma peça que existe) e
  **gravidade**: `impede_uso` ou `pode_esperar`.
- **FR-063** A gravidade é a única informação que muda uma decisão: a peça pode ir para o próximo
  evento assim como está, ou não pode?
- **FR-064** Com `impede_uso` aberto, o aviso aparece **na ficha** (lista de Figurinos, sobre a
  foto) e **no elenco do evento** — onde alguém está prestes a separar aquele boneco. Ali o
  bloqueio vence o "Separado": marcar como separado uma peça que não pode ir seria exatamente o
  erro que o aviso existe para impedir.
- **FR-065** Resolver a manutenção apaga o aviso. Alerta que não some vira ruído e deixa de ser
  lido.
- **FR-066** Pedido aberto **sem responsável** avisa o setor de figurino por e-mail e entra num
  painel próprio da home ("Oficina — sem responsável"). Manutenção quase sempre nasce órfã: quem
  relata o defeito recebeu o feedback do evento e não é quem vai consertar.
- **FR-067** Na manutenção, quantidade some do formulário e o painel de dinheiro só aparece se
  houver custo previsto ou gasto lançado — a maior parte é trabalho manual, e um "R$ 0,00" grande
  sugeriria que falta lançar alguma coisa.

## Verificação

`scripts/db/verify_producao_figurinos.py`, contra `manto_local`:

1. ciclo completo solicitado → aprovado → em_producao → pronto, com histórico gravado a cada passo;
2. RBAC: quem não é Superadmin não aprova; Revendedor não abre pedido;
3. gasto vinculado entra no total só depois de aprovado;
4. excluir o evento mantém o pedido e zera o vínculo;
5. o compromisso do Google é ignorado por `sync_events` (não vira evento fantasma);
6. home devolve o painel pessoal só para o responsável, com urgência correta;
7. anexo de foto e de orçamento sobem, listam e somem ao apagar.

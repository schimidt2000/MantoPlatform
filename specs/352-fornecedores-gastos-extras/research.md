# Pesquisa — 352 Fornecedores cadastrados nos gastos extras

Nenhum NEEDS CLARIFICATION ficou no contexto técnico; as decisões abaixo saem da leitura do código e
dos dados de produção (leitura, 17/11).

## R1. Onde o fornecedor está hoje

- **Decisão**: o cadastro é tabela própria ligada a `special_expenses` por FK opcional; o gasto
  continua guardando `supplier_name`/`supplier_pix`.
- **Por quê**: `payee_name`/`payee_pix` (`app/models.py`, `SpecialExpense`) alimentam a Planilha de
  Pagamentos, a DRE, o auditor financeiro e a skill `financeiro`; trocar a fonte do nome para a tabela
  nova obrigaria a mexer em todos. E o PIX do gasto é o PIX para o qual se pagou — histórico, não
  referência.
- **Alternativas**: (a) só autocompletar sobre `DISTINCT supplier_name` — sem PIX confiável, sem
  arrumar grafias, sem "quanto pagamos ao X"; rejeitada. (b) tirar `supplier_*` do gasto e ler do
  cadastro — quebra o histórico do PIX e todos os leitores; rejeitada.

## R2. Dados de produção (17/11, somente leitura)

246 gastos; 83 com desembolso `fornecedor`, 65 grafias distintas; 2 devoluções (`cliente`). Agrupando
por chave PIX normalizada ou nome normalizado saem 41 grupos, e todos os grupos com mais de uma
grafia foram conferidos à mão (descrições dos gastos lidas): "Aluguel Sonic e knuckles" tem o CNPJ
da Real Produções e a descrição "Aluguel figurino Sonic" — o nome digitado era a descrição; "Meta"
(fornecedor de figurino, não a Meta dos anúncios) tem o mesmo CNPJ de "Sheila/david". Nenhum grupo
por PIX junta fornecedores diferentes.

## R3. Normalização do nome

- **Decisão**: sem acento, minúsculas, todo trecho não alfanumérico vira um espaço.
- **Por quê**: as grafias de produção diferem por acento (ADAO/ADÃO), caixa, espaço em volta de "/"
  ("Ramon / Real" × "Ramon/real") e parênteses ("Karen (madu)"). Só acento e caixa
  (`strip_accents_lower`, feature 114) não juntaria "Ramon / Real" com "Ramon/real".
- **Alternativa**: semelhança aproximada (distância de edição) para juntar "Peterson" com "Peterson
  Caminhão" — falsos positivos entre pessoas diferentes ("Talita" × "Talita Stefani"); a junção por
  semelhança fica com o Financeiro, na tela (juntar).

## R4. Corrida no cadastro automático

- **Decisão**: `UNIQUE(nome_normalizado)` + `SAVEPOINT` (`db.session.begin_nested()`); no
  `IntegrityError`, desfaz o savepoint e relê pelo nome.
- **Por quê**: o padrão da casa é idempotência por restrição de banco (`docs/00` §6.10); o
  savepoint preserva o gasto que está sendo criado na mesma transação.

## R5. Busca das sugestões

- **Decisão**: `GET /api/gastos/fornecedores` uma vez; filtro local do `Combobox` (já ignora acento).
- **Por quê**: dezenas de fornecedores; o `CLAUDE.md` registra que requisição por tecla é o que
  sangra primeiro no deploy do backend. O `Combobox` filtra local quando não recebe `onQueryChange`.

## R6. Modo texto livre do `Combobox`

`freeSolo` (`packages/ui/src/components/combobox.tsx`): digitar chama `onChange(texto, null)`;
escolher chama `onChange(option.label, option)`. É exatamente "escolher preenche, digitar cadastra":
`option === null` zera o `fornecedorId`.

## R7. Juntar sem deadlock

Duas linhas de `fornecedores` travadas `FOR UPDATE ... ORDER BY id` (`docs/00` §6.25); depois o
`UPDATE` dos gastos. Ninguém mais trava fornecedor → gasto em ordem inversa (o gasto novo só lê o
fornecedor; o cadastro automático insere, não trava).

## R8. Banco de verificação

`manto_352` restaurado do dump `backups/manto_2026-11-17_0200.dump` (head `d334b2c4e6f8`, 83 gastos a
fornecedor). O `manto_local` é compartilhado com as sessões 348–351 (o `manto_348` é delas) — ver a
tabela de complexidade do `plan.md`.

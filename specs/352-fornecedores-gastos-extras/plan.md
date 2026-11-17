<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Fornecedores cadastrados nos gastos extras

**Branch**: `352-fornecedores-gastos-extras` | **Data**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/352-fornecedores-gastos-extras/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

> **Número**: a feature nasceu como 348 e foi renumerada para **352** no mesmo dia: o alocador não
> viu as branches `348-origem-completa`, `349`, `350` e `351` de outra sessão (worktrees em
> `.claude/worktrees/`). Nenhum artefato dessas sessões foi tocado (inclusive o banco `manto_348`).

## Resumo

Cadastro `fornecedores` ligado aos gastos extras por `special_expenses.fornecedor_id`. O núcleo
novo `app/gastos/fornecedor_ops.py` resolve o fornecedor de todo gasto a fornecedor salvo pelo
núcleo existente (`gastos_ops.create_expense`/`edit_expense`): pelo id escolhido, senão pelo nome
normalizado, senão cadastra — e completa PIX e categoria que faltam, sem substituir. A tela do gasto
troca o `<input>` do nome pelo `Combobox` de `@manto/ui` em modo texto livre (`freeSolo`), filtrando
localmente a lista de fornecedores ativos. Financeiro e Superadmin ganham a página
`/gastos/fornecedores` (cadastrar, alterar, arquivar, juntar). A migration cria a tabela, a coluna e
importa o histórico por união de grupos (mesma chave PIX normalizada **ou** mesmo nome normalizado),
com o nome arrumado da tabela abaixo.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`
(`apiFetch`/`assetUrl`), `@manto/money`

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`); verificação contra
`manto_352` (ver Rastreamento de complexidade). Nenhum arquivo novo em disco.

**Verificação**: `specs/352-fornecedores-gastos-extras/verify_352.py` contra `manto_352` (login só
pela API; escrita por conexão separada); `cd frontend && npm run typecheck`; tela aberta no Browser
pane em 390px e desktop

**Plataforma-alvo**: web — Render; app interno usado no celular como app instalado

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: as sugestões filtram no navegador, sem requisição por tecla (a lista de
fornecedores ativos é de dezenas; `GET` uma vez por abertura da tela, `staleTime` 5 min). O `GET`
do Financeiro soma gastos por fornecedor numa consulta agregada só, não N+1.

**Restrições**: campo novo do payload opcional no React (`docs/00` §6.21); chave PIX e documento
nunca no repositório (só nomes na tabela de grafias); a migration não importa código de `app/`.

**Escala/escopo**: 1 tabela nova (`fornecedores`), 1 coluna nova (`special_expenses.fornecedor_id`),
4 endpoints novos, 2 endpoints alterados (aceitam `fornecedor_id`), 1 tela nova, 1 campo trocado no
formulário de gasto, 1 item de menu.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | `Combobox` (`@manto/ui`, modo `freeSolo` + filtro local sem acento), `Modal`, `ConfirmDialog`, `KebabMenu`, `PageHeader`; `gastos_ops.is_financeiro` como gate; `gastos_ops._log` para a auditoria; `strip_accents_lower` (`app/utils.py`) dentro da normalização; endpoints nos módulos `gastos_read`/`gastos_write` existentes (sem módulo novo a registrar) |
| II. Padrões de código | type hints/docstrings; `ruff format` só em `fornecedor_ops.py` e na migration (novos); `ruff check` nos tocados; TS estrito, sem `any` |
| III. Camadas / API First | regra em `fornecedor_ops.py` (puro, sem `flask.request`); views só gate + chamada + serialização; nenhuma rota fora de `/api` |
| IV. Não quebrar o que funciona | aditiva: coluna nula, `supplier_name`/`supplier_pix` continuam a fonte da Planilha de Pagamentos, DRE e auditor financeiro; devolução (`cliente`) e reembolso intocados; contrato de `POST/PATCH /api/gastos` só ganha campo opcional |
| V. UI/UX com feedback | TanStack Query; `Button loading`; erro no campo (`fields.nome`, `fields.destino_id`); dados digitados preservados; juntar pede confirmação explícita no diálogo |
| VI. Esteira (Nível 1) | esteira completa; artefatos em `specs/352-…/` |
| VII. Living Spec | spec escrita antes; mudança de comportamento volta à spec primeiro |
| VIII. Verify antes do núcleo | `verify_352.py` na fase Foundational, antes de `fornecedor_ops.py` |
| IX. Dinheiro BRL | total aprovado por fornecedor exibido com `formatBRL`; `Numeric` no banco, `float` no JSON como o resto de `gastos_read` |
| X. Mobile-first público | não toca superfície pública; a tela interna nasce em 390px (preferência do dono) |
| XI. Framer Motion | `Modal` e `Combobox` já animam com `useReducedMotion`; lista nova sem animação própria |
| XII. Combobox / Maps | o nome do fornecedor (dezenas de itens) é `Combobox`; o destino do "Juntar" também; a categoria (5 itens) segue `<select>` |
| XIII. RBAC declarado | `GET` qualquer logado (escopo reduzido para não gestores); `POST`/`PATCH`/`juntar` Financeiro+Superadmin; linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | sem env nova; nada escreve fora (o e-mail de gasto novo já existente segue igual) |
| XV. Texto por superfície | app interno, operacional; "Fornecedores", "Novo fornecedor", "Juntar com outro fornecedor", "Arquivar", "Reativar", estado vazio "Nenhum fornecedor encontrado."; erros "Já existe um fornecedor com este nome." — nenhuma string da API comparada no frontend |
| Stack | migration à mão `f352a1b2c3d4` (`down_revision = d334b2c4e6f8`); sem Jinja novo; sem segredo |
| Operação e Deploy | toca só `manto-backend` + `manto-frontend`; não toca `startCommand`; a migration reescreve `supplier_name` dos gastos ligados → ensaio em banco descartável com dump fresco (`manto_352`, dump de 17/11 02h00) rodando `flask db upgrade && python seed.py` |

**Resultado**: aprovado, com uma exceção registrada (banco de verificação).

## Decisões de desenho

### 1. Nome normalizado (a regra de "mesmo fornecedor")

`normalizar_nome(texto) = re.sub(r"[^a-z0-9]+", " ", strip_accents_lower(texto)).strip()` —
sem acento, minúsculas, toda pontuação e espaço viram um espaço: "Ramon / Real Produções" e
"Ramon/real produções" dão `ramon real producoes`. Guardado em `fornecedores.nome_normalizado`
com `UNIQUE` (constituição: idempotência por restrição de banco). A migration tem uma cópia da
função (migration não importa `app/`); o cenário 1 do verify confere que todo
`nome_normalizado` gravado é igual a `fornecedor_ops.normalizar_nome(nome)`.

### 2. Chave PIX normalizada (só para juntar o histórico)

Vazia ou "-" → nenhuma. Com letra (e-mail, chave aleatória) → minúsculas sem espaço. Sem letra
(CPF, CNPJ, telefone) → só os dígitos. Não é coluna: só a importação usa.

### 3. Resolver o fornecedor de um gasto (`fornecedor_ops.resolver_para_gasto`)

Chamado por `create_expense` e `edit_expense` só quando o desembolso é `fornecedor`:

1. `fornecedor_id` válido → esse fornecedor;
2. senão, o de mesmo `nome_normalizado` (ativo ou arquivado — arquivado continua arquivado);
3. senão, cadastra (nome digitado com espaços colapsados, PIX e categoria do gasto se for
   escolhível) num `SAVEPOINT`; `IntegrityError` (outra pessoa cadastrou no mesmo instante) →
   desfaz o savepoint e relê pelo nome.

Depois: completa `pix`/`categoria_padrao` vazios com os do gasto; o gasto grava
`supplier_name = fornecedor.nome` (a grafia do cadastro) e o `supplier_pix` digitado. Desembolso
que não é `fornecedor` → `fornecedor_id = None`.

### 4. Renomear e juntar reescrevem só o nome dos gastos

`alterar` com nome novo: `UPDATE special_expenses SET supplier_name = :nome WHERE fornecedor_id = :id`.
`juntar(origem, destino)`: trava os dois por `ORDER BY id` (`docs/00` §6.25), move os gastos com o
nome do destino, completa PIX/categoria do destino com os da origem, apaga a origem, registra na
auditoria. `supplier_pix` dos gastos nunca muda (FR-007). Nenhum dos dois acende
`approved_with_edits` — não é edição do gasto.

### 5. Categorias escolhíveis

`fornecedor_ops.CATEGORIAS_DO_FORNECEDOR` = `SpecialExpense.CATEGORIES` menos "Devolução a cliente"
e "Multa de cancelamento" (nascem só pelo cancelamento). Vai no `GET` como `categorias`.

### 6. Tela

- **Formulário de gasto** (`GastosExtrasPage`): `FornecedorCampo` (novo, em
  `components/Gastos/`) envolve o `Combobox freeSolo` com as opções ativas (rótulo = nome,
  segunda linha = PIX · categoria). Digitar limpa `fornecedorId`; escolher preenche nome, PIX,
  `fornecedorId` e a categoria padrão. Texto que não casa com nenhum nome normalizado mostra
  "Fornecedor novo: ficará salvo para os próximos gastos." O cabeçalho da página ganha o botão
  "Fornecedores" para quem gerencia.
- **Página `/gastos/fornecedores`** (`FornecedoresPage`): busca e "Mostrar arquivados" no endereço
  (`useSearchParams`, `replace` — `docs/00` §5 "Lista e arquivo"), `useRestaurarRolagem`; um cartão
  por fornecedor com nome, PIX (`CopyButton`), categoria, "N gastos · R$ X aprovados · último em
  dd/mm/aaaa", selo "Arquivado"; `KebabMenu` com Alterar, Juntar com outro fornecedor, Arquivar /
  Reativar. Diálogos: cadastro/alteração (`Modal`) e juntar (`Modal` com `Combobox` do destino, a
  frase do efeito com os números e o botão destrutivo).
- **Menu**: item "Fornecedores" no grupo do Financeiro, depois de "Gastos Recorrentes",
  `isVisible` Financeiro/Superadmin.

### 7. Importação (migration `f352a1b2c3d4`)

União de grupos sobre os gastos `disbursement_type = 'fornecedor'` (devolução `cliente` fica fora):
gastos com a mesma chave PIX normalizada ou o mesmo nome normalizado caem no mesmo grupo (union-find
em Python sobre `op.get_bind()`). Por grupo: nome = o da tabela abaixo se alguma grafia do grupo
estiver nela; senão a grafia mais usada (empate: a do gasto mais recente); PIX = o do gasto mais
recente que tem PIX; categoria = a mais usada entre as escolhíveis (empate: a mais recente). Nome
normalizado já usado por outro grupo → sufixo " (2)" (defensivo; não acontece com os dados de 17/11).
Liga os gastos e grava neles o nome do grupo.

**Grafias arrumadas** (decididas sobre os 83 gastos de produção em 17/11; a chave é o nome
normalizado de uma das grafias do grupo; só nomes, nenhum PIX):

| Grafias em produção | Nome no cadastro |
|---|---|
| ADAO · ADÃO · ADÃO LIMA da SILVA · ADÃO LIMA DA SILVA | Adão Lima da Silva |
| Aluguel Sonic e knuckles · Ramon / Real Produções · Ramon/real produções · Real produções / Ramon Rossi | Real Produções (Ramon Rossi) |
| Andressa Carvalho Lages do Vale · ANDRESSA CARVALHO LAGES DO VALE | Andressa Carvalho Lages do Vale |
| Beatriz Hornink Boneti · Bia Hornink | Beatriz Hornink Boneti |
| Castelo das iludidos- Sara · Sara Castelo | Sara Castelo (Castelo das Iludidos) |
| Diego Motta · Studio de Art Diego Motta | Studio de Art Diego Motta |
| Di Moto boy da Fatima · Do motoboy Fatima | Motoboy da Fátima |
| Karen (madu) · Karen Madureira · Karen Madureiro | Karen Madureira |
| Marcelo · Marcelo Lima | Marcelo Lima |
| Meta · Meta - personagens · Sheila/david · Sheila/david meta | Meta (Sheila e David) |
| Peterson · Peterson Caminhão | Peterson (caminhão) |
| Rosangela · ROSANGELA · Rosângela | Rosângela |
| THUNDER PRINT · Thunder Print 3D · THUNDER PRINT 3D | Thunder Print 3D |
| Will · Will Coordenador · William Castro | William Castro |
| Jose Carlos C DAUDT | Jose Carlos C. Daudt |
| Kelvem Jhonata Almeida da cruz | Kelvem Jhonata Almeida da Cruz |
| Mercado livre | Mercado Livre |
| Talita Stefani de castro (Will Castro) | Talita Stefani de Castro (Will Castro) |
| Victor Santos De Santana | Victor Santos de Santana |
| Certificado digital | Certificado Digital |

Grupos que a regra **não** junta, de propósito (chaves PIX diferentes): Talita × Talita Stefani de
Castro; Andressa Carvalho × Andressa da Silva; Beatriz Estevam × Beatriz Hornink; Giovana Serracini ×
Giovanna Sambra; Ruan Augusto × Ruan Siqueira; Fátima Regina Ribeiro × Motoboy da Fátima. Resultado
esperado em produção: **41 fornecedores** a partir de 65 grafias (ensaio de 17/11: 41, todos os grupos conferidos).

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/352-fornecedores-gastos-extras/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/api.md
├── checklists/requirements.md · checklists/<tema>.md (/speckit-checklist)
├── tasks.md
└── verify_352.py
```

### Código

```text
app/models.py                                  # Fornecedor + SpecialExpense.fornecedor_id/fornecedor
migrations/versions/f352a1b2c3d4_fornecedores.py   # tabela, coluna, importação
app/gastos/fornecedor_ops.py                   # NOVO: normalizar, listar, cadastrar, alterar, juntar, resolver_para_gasto
app/gastos/gastos_ops.py                       # create_expense/edit_expense chamam resolver_para_gasto
app/api/gastos_read.py                         # GET /api/gastos/fornecedores; `fornecedor_id` no _expense_dict
app/api/gastos_write.py                        # POST/PATCH fornecedores, POST juntar; `fornecedor_id` em POST/PATCH /api/gastos
frontend/apps/internal/src/lib/fornecedores.ts             # NOVO: tipos + hooks
frontend/apps/internal/src/lib/gastos.ts                   # fornecedor_id no tipo e nos inputs; invalida fornecedores
frontend/apps/internal/src/components/Gastos/FornecedorCampo.tsx   # NOVO
frontend/apps/internal/src/pages/GastosExtrasPage.tsx      # usa FornecedorCampo; botão "Fornecedores"
frontend/apps/internal/src/pages/FornecedoresPage.tsx      # NOVO
frontend/apps/internal/src/App.tsx · lib/navigation.tsx    # rota + item de menu
```

**Decisão de estrutura**: o fornecedor é do domínio Gastos (`app/gastos/`, `/api/gastos/...`,
`/gastos/fornecedores`); endpoints entram nos módulos `gastos_read`/`gastos_write` já registrados.
`fornecedor_ops` não importa `gastos_ops` no topo (`gastos_ops` é que o importa); a auditoria usa
`gastos_ops._log` por import tardio, como o resto do domínio faz entre módulos.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Verify e ensaio contra `manto_352`, não `manto_local` (Princípio VIII) | o `manto_local` é compartilhado com as sessões 348–351 abertas em worktrees; aplicar `f352a1b2c3d4` nele deixaria o banco numa revisão que as branches delas não conhecem; e os gastos dele param em 30/09 — a importação precisa das 65 grafias de 17/11 | refazer o `manto_local` apagaria o estado das outras sessões (memória "espelho próprio por feature", 338) |
| Nomes de fornecedor na migration | o dono pediu "você julga e já junta e arruma"; o resultado precisa sair igual na publicação, sem passo manual | arrumar à mão depois do deploy pela tela dependeria de alguém lembrar; só nomes entram, nunca PIX/documento (regra da 318) |

## Pós-publicação (registrar no `docs/03`)

A migration da sessão 348 (`a348c0d1e2f3`) também nasce sobre `d334b2c4e6f8`. Quem publicar a
segunda das duas reencadeia `down_revision` sobre a primeira (head único — `docs/00` §6.15).

# Plano de implementação: Todo o comercial volta a ver e abrir o orçamento de qualquer colega

**Branch**: `301-orcamentos-visiveis-comercial` | **Data**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/301-orcamentos-visiveis-comercial/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.0.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

Desfazer uma regressão de 23/07/2026: a migração do módulo de Orçamento para React (feature 177)
reintroduziu um filtro por dono que tinha sido removido de propósito em 20/05 (`6b191e4`), e a
regra se espalhou para a aba Comercial do evento (239) e o vínculo orçamento↔evento (273).

**Abordagem**: a trava tem dois pontos de origem no módulo (`_get_entry_or_none` e o `filter_by`
da listagem) e um herdeiro em cada domínio vizinho. Derruba-se a trava de **leitura** nos quatro
endpoints do histórico, mantém-se no `DELETE`, e **reescreve-se** a guarda do vínculo para olhar o
autor do orçamento *já vinculado* em vez do alvo — porque ao remover o 404 do alvo, o caminho de
"re-aplicar valores" ficaria aberto sobre venda alheia (R2). No frontend, duas telas deduzem RBAC
do silêncio do payload e precisam passar a receber flags explícitas (R3). Nada de migration, nada
de endpoint novo, nada de env nova.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy; React, TanStack Query, Tailwind, `@manto/ui`,
`@manto/api-client` (`apiFetch`/`apiFetchBlob`), `@manto/money`. **Nenhuma dependência nova.**

**Armazenamento**: PostgreSQL — verificação contra `manto_local`. **Sem migration**: `OrcamentoHistory`
e `AuditLog` já têm todas as colunas necessárias.

**Verificação**: `specs/301-orcamentos-visiveis-comercial/verify_301.py` contra `manto_local`
(13 cenários, 5 dos quais devem falhar); `cd frontend && npm run typecheck`; tela aberta no
Browser pane (`/orcamento/historico` e um evento vendido por outra pessoa, ambos logado como
COMERCIAL não-superadmin)

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs); esta feature é 100% tela de staff
(`apps/internal`)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: a listagem passa a varrer o histórico inteiro em vez de uma fatia por
usuário — 1.809 linhas no espelho, teto de 300 na resposta, e o `SELECT` único de eventos vivos da
feature 273 já evita N+1. Sem meta nova.

**Restrições**: sem rota pública nova (nada a mexer em `BACKEND_PREFIXES`); `sale_date` e
`sale_value` são campos com consequência financeira (comissão, hotfix 267b) e só o autor do
orçamento vinculado ou o superadmin os reescreve; `audit()` **não commita sozinha**.

**Escala/escopo**: 0 tabelas, 0 colunas, 0 migrations · 6 endpoints alterados (nenhum novo) ·
**5** arquivos de backend · **5** de frontend · 3 de documentação.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1 (ver "Reavaliação" ao fim).*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Auditoria reusa `app/utils.py:audit()` (R4) — sem model, helper ou migration novos. A busca de orçamento do evento (`OrcamentoPicker`) é consertada pelo mesmo endpoint da lista, sem código próprio (R6). O vínculo continua em `orcamento_evento_ops.set_event_orcamento`, intocado |
| II. Padrões de código | Type hints e docstrings nas funções tocadas; `_get_entry_or_none` se **divide em duas com nomes que declaram a regra** (R1) — é o remédio direto para "ler o nome do gate não basta"; `ruff check` nos arquivos tocados; TS estrito |
| III. Camadas / API First | `pode_gerir` e `pode_excluir` são RBAC e nascem **na view** (`agenda_read.py`, `orcamento_read.py`); `autor` é dado do orçamento e entra no `_ops` puro (`resumo_do_orcamento`, R7). Nenhum endpoint novo, nada a registrar em `app/api/__init__.py`, nenhuma rota pública |
| IV. Não quebrar o que funciona | Mudança **aditiva** no payload, com **uma remoção deliberada**: `is_superadmin` sai de `GET /api/orcamento/historico` (R5) após varredura que confirmou leitor único **da chave** (o endpoint tem três consumidores). O `DELETE` e a guarda 409 da 273 (evento vivo vinculado) continuam valendo |
| V. UI/UX com feedback | TanStack Query já em uso; a recusa do vínculo vira mensagem que **nomeia o autor** (FR-010), não um 404 mudo; "Excluir" some da linha em vez de falhar depois do `confirm()` |
| VI. Esteira (Nível 1) | `specify` → `clarify` → `plan` feitos; faltam `checklist`, `tasks`, `analyze`, `implement`, `converge`. Artefatos mínimos em `specs/301-orcamentos-visiveis-comercial/` |
| VII. Living Spec | Spec atualizada **antes** do código: as 3 decisões do clarify já estão em FR-011/012/013 e nos cenários |
| VIII. Verify antes do núcleo | `verify_301.py` é a primeira tarefa (fase Foundational), falhando pelos motivos certos; **4 cenários devem falhar** (8, 9, 10, 11); a auditoria e o vínculo são conferidos **por conexão separada** — R4 explica por que isso não é formalidade aqui |
| IX. Dinheiro BRL | Não cria nem formata valor novo; a tela já usa `brl()`/`@manto/money`. `sale_value` é lido, nunca reformatado |
| X. Mobile-first público | **Não se aplica** — `apps/internal`, tela de staff em desktop; nenhuma superfície pública tocada |
| XI. Framer Motion | **Não se aplica** — nenhuma transição nova; a mudança é de colunas, flags e botões |
| XII. Combobox / Maps | **Não se aplica** — o seletor de vendedor tem 5 opções (medido), abaixo do limiar de combobox; nenhum endereço novo |
| XIII. RBAC declarado | Gate de módulo `_require_vendas()` **inalterado** (COMERCIAL, SUPERADMIN); o que muda é a checagem de dono interna, tabelada em `contracts/api-endpoints.md` e destinada a `docs/01` §4.3 (FR-014). O frontend não decide nada: recebe `pode_gerir` e `pode_excluir` prontos |
| XIV. Config / efeito externo | **Nenhuma env nova.** Efeito externo tocado: o envio de e-mail já existente — o plano não amplia quem pode enviar para fora, só registra quando o orçamento é de outra pessoa |
| Stack | Sem migration (`OrcamentoHistory` e `AuditLog` intactos); sem Jinja novo; sem segredo novo |
| Operação e Deploy | Não toca `startCommand`, `render.yaml` nem volume. Deploy comum no Render (~60s de janela); sem script pós-deploy, sem backfill, sem passo manual no Shell |

**Resultado do gate (pré-Phase 0)**: **aprovado, sem violação a justificar.** A tabela de
"Rastreamento de complexidade" fica vazia de propósito.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/301-orcamentos-visiveis-comercial/
├── spec.md              # /speckit-specify + /speckit-clarify
├── plan.md              # este arquivo
├── research.md          # Phase 0 — R1..R9
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── api-endpoints.md # Phase 1 — o contrato que a 177 errou
├── checklists/
│   └── requirements.md  # /speckit-specify
├── tasks.md             # /speckit-tasks
└── verify_301.py        # Princípio VIII — escrito antes do núcleo
```

### Código (só o que esta feature toca)

```text
app/api/orcamento_read.py          # :150 filtro da lista · :219 _get_entry_or_none → divide em duas
                                   # :214 remove is_superadmin do payload · :190 users sempre
                                   # + pode_excluir por linha
app/api/orcamento_write.py         # :66 PDF, :88 e-mail, :115 DELETE — trocam de função de busca
                                   # e-mail ganha audit() + commit explícito
app/api/agenda_read.py             # :905-916 cai owns_orcamento · payload ganha pode_gerir/autor
                                   # :157-159 apaga o comentário que ensina a regra antiga
                                   # + bloco RBAC: de topo (Princípio XIII)
app/api/agenda_write.py            # :1185 cai o 404 por dono do alvo
                                   # :1207 guarda reescrita: trocar + soltar + re-aplicar
app/calendar/orcamento_evento_ops.py  # :70 resumo_do_orcamento ganha `autor`
app/utils.py                       # reusado sem alteração (audit)

frontend/apps/internal/src/lib/orcamento.ts                 # tipos: -is_superadmin, +pode_excluir
frontend/apps/internal/src/pages/OrcamentoHistoricoPage.tsx # coluna e filtro incondicionais;
                                                            # Excluir por pode_excluir
frontend/apps/internal/src/components/OrcamentoPicker.tsx   # mostra o vendedor; docstring corrigido
frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx
                                   # :580 orcamentoDeOutro deixa de ser dedução e vira flag

docs/01_SISTEMA_E_BANCO.md         # §3.13 e §4.3 (FR-014)
docs/02_*                          # tela Histórico de Orçamentos
docs/03_HISTORICO_MUTACOES.md      # entrada no topo
```

**Decisão de estrutura**: nada muda de lugar. A feature é cirúrgica — remove uma condição em
quatro pontos, reescreve uma guarda em um ponto, e transforma duas deduções de frontend em flags de
servidor. O único arquivo que ganha função nova é `orcamento_read.py`, e ganha porque a função
existente precisa **se dividir** para que o `DELETE` não herde a liberação (R1).

## Ordem de implementação (entra no `/speckit-tasks`)

1. **Foundational** — `verify_301.py` com os 12 cenários, falhando pelos motivos certos.
2. **História 1 (P1)** — `orcamento_read.py` + `orcamento_write.py` + tipos e tela do histórico.
   Inclui a auditoria (FR-013) e a remoção de `is_superadmin` (R5).
3. **História 2 (P2)** — `agenda_read.py` (payload do evento) + `ComercialSection` (flag em vez de
   dedução) + `resumo_do_orcamento` ganha `autor`.
4. **História 3 (P3)** — `agenda_write.py` (guarda reescrita) + botões da aba Comercial por
   `pode_gerir` + `OrcamentoPicker` mostrando o vendedor.
5. **Documentação** — `docs/01` §3.13 e §4.3, `docs/02`, `docs/03` (FR-014).

As histórias são independentes e verificáveis sozinhas, na ordem das prioridades da spec: parar
depois da 1 já entrega o pedido literal do dono.

## Rastreamento de complexidade

> Preencher SÓ se o Constitution Check tiver violação a justificar.

**Vazia** — nenhuma violação. A feature remove condição, não adiciona camada.

## Reavaliação do Constitution Check (pós-Phase 1)

Refeita depois de `data-model.md`, `contracts/api-endpoints.md` e `quickstart.md`:

- **Nenhuma violação nova.** O desenho da Phase 1 não introduziu entidade, endpoint, env nem
  dependência — confirmou o contrário: uma remoção de chave (`is_superadmin`) e duas adições de
  flag de RBAC computada no servidor.
- **Princípio XIII reforçado pelo contrato**: `contracts/api-endpoints.md` declara a regra de dono
  endpoint por endpoint, **em oposição explícita** à linha errada de
  `specs/177-.../contracts/api-endpoints.md:119`. Como foi um contrato desatualizado que reimportou
  esta regressão, o contrato desta feature carrega um aviso de não-repetição — é o próprio FR-014
  em forma de artefato.
- **Princípio VIII reforçado**: o `quickstart.md` marca os dois pontos onde um verify passaria
  verde sem testar nada (a auditoria sem commit e o vínculo conferido na mesma sessão).

**Gate final: aprovado.**

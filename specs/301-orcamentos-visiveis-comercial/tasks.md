---
description: "Tarefas da feature 301 — orçamentos visíveis para todo o comercial"
---
# Tasks: Todo o comercial volta a ver e abrir o orçamento de qualquer colega

**Input**: artefatos em `/specs/301-orcamentos-visiveis-comercial/`

**Pré-requisitos**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) ·
[data-model.md](./data-model.md) · [contracts/api-endpoints.md](./contracts/api-endpoints.md) ·
[quickstart.md](./quickstart.md)

**Verificação (OBRIGATÓRIA — constituição, Princípio VIII)**:
`specs/301-orcamentos-visiveis-comercial/verify_301.py`, contra `manto_local`. A tarefa que
**escreve** o verify é a T001, na fase Foundational, **antes** do núcleo: ele nasce falhando pelos
motivos certos e passa ao fim de cada história. Não existe pytest nem `tests/` neste repositório.

**Organização**: por história da spec; cada uma implementável, verificável e entregável sozinha.

## Formato: `[ID] [P?] [Story] Descrição`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1, US2, US3 — histórias da spec

---

## Phase 1: Setup

**Nenhuma tarefa.** Esta feature não tem setup: sem migration (nem `models.py` nem `AuditLog`
mudam), sem constante nova em `app/constants.py`, sem dependência nova em `requirements.txt` ou
`package.json`, sem env nova em `app/config.py` ou no painel do Render, sem rota pública (nada a
mexer em `BACKEND_PREFIXES` de `frontend/server.js`).

A única preparação é de ambiente, não de código: `manto_local` de pé, e as três variáveis de
`quickstart.md` §Pré-requisitos exportadas em toda sessão de script.

---

## Phase 2: Foundational (bloqueia as histórias)

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T001 **`specs/301-orcamentos-visiveis-comercial/verify_301.py`** — os 13 cenários da seção
      "Verificação" da spec, com três usuários descartáveis (A = COMERCIAL autor, B = COMERCIAL
      não-superadmin, F = FINANCEIRO). Login só por `POST /api/auth/login`; requisições HTTP fora
      de `app.app_context()`; **escrita conferida por conexão separada** nos cenários 5, 7 e 9
      (auditoria, vínculo e `sale_value`/`sale_date` — ver `quickstart.md` §"os dois pontos onde
      este verify passa verde sem testar nada"); **cinco cenários que DEVEM falhar** (8, 9, 10,
      11, 12). Respeitar os **arranjos obrigatórios** dos cenários 9 e 10 descritos na spec: sem
      eles as asserções nascem vazias e passam verde com a trava quebrada. Limpeza no `finally` com `rollback()` → `roles.clear()` → delete do usuário; prefixo
      `__v301_` nos dados; saída `N/N OK` e código de retorno 1 em falha

**Checkpoint**: verify escrito e **falhando pelos motivos certos** — cenários 1–7 falham por dono
(403/404/lista vazia), nunca por `ImportError`, credencial ou endereço inválido. Se falhar por
outra coisa, o verify está errado, não o código.

---

## Phase 3: História 1 — O histórico volta a ser do time (Prioridade: P1) 🎯 MVP

**Objetivo**: qualquer pessoa do comercial vê, abre, recalcula, baixa o PDF e reenvia o e-mail do
orçamento de qualquer colega — sabendo de quem é cada um. Excluir continua sendo do dono, e a tela
para de oferecer o botão a quem não pode.

**Verificação da história (obrigatória)**: cenários **1–5, 10 e 11** do `verify_301.py` em PASS;
tela `/orcamento/historico` aberta no Browser pane **logada como COMERCIAL não-superadmin**
(`quickstart.md` §3.1).

- [X] T002 [US1] `app/api/orcamento_read.py`: dividir `_get_entry_or_none(entry_id, is_sa)` em
      duas funções com nome que declara a regra — `_get_entry(entry_id)` (só existência, para
      leitura) e `_get_entry_para_excluir(entry_id, is_sa)` (existência + dono). **Não** apagar a
      checagem de dono: ela migra inteira para a segunda função (FR-006). Ver `research.md` R1.
      São **7** referências ao nome antigo, não 4: além das três de `orcamento_write.py` (T005),
      atualizar aqui a chamada do **detalhe** (`:236` — o endpoint mora neste arquivo, não no de
      escrita) e, em `app/api/orcamento_write.py:16`, o **import**, senão o módulo de escrita cai
      logo no import. A sétima é um comentário em `agenda_read.py:157-159`, tratada na T010
- [X] T003 [US1] `app/api/orcamento_read.py`: na listagem (`api_orcamento_historico_list`) remover
      `if not is_sa: query.filter_by(user_id=...)`, deixar `user_id` da querystring valer para
      qualquer autorizado, popular `users` **sempre**, e acrescentar `pode_excluir` por linha em
      `_entry_summary` (autor == quem pede, ou SUPERADMIN) — FR-001, FR-004, FR-005, FR-007
- [X] T004 [US1] `app/api/orcamento_read.py`: remover a chave `is_superadmin` do payload da
      listagem (`research.md` R5) e **criar** — o arquivo não tem nenhum hoje — o bloco `RBAC:` no
      topo do módulo, logo depois da linha-resumo do docstring (Princípio XIII; formato de
      `app/api/notificacoes_write.py:1-7`). O bloco **não** pode dizer "o gate é de módulo": são
      **dois** gates aqui — `_require_vendas()` em opções, personagens-no-dia, distância,
      histórico e histórico/`<id>`; `_require_superadmin()` **só** em `GET /orcamento/settings`.
      Declarar que, passado o gate, **não há** checagem de dono (o `DELETE`, em `orcamento_write`,
      é o ponto único) e que a liberação é deliberada (`6b191e4`), para a próxima reescrita não
      reimportar o filtro por `user_id` — FR-014
- [X] T005 [US1] `app/api/orcamento_write.py`: PDF e enviar-email passam a usar `_get_entry`;
      **o `DELETE` passa a usar `_get_entry_para_excluir`**. O detalhe **não** está aqui — mora em
      `orcamento_read.py` e é tarefa da T002. Atenção à ordem real do `DELETE`: a checagem de dono
      vem **primeiro** (`:115`, 404) e a guarda 409 de evento vivo só depois (`:124`) — quem não é
      dono nunca chega no 409. **Não reordenar**: inverter passaria a confirmar a existência do
      evento vinculado para quem não é dono (Princípio XIII: 404, não 403) — FR-003, FR-006
- [X] T006 [US1] `app/api/orcamento_write.py`: em `api_orcamento_historico_enviar_email`, gravar
      auditoria com `audit()` de `app/utils.py` **só** quando o orçamento é de outra pessoa **e**
      o envio deu certo, seguida de `db.session.commit()` explícito — `audit()` não persiste
      sozinha e esta view não comita hoje (FR-013; `research.md` R4; hotfix 257). No mesmo arquivo,
      **criar** o bloco `RBAC:` de topo (Princípio XIII; hoje não existe): os dois gates importados
      de `orcamento_read.py`, quais rotas cada um cobre, o fato de `GET .../pdf` ser **leitura**
      apesar de morar no módulo `_write`, e que o `DELETE` é a **única** checagem de dono que
      sobra — FR-014
- [X] T007 [P] [US1] `frontend/apps/internal/src/lib/orcamento.ts`: em `OrcamentoHistoricoEntry`
      acrescentar `pode_excluir: boolean`; em `OrcamentoHistoricoResponse` **remover**
      `is_superadmin`. O `npm run typecheck` passa a ser quem prova que nenhum consumidor ficou
      para trás
- [X] T008 [US1] `frontend/apps/internal/src/pages/OrcamentoHistoricoPage.tsx`: coluna "Vendedor" e
      seletor de vendedor **incondicionais** (sem `is_superadmin`); a lista abre com o time inteiro,
      sem filtro pré-aplicado (FR-012); o botão "Excluir" só é renderizado quando `pode_excluir`

**Checkpoint**: MVP entregue — o pedido literal do dono está atendido e verificável sozinho.

---

## Phase 4: História 2 — A aba Comercial mostra o orçamento do colega (Prioridade: P2)

**Objetivo**: ao abrir um evento vendido por outra pessoa, quem é do comercial vê o que o orçamento
vendeu e o link para abri-lo — **sem** ganhar botões que o servidor vai recusar.

**Verificação da história (obrigatória)**: cenário **6** do `verify_301.py` em PASS; evento vendido
por outra pessoa aberto no Browser pane como COMERCIAL não-superadmin (`quickstart.md` §3.2).

> **Por que o `pode_gerir` entra nesta história e não na 3**: assim que o payload passar a entregar
> o orçamento (T010), a dedução `orcamentoDeOutro = !orc && venda.tem_orcamento` de
> `ComercialSection.tsx:580` vira `false` para sempre e os três botões aparecem para todo mundo.
> Entregar a US2 sem T012 criaria o botão mentiroso — a US2 **não é independente** sem ele.

- [X] T009 [P] [US2] `app/calendar/orcamento_evento_ops.py`: `resumo_do_orcamento` passa a incluir
      **`autor`** (nome de quem fez o orçamento). A chave **não** se chama `vendedor`: o mesmo
      bloco `venda` já traz `venda.seller` (`agenda_read.py:943`), que é o vendedor **do evento** —
      outra pessoa. É dado do orçamento, então cabe no `_ops` puro; `pode_gerir` **não** entra aqui
      (é RBAC, Princípio III)
- [X] T010 [US2] `app/api/agenda_read.py`: remover o bloco `owns_orcamento` — o comercial deixa de
      precisar ser o autor para receber `orcamento_history_id` e o resumo — e acrescentar
      `pode_gerir` ao bloco `venda.orcamento`, calculado **na view** (autor do orçamento vinculado,
      ou SUPERADMIN). FINANCEIRO continua sem o bloco e com `tem_orcamento` — FR-009.
      Apagar também os comentários de `:157-159` **e `:901-904`**, que ainda ensinam a regra que
      esta feature remove
      ("só quem consegue de fato abrir… o comercial **dono** do orçamento") e cita
      `_get_entry_or_none`, nome que deixa de existir na T002. E **criar** o bloco `RBAC:` de topo
      do módulo (Princípio XIII; hoje não existe), descrevendo `_role_flags` e o que cada flag
      libera — FR-014
- [X] T011 [P] [US2] `frontend/apps/internal/src/lib/agenda.ts`: em `EventoDetalhe`, o
      `venda.orcamento` ganha `autor: string` e `pode_gerir: boolean`
- [X] T012 [US2] `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx`: trocar a
      dedução `orcamentoDeOutro` por `pode_gerir` vindo do servidor; mostrar sempre os chips, o
      nome do vendedor e "Abrir orçamento"; renderizar "Aplicar ao evento", "Trocar" e
      "Desvincular" **somente** quando `pode_gerir` — FR-007, FR-009, `research.md` R3

**Checkpoint**: histórias 1 e 2 funcionam de forma independente; nenhuma tela oferece ação que o
servidor recusa.

---

## Phase 5: História 3 — Amarrar ao evento o orçamento de um colega (Prioridade: P3)

**Objetivo**: qualquer pessoa do comercial vincula a um evento **sem orçamento** o orçamento de uma
colega; trocar, soltar ou re-aplicar um vínculo alheio continua sendo do autor ou do superadmin, e
a recusa diz de quem é.

**Verificação da história (obrigatória)**: cenários **7, 8 e 9** do `verify_301.py` em PASS (7
passa; 8 e 9 **devem falhar**); fluxo de vincular conferido no Browser pane (`quickstart.md` §3.3).

- [X] T013 [US3] `app/api/agenda_write.py`: remover o 404-por-dono sobre o orçamento **alvo**,
      mas **condicionado ao papel**: quem tem o módulo de Orçamento (COMERCIAL ou SUPERADMIN) passa
      a poder apontar qualquer orçamento; **FINANCEIRO continua levando 404** ao apontar orçamento
      que não é dele. Sem essa condição a feature dá ao FINANCEIRO — que passa em
      `_can_manage_sale()` e hoje é barrado justamente por este 404 — um poder que ninguém pediu,
      contra §Fora de escopo e SC-005. A partir daqui a única checagem de dono sobre o **alvo** é
      essa de papel; a de autoria passa a valer só para o vínculo **atual** — FR-010, FR-011
- [X] T014 [US3] `app/api/agenda_write.py`: reescrever a guarda do vínculo atual para cobrir os
      **três** verbos — trocar, desvincular e **re-aplicar** (o caso em que o id pedido é igual ao
      vínculo atual e hoje escapa da condição `atual_id != entry.id`). Manter `orcamento_de_outro`
      e acrescentar o **nome do autor** à mensagem. Atualizar o docstring do endpoint, que hoje
      justifica a trava por "quem não vê o orçamento não o troca" — razão que deixou de existir —
      FR-011, `research.md` R2
- [X] T015 [P] [US3] `frontend/apps/internal/src/components/OrcamentoPicker.tsx`: a linha do
      resultado passa a mostrar o vendedor (agora a busca devolve orçamentos de todo o time); e
      corrigir o docstring do componente, que afirma *"já respeita o dono: comercial só vê os
      próprios, superadmin vê todos"* — frase que esta feature torna falsa (`research.md` R6)
- [X] T016 [US3] `frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx`: exibir a
      recusa 409 com o nome do autor e a saída — os **três** verbos que FR-011 tranca: "só <nome>
      ou o superadmin podem trocar, desvincular ou re-aplicar" —
      em vez de erro genérico — FR-010

**Checkpoint**: as três histórias funcionam de forma independente; o fluxo completo fecha.

---

## Phase 6: Polimento e transversais

- [X] T017 [P] `cd frontend && npm run typecheck` limpo nas três SPAs — é o portão que prova que a
      remoção de `is_superadmin` não deixou consumidor para trás
- [X] T018 [P] `ruff check` limpo em `app/api/orcamento_read.py`, `app/api/orcamento_write.py`,
      `app/api/agenda_read.py`, `app/api/agenda_write.py`, `app/calendar/orcamento_evento_ops.py`
- [X] T019 Telas abertas de verdade no Browser pane, **como COMERCIAL não-superadmin**, incluindo
      `/orcamento` (a calculadora): o selo de contagem ao lado do link "Histórico de Orçamentos"
      (`OrcamentoCalculadoraPage.tsx:508-511`) passa a contar o time e satura em **300** — efeito
      aceito (spec, §Casos de borda), mas conferir que a tela não quebra. Demais telas conforme
      `quickstart.md` §3.1, §3.2 e §3.3; e as regressões de `quickstart.md` §4 conferidas
      (FINANCEIRO segue em 403, EducaManto intocado, 409 de evento vivo no DELETE, Config. de
      Preços só do SUPERADMIN)
- [X] T020 `docs/01_SISTEMA_E_BANCO.md` §3.13: a regra de escopo do histórico, explícita, mais a
      linha de auditoria do reenvio de orçamento alheio
- [X] T021 `docs/01_SISTEMA_E_BANCO.md` §4.3: atualizar a linha do `_require_vendas()` homônimo de
      `orcamento_read.py` (**sem** checagem de dono, exceto no `DELETE`) e a de
      `PATCH /api/events/<id>/orcamento` (vincular livre; trocar/soltar/re-aplicar do autor).
      **Não** enfiar `_require_superadmin` nessa linha: §4.3 é indexada por função de gate e já tem
      a linha do `_require_superadmin()` citando `orcamento_read` — duplicar ali é criar duas
      verdades na mesma tabela. Conferir também os números de linha citados na tabela
      (`orcamento_read.py:30`, `orcamento_write.py:19`), que os blocos `RBAC:` das T004/T006
      deslocam — FR-014
- [X] T022 [P] `docs/02_*`: tela Histórico de Orçamentos — coluna "Vendedor" e filtro de vendedor
      para todo o comercial, e o botão "Excluir" que só aparece para quem pode
- [X] T023 `docs/03_HISTORICO_MUTACOES.md`: entrada no topo registrando a relação **causa → efeito**
      — a 301 desfaz a regressão introduzida pela 177 em 23/07/2026 e amplia a trava de escrita do
      vínculo (não basta dizer o que foi feito)
- [X] T025 `specs/177-migracao-ferramentas-react/contracts/api-endpoints.md:118-119`: nota inline
      de **regra superada** pela 301, apontando para `docs/01` §4.3. O arquivo fica como registro
      histórico — mas foi ele que reimportou a restrição, então não pode continuar ensinando a
      regra antiga sem aviso — FR-015
- [X] T024 Percorrer [checklists/rbac.md](./checklists/rbac.md) e
      [checklists/regressao.md](./checklists/regressao.md); resolver o que ficar aberto **na spec**
      antes de chamar a feature de pronta (os portões CHK001–CHK010 são compartilhados: rode uma vez)

---

## Dependências e ordem

```text
Foundational (T001)
      │
      ▼
US1  T002 → T003 → T004        T007 ─┐          (T007 é [P] com o backend)
       └──→ T005 → T006              ├→ T008
      │
      ▼
US2  T009 [P] ─┐                T011 [P] ─┐
               ├→ T010 ─────────────────── ├→ T012
      │
      ▼
US3  T013 → T014        T015 [P]        T016
      │
      ▼
Polimento (T017–T025)
```

- **T002 é pré-requisito de T005**: o `DELETE` só pode trocar de função depois que a função de dono
  existir separada. Inverter a ordem libera o `DELETE` por engano — é o erro simétrico mais
  provável desta feature, e o cenário 10 do verify existe para pegá-lo.
- **T003 e T004 mexem no mesmo arquivo** que T002: sequenciais, sem `[P]`.
- **Não existe estado verde entre T002 e T005**: a T002 renomeia a função, então o import de
  `orcamento_write.py:16` quebra o módulo inteiro até a T005 rodar. É esperado — mas não pare no
  meio nem rode o verify aí, porque a falha será de import, não de regra. Rede de segurança
  parcial: com `F` ligado no `ruff`, esquecer a chamada do **detalhe** vira `F821`; as três de
  `orcamento_write.py` continuam "definidas" pelo import e só caem em runtime.
- **T012 não é opcional para a US2**: sem ele a história entrega botões que o servidor recusa.
- **T016 e T012 são o mesmo arquivo**: sequenciais.
- As histórias respeitam a ordem de prioridade da spec (P1 → P2 → P3) e cada uma fecha com os seus
  cenários do verify em PASS.

## Paralelismo

| Momento | Podem ir juntas |
|---|---|
| Dentro da US1 | **T007** (tipos do frontend) com **T002–T006** (backend) |
| Dentro da US2 | **T009** (`_ops`) e **T011** (tipos) com o backend da view |
| Dentro da US3 | **T015** (picker) com **T013/T014** (endpoint) |
| No polimento | **T017**, **T018** e **T022** entre si |

## Estratégia

- **MVP**: Foundational + História 1 (T001–T008). Entrega o pedido literal do dono — "ver e abrir
  orçamentos de outras pessoas" — e é verificável sozinha. Parar aqui é uma entrega legítima.
- **Incremental**: cada história fecha com os seus cenários do verify em PASS e não quebra a
  anterior. A US2 leva junto o `pode_gerir` justamente para não abrir um estado quebrado.
- **Commits**: `feat(301):` por tarefa ou grupo lógico, **sempre por caminho** — nunca `git add -A`
  (a raiz tem tokens e arquivos não versionados). Docs em `docs(301):`.
- **Deploy**: comum. Não toca `startCommand`, `render.yaml`, volume nem migration; sem backfill e
  sem passo manual no Shell do Render.

---

## Phase 7: Convergence

Achados do `/speckit-converge` (2026-09-22): 10 grupos de intenção avaliados contra o código, com
passada adversarial. **17 lacunas confirmadas, que são 8 distintas** — o JSDoc obsoleto foi
reportado por seis grupos independentes.

O padrão dos achados é o próprio assunto da feature: **texto que ensina a regra antiga**, em três
lugares que a implementação não alcançou, e **citação `arquivo:linha` deslocada** por ela mesma.

- [X] T026 **CRITICAL** Criar o bloco `RBAC:` no topo de `app/api/agenda_read.py`, no formato de
      `app/api/notificacoes_write.py:1-7` e dos irmãos que a T004/T006 já receberam: o módulo é de
      serialização e não tem rota própria (o gate é da view que o chama), `_role_flags` (`:135`) é
      a fonte das flags e respeita a impersonação, `show_comercial` = COMERCIAL/FINANCEIRO/SA, e
      desde a 301 `venda.orcamento` sai para quem tem o módulo de Orçamento, sem checagem de dono.
      Aproveitar para corrigir a linha-resumo, que ainda anuncia o detalhe do evento como trabalho
      futuro ("entra no Incremento B") embora `serialize_event_detail` (`:677`) more aqui —
      per tasks.md T010 (FR-014), Constituição XIII (`missing`)
- [X] T027 **HIGH** Reescrever o JSDoc de `useOrcamentoHistorico` em
      `frontend/apps/internal/src/lib/orcamento.ts:321`, que ainda afirma "SUPERADMIN vê todos,
      demais só os próprios" — falso contra o endpoint desde a T003, e no arquivo que a T007
      editou, onde os comentários vizinhos (`:298`, `:307`) já citam a 301 — per FR-015
      (`contradicts`)
- [X] T028 **HIGH** Pôr nota de regra superada no parágrafo da feature 239 em
      `docs/01_SISTEMA_E_BANCO.md:724-727`, que ainda ensina que `venda.orcamento_history_id` "só
      vem preenchido quando quem lê consegue de fato abrir o orçamento (superadmin, ou o comercial
      dono daquele orçamento)". Mesmo padrão da nota aplicada ao contrato da 177 — per FR-015
      (`contradicts`)
- [X] T029 **MEDIUM** Corrigir as três citações que o bloco `RBAC:` da T004 deslocou:
      `_require_vendas` saiu de `orcamento_read.py:30` para `:43`, e `docs/00_MAPA_DO_SISTEMA.md:115`,
      `docs/05_DIVIDA_TECNICA.md:29` e `docs/05_DIVIDA_TECNICA.md:164` seguem apontando para `:30`.
      Preferir citar só o arquivo e o nome da função, que não envelhece — per CLAUDE.md §0
      ("citação arquivo:linha se confere contra HEAD") (`partial`)
- [X] T030 **MEDIUM** Completar a linha `show_comercial` de `docs/01` §4.3 (`:1505`) com a regra da
      301 para o detalhe do evento: passado o gate, `venda.orcamento` sai para quem tem o módulo de
      Orçamento, sem checagem de dono; FINANCEIRO segue só com `tem_orcamento` — per FR-014
      (`partial`)
- [X] T031 **MEDIUM** Corrigir a seção do `PATCH` em
      `specs/301-orcamentos-visiveis-comercial/contracts/api-endpoints.md`: o 404 passou a ter
      **duas** causas (alvo inexistente **e** quem não tem o módulo de Orçamento apontando orçamento
      alheio), e a linha da tabela ainda diz "qualquer COMERCIAL" sem a ressalva do FINANCEIRO —
      per contracts §PATCH (`contradicts`)
- [X] T032 **MEDIUM** Trocar a contagem por conteúdo no cenário 5 de
      `specs/301-orcamentos-visiveis-comercial/verify_301.py`: hoje `_qtd_auditoria` só conta
      linhas, e SC-008 exige que o reenvio seja **reconstituível** — quem enviou, qual orçamento e
      para qual endereço. Ler `actor_name` e `detail` por conexão separada e aferi-los —
      per SC-008 (`partial`)
- [X] T033 **LOW** Decidir sobre a chave `autor` extra no 409 de
      `app/api/agenda_write.py:1236`: nenhum artefato a pede (a mensagem já nomeia o autor, e é ela
      que a tela mostra). Remover, ou registrá-la no contrato — per contracts §PATCH (`unrequested`)

---

## Phase 8: Convergence (2ª rodada)

A rodada 1 foi corrigida item a item e a 2ª achou **mais dois resíduos das mesmas duas classes**
— sinal de que caçar de um em um deixaria cauda. Fechadas por **varredura da classe inteira**:

- **Textos que ensinam a regra antiga** (`grep` por "dono do orçamento", "comercial dono",
  "SUPERADMIN vê todos", "só os próprios" em `app/`, `frontend/` e `docs/00–02,04,05`): sobrava
  **um** no domínio Orçamento. Os demais acertos são de **Gastos Extras** e do portal — domínios
  onde "só os próprios" é decisão registrada (features 013, 179) e está correto, explicitamente
  fora do escopo desta feature.
- **Módulos de API tocados sem bloco `RBAC:` de topo**: sobrava **um**. `orcamento_evento_ops.py`
  não entra — é `_ops` puro, sem rota (Princípio XIII trata de rota).

- [X] T034 **HIGH** Reescrever os comentários de `venda.orcamento_history_id`, `tem_orcamento` e
      `orcamento` em `frontend/apps/internal/src/lib/agenda.ts`, que ainda diziam "superadmin, ou
      comercial **dono** do orçamento" e "só vem para quem pode abri-lo" — falso contra
      `agenda_read.py` desde a T010, no arquivo que a T011 editou — per FR-015 (`contradicts`)
- [X] T035 **MEDIUM** Criar o bloco `RBAC:` no topo de `app/api/agenda_write.py`, o último módulo
      de API tocado sem ele: os cinco gates do evento, a nota de que ensaio e grupo têm os seus, e
      a regra de autoria da 301 no `PATCH /events/<id>/orcamento` — per Constituição XIII
      (`missing`)

---

## Phase 9: Convergence (3ª rodada)

**2 confirmadas, 3 derrubadas** (8 → 2 → 2 nas três rodadas). As duas são efeito colateral das
edições da própria convergência, e uma delas expôs um defeito no meu método de varredura.

**Por que a varredura da fase 8 não pegou**: ela era `grep` por linha, e a frase
`"orçamento de outro vendedor"` quebra entre `outro` e `vendedor` num comentário de 100 colunas.
Busca por **prosa** neste repositório precisa normalizar antes de casar — juntar linhas, remover
prefixo de comentário, tirar acento e caixa. Refeita assim, a varredura achou **exatamente um**
resíduo; os demais acertos são de Gastos Extras e do portal, corretos.

- [X] T036 **MEDIUM** Reescrever o comentário de `tem_orcamento` em `app/api/agenda_read.py`, que
      dizia que o painel avisa "orçamento de outro vendedor" — frase que a tela não mostra mais, e
      causa que a T010 eliminou para o COMERCIAL: o único caso restante é quem não tem o módulo —
      per FR-015 (`contradicts`)
- [X] T037 **MEDIUM** Corrigir `docs/00_MAPA_DO_SISTEMA.md` e `docs/05_DIVIDA_TECNICA.md`, que
      citavam `agenda_read.py:136-161` para `_role_flags` — faixa deslocada para `:149` pelo bloco
      `RBAC:` da T026, a mesma classe que a T029 abriu. Passaram a citar arquivo + nome da função —
      per FR-014, CLAUDE.md §0 (`partial`)

# Pesquisa — Feature 322

## R1. De onde vem o tipo do personagem

- **Decisão**: um campo `perfil` em cada item de `_compute_performer_caches` (e em `produtos._item`),
  montado com os mesmos ingredientes da `descricao` da conta do teto, mas sem valores e sem a faixa
  de Natal: tipo + marcas. Gravado em `EventRole.perfil_vendido`.
- **Tipo**: ator → `ATOR_SUBTIPO_LABELS` ("Ator cara-limpa", "Boneco", "Cantor"); cantor → "Cantor";
  especial → o nome do especial como a tabela de preços o escreve ("Boneco Grande Especial",
  "Bailarino", "Perna de Pau", "Sósia"); vaga de produto (309) → o rótulo do produto ("Visita
  Mágica"). Mantém a grafia da tabela (não rebaixa a caixa): "Homem-Aranha" e "Papai Noel" são nomes
  próprios.
- **Marcas**, nesta ordem: "show", "cantor" (especial que canta), "com maquiagem" / "com
  maquiagem especial". Separador " · ".
- **Personagem especial cujo nome repete o tipo** ("Bailarino" chamado "Bailarino"): o perfil fica
  igual; a tela mostra mesmo assim — repetir é melhor do que o casting achar que falta informação.
- **Rationale**: a conta do teto já é a fonte do que foi vendido e só o superadmin a lê; tirar dela o
  texto (parse) seria frágil. Produzir o campo ao lado garante a mesma origem.
- **Alternativas**: (a) parsear `cache_cap_note` na leitura — rejeitado: texto com valores e formato
  livre; (b) guardar o tipo cru ("especial", "Bailarino") e montar na tela — rejeitado: duas fontes
  do mesmo texto, e a tela teria de conhecer a tabela de especiais.

## R2. O perfil chega a quem

- **Decisão**: `_serialize_role` manda `perfil` (texto pronto) a todo leitor do elenco: o gravado
  ou, sem ele, as marcas das flags ("Cantor", "Com maquiagem", "Cantor · com maquiagem"). Sem nada,
  `null`.
- **Rationale**: a spec (FR-002/FR-003) pede para quem vê o card; sem dinheiro, não há o que esconder.

## R3. Pareamento do perfil na criação

- **Decisão**: o mesmo pareamento posicional do teto (`orc_chars[i]`), em `_create_roles_from_input`.
  Linha acrescentada à mão além da lista nasce sem perfil (como nasce sem teto).
- **Vínculo 273**: personagem casado pelo nome normalizado recebe o perfil se ainda não tiver
  (FR-004). Os não casados já vão no relatório.

## R4. Onde o sistema cria vaga sozinho (marca `criada_pelo_sistema`)

Levantado com `grep "EventRole("`:

| Local | O que cria | Marca? |
|---|---|---|
| `routes._ensure_coordinator` | Coordenador vazio (criação sem campo, sync do Google) | sim |
| `routes._ensure_sound_technician` | Técnico de Som (Nivaldo) + Presença | sim |
| `routes._create_extra_roles_from_orcamento` | Coordenador/Técnico/Maquiador do orçamento | sim (inclusive quando corrige linha legada no lugar) |
| `orcamento_evento_ops.aplicar_equipe_do_orcamento` | Coordenadores, Técnico, Maquiador | sim |
| `casting_ops.garantir_vaga_de_maquiador` (novo) | Maquiador | sim |
| `routes._apply_default_roles` com `coordinator_talent_id` | Coordenador escolhido no formulário | **não** (clarify) — leva `escalado_pelo_comercial` |
| `event_ops.update_event_core` (coordenador do formulário) | idem | **não** |
| `casting_ops.add_role` | "Adicionar pessoa/personagem" | não |
| `routes` sync do Google (personagem do título) | personagem | não (é o título que alguém escreveu) |
| `virtuais_ops` (1621) | vaga da venda virtual | fora de escopo (não é casting de evento presencial) |

## R5. A regra do maquiador

- **Decisão**: `casting_ops.garantir_vaga_de_maquiador(event) -> EventRole | None`. Consulta as vagas
  do evento por `EventRole.query.filter_by(event_id=...)` (o autoflush enxerga as recém-adicionadas
  na mesma sessão); se o evento não está cancelado, tem personagem com `needs_makeup` e nenhuma vaga
  com "maquiad" no nome, cria `Maquiador` (`role_type="extra"`, sem talento, sem teto,
  `criada_pelo_sistema=True`) e um `EventLog` do Sistema. Não comita (quem chama comita).
- **Chamadas**: fim de `_create_event_core` (depois de `_apply_default_roles`); fim de
  `update_event_core`; `vincular_orcamento` depois do `aplicar_equipe`.
- **Não roda** no sync do Google (personagem do título nasce sem maquiagem) nem por script
  (sem retroativo).
- **Critério "maquiad"**: idêntico ao selo `maquiagem.fechado` de `agenda_read` e a
  `ehVagaDeMaquiador` do React, para o selo e a regra concordarem.

## R6. Trava da maquiagem

- **Decisão**: em `update_event_core`, quando `is_superadmin` é falso: vaga existente mantém
  `role.needs_makeup`; vaga nova nasce com `needs_makeup=None`. O parâmetro `is_superadmin` já chega
  (`api_update_event`). Criação (`_create_roles_from_input`) e vínculo continuam livres (FR-013).
- **Tela**: `ElencoBlock` ganha `maquiagemTravada?: boolean`; `EventEditPage` passa
  `!data.flags.is_superadmin`. Caixa `disabled` + texto de ajuda uma vez no bloco.
- **Por que no servidor**: Princípio XIII — a tela travada sozinha deixa a rota aceitando.

## R7. Marca do comercial

- **Decisão**: `escalado_pelo_comercial=True` onde o formulário põe talento: `_create_roles_from_input`
  (pré-escala), `_apply_default_roles` (coordenador escolhido), `update_event_core` (pré-escala que
  troca o talento; coordenador que troca). `assign_role` faz `escalado_pelo_comercial=None` quando o
  talento muda (inclusive para vazio). Salvar o formulário sem trocar o talento não toca a marca
  (o código só escreve quando `role.talent_id != pre_tid`).
- **Texto**: "inserido pelo comercial" (palavras do dono), junto ao nome do talento.
- **Presença do técnico** (`assign_tech_presence`): nunca recebe a marca; não precisa desligar.

## R8. Título

- O título é montado a partir dos personagens (`role_type="character"`) e o sync descarta segmentos
  reservados (`RESERVED_TITLE_NAMES` inclui "Maquiador"). A vaga nova é `extra`: não entra. O verify
  confere o `title` do evento criado no cenário 12.

## R9. Migration

- Aditiva, três colunas nulas em `event_roles`, `down_revision = "e8b4a1c7d310"` (a cabeça única
  depois do lote de 23/10 — conferido: nenhuma migration a tem como `down_revision`). Sem backfill.

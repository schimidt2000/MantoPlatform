# Plano de implementação: Feature 322 — o casting vê o que está fechando

**Branch**: `322-o-que-o-casting-fecha` | **Data**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/322-o-que-o-casting-fecha/spec.md`

## Resumo

Três colunas novas em `event_roles` e o código que as preenche e mostra:

1. **`perfil_vendido`** — o tipo que o orçamento vendeu, em texto ("Boneco Grande Especial", "Cantor
   · show · com maquiagem"). Nasce em `_compute_performer_caches` (a mesma fonte que já monta a
   conta do teto) e em `produtos.itens_do_teto`, entra na vaga na criação
   (`_create_roles_from_input`) e no vínculo 273 (`aplicar_equipe_do_orcamento`, só onde está
   vazio). A API manda a todo leitor do elenco um `perfil` já pronto para exibir: o gravado ou,
   sem ele, as marcas das flags ("Cantor · com maquiagem").
2. **`criada_pelo_sistema`** — marcada em toda vaga que o sistema cria sozinho: `_ensure_coordinator`,
   `_ensure_sound_technician`, `_create_extra_roles_from_orcamento`, os extras do vínculo 273 e a
   regra nova `garantir_vaga_de_maquiador` (casting_ops), chamada no fim da criação, da edição e do
   vínculo de orçamento.
3. **`escalado_pelo_comercial`** — marcada quando o talento entra pelo formulário do evento
   (pré-escala de personagem e campo Coordenador, na criação e na edição); desligada quando o
   talento muda por `assign_role` (card do casting).

Mais a trava da maquiagem na edição: `update_event_core` ignora `needs_makeup` de quem não é
superadmin (personagem existente mantém o valor; personagem novo nasce sem). A tela trava a caixa e
explica. O card do casting ganha a linha do perfil e as duas marcas discretas.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, `@manto/ui`, `@manto/api-client`

**Armazenamento**: PostgreSQL — produção no Render; verificação contra `manto_local`

**Verificação**: `specs/322-o-que-o-casting-fecha/verify_322.py` contra `manto_local`;
`cd frontend && npm run typecheck`; página do evento e formulário de edição abertos no Browser pane

**Plataforma-alvo**: web interna (staff em desktop e celular)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: N/A — nenhuma consulta nova por vaga; `garantir_vaga_de_maquiador` faz
uma consulta por salvamento

**Restrições**: bundle velho com servidor novo (e vice-versa) não pode quebrar a tela — os três
campos novos do payload nascem opcionais no TS; a coluna nova não pode ser exigida pelo código
antigo (aditiva, nula)

**Escala/escopo**: 1 tabela (3 colunas), 1 migration, 0 endpoints novos, 3 endpoints com
comportamento alterado (`POST /api/events`, `PATCH /api/events/<id>`, `PATCH
/api/events/<id>/orcamento`), 1 payload ampliado (`GET /api/events/<id>`), 2 componentes React
(`CastingSection`, `ElencoBlock`) + `EventEditPage`

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | O perfil sai da MESMA função que monta a conta do teto (`_compute_performer_caches` / `itens_do_teto`), com os mesmos rótulos (`ATOR_SUBTIPO_LABELS`, nomes da tabela de especiais). O critério de "já tem maquiador" é o do selo existente (`"maquiad"` no nome, `agenda_read` e `CastingSection.ehVagaDeMaquiador`). Vínculo reusa a regra "nunca apaga" da 273. |
| II. Padrões de código | type hints e docstring nas funções novas; constantes para os textos; `ruff check` nos tocados |
| III. Camadas / API First | regra nova em `app/calendar/casting_ops.py` (puro); endpoints não mudam de forma, só repassam `is_superadmin` que já recebem |
| IV. Não quebrar o que funciona | migration aditiva e nula; payload só ganha chaves; campos novos opcionais no TS; a trava de maquiagem só age em `update_event_core` (criação e vínculo intocados) |
| V. UI/UX com feedback | a caixa travada leva `title` + texto de ajuda; sem estado novo de carregamento |
| VI. Esteira (Nível 1) | migration + mais de um domínio (calendar, orcamento) + tela → esteira completa |
| VII. Living Spec | spec com 5 histórias e clarificações antes do código |
| VIII. Verify antes do núcleo | `verify_322.py` escrito e vermelho antes do núcleo; 17, 18 e 22 falham no código antigo |
| IX. Dinheiro BRL | o perfil não carrega valor; o teto e a conta continuam só para superadmin |
| X. Mobile-first público | não toca superfície pública; a página do evento é conferida também em 375×812 |
| XI. Framer Motion | sem animação nova |
| XII. Combobox / Maps | não se aplica |
| XIII. RBAC declarado | `PATCH /api/events/<id>`: maquiagem só superadmin (servidor), linha em `docs/01` §4.3; leitura do perfil para todo papel que já lê o elenco |
| XIV. Config / efeito externo | sem env nova; o título do Google não muda (vaga extra nunca entra no título — 239) |
| XV. Texto por superfície | interno operacional: "adicionado pelo sistema", "inserido pelo comercial", "Só o superadmin muda a maquiagem depois que o evento existe." — minúsculas nas marcas (são complemento, não rótulo); nada que o frontend compare |
| Stack | migration à mão, `down_revision = "e8b4a1c7d310"` (head da 310); sem Jinja novo |
| Operação e Deploy | sem `startCommand`; migration aditiva não pede ensaio destrutivo, mas roda `flask db upgrade` no `manto_local` antes do merge |

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/322-o-que-o-casting-fecha/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/evento-elenco.md
├── checklists/requirements.md (+ /speckit-checklist)
├── tasks.md
└── verify_322.py
```

### Código

```text
migrations/versions/c322a7e1b9d4_vaga_perfil_e_origem.py   # 3 colunas em event_roles
app/models.py                                  # EventRole: perfil_vendido, criada_pelo_sistema, escalado_pelo_comercial
app/calendar/routes.py                         # _compute_performer_caches (perfil), _ensure_coordinator/_ensure_sound_technician,
                                               # _create_roles_from_input, _create_extra_roles_from_orcamento, _apply_default_roles, criação
app/orcamento/produtos.py                      # _item/itens_do_teto: perfil das vagas do produto
app/calendar/casting_ops.py                    # garantir_vaga_de_maquiador (novo), assign_role desliga escalado_pelo_comercial
app/calendar/event_ops.py                      # update_event_core: trava de maquiagem, marca da pré-escala, garantir maquiador
app/calendar/orcamento_evento_ops.py           # aplicar_equipe_do_orcamento: perfil + criada_pelo_sistema; vínculo garante maquiador
app/api/agenda_read.py                         # _serialize_role: perfil, criada_pelo_sistema, escalado_pelo_comercial
frontend/apps/internal/src/lib/agenda.ts       # RoleItem (3 campos opcionais)
frontend/apps/internal/src/components/EventDetail/CastingSection.tsx   # linha do perfil + marcas
frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx  # prop maquiagemTravada
frontend/apps/internal/src/pages/EventEditPage.tsx                      # passa a trava para quem não é superadmin
```

**Decisão de estrutura**: a regra "personagem maquiado ⇒ vaga de maquiador" mora em `casting_ops`
(domínio das vagas, já puro) e é chamada pelos três caminhos que podem acender a maquiagem. O perfil
nasce onde a conta do teto nasce, para nunca divergir do que a venda calculou.

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Mexer em `app/calendar/routes.py` (sem índice, legado) | `_compute_performer_caches`, `_ensure_*` e `_create_roles_from_input` moram lá e são a fonte única | mover as funções para `_ops` seria refatoração lateral (CLAUDE.md §8) |

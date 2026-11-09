<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: Mudança no evento avisa o Casting, e o teto do cachê acompanha

**Branch**: `339-evento-mudou-avisa-casting` | **Data**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/339-evento-mudou-avisa-casting/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3+) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

Seis histórias sobre um mesmo eixo: o evento muda e quem escala precisa saber e conseguir agir.
(1) O valor que o Superadmin autoriza acima do teto vira **teto da vaga** em coluna própria, e não
depende mais do cachê da pessoa. (2) A troca de tipo com SHOW **recalcula o teto** pela conta da
criação com o "show" ligado/desligado e **avisa** Casting, Ensaio e Superadmin. (3) O aviso tem
**"Ciente" por pessoa**, numa coluna nova da notificação da 272, separado do "lida" do sino. (4) O
título que **perde** ocorrências de um personagem remove vaga vazia ou marca a vaga ocupada como
sobrando, em evento da plataforma e do Google; o sync deixa de apagar vaga ocupada. (5) Vincular
orçamento novo reescreve os tetos. (6) Remover ou acrescentar vaga ajusta **uma** ocorrência do título
(regra de contagem), e o ensaio futuro acompanha o título — no sistema e no Google.

Abordagem: dois módulos puros novos (`teto_ops.py`, `titulo_ops.py`) com toda a regra; os pontos
existentes (`assign_role`, `add_role`/`delete_role`, `_entrar_em_show`/`_sair_de_show`,
`aplicar_equipe_do_orcamento`, `sync_events`, `update_event_core/basics`) só chamam. Detalhe de cada
decisão em [research.md](./research.md); esquema em [data-model.md](./data-model.md); contratos em
[contracts/api.md](./contracts/api.md); roteiro em [quickstart.md](./quickstart.md).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`
(`apiFetch`/`assetUrl`), `@manto/money`. Nenhuma dependência nova.

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`, `render.yaml`); verificação
contra a cópia `manto_local` (ou `manto_339` do dump noturno, se o `manto_local` estiver preso em
migration de outra feature).

**Verificação**: `specs/339-evento-mudou-avisa-casting/verify_339.py` contra `manto_local` (login só
pela API; escrita por conexão separada; Google e e-mail falsos — `research.md` R9);
`cd frontend && npm run typecheck`; tela aberta no Browser pane (desktop e 375×812)

**Plataforma-alvo**: web — Render; staff em desktop e celular (o Casting usa o celular)

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: o sync não pode ficar visivelmente mais lento: a reconciliação só roda para
evento cujo título mudou (comparação de strings que já existe, `routes.py:2484`), e o push de título de
ensaio só nesse caso.

**Restrições**: Google escrito só depois do commit e fora de trava (`docs/00` §6 item 25);
`service.update_event` não tem trava de ambiente — o verify troca `build`/`load_credentials`; campo
novo do payload opcional no React; texto pelo Princípio XV (superfície interna).

**Escala/escopo**: 5 colunas novas (4 em `event_roles`, 1 em `notifications`), 1 endpoint novo
(`POST /api/notificacoes/<id>/ciente`), 6 portas alteradas (assign, add/delete de vaga, PATCH do
evento e do básico, PATCH do orçamento) + `sync_events`; 1 componente novo (faixa) e ajustes no card
de casting, no item do sino e nos tipos.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Notificações e dedupe da 272 (`emitir`, `resolver_destinatarios`, `UNIQUE(user_id, dedupe_key)`); conta do teto da criação (`_compute_performer_caches`, `snapshot_do_orcamento`, `_duracao_do_evento`, `_chave_cache`, `data_do_evento`); casamento por nome (`orcamento_evento_ops._chave`); `parse_characters`; push de ensaio (`update_ensaio` como molde); faixa no molde de `QuadroDoPedido`; `GoogleFalso` dos verifies 303/306. Nenhuma tabela nova |
| II. Padrões de código | type hints/docstrings Google; constantes no topo (`KINDS_COM_CIENTE`, textos); `ruff check` nos tocados, `ruff format` só em `teto_ops.py`/`titulo_ops.py`/migration |
| III. Camadas / API First | regra em `app/calendar/teto_ops.py` e `titulo_ops.py` (puros, sem `flask.request`; autor entra por parâmetro); `notificacoes_ops` ganha os produtores; endpoints só RBAC + chamada + serialização. Imports tardios de `calendar/routes.py` (`parse_characters`, `_compute_performer_caches`) seguem o padrão já usado por `event_ops` e `orcamento_evento_ops` (`docs/00` §7) |
| IV. Não quebrar o que funciona | migration aditiva; `cache_cap_efetivo` mantém o piso do cachê atual (238); a troca de tipo desfeita (409) não recalcula nem avisa; "Editar" continua mandando no título; mudança deliberada de comportamento: o sync não apaga mais vaga ocupada (FR-023, confirmada no clarify) — registrada no `docs/03`. Consumidores do detalhe do evento conferidos: todas as escritas que devolvem `serialize_event_detail` ganham `avisos` sem quebrar (campo opcional) |
| V. UI/UX com feedback | "Ciente" com `loading` e erro inline; `warnings` das escritas em toast; mutação no `EventHeader` (faixa desmonta no sucesso) |
| VI. Esteira (Nível 1) | specify → clarify → plan → checklist → tasks → analyze → implement → converge |
| VII. Living Spec | spec corrigida antes do plano (FR-027/028: regra de contagem para o nome não sair duas vezes) |
| VIII. Verify antes do núcleo | `verify_339.py` na fase Foundational, falhando primeiro (colunas e funções inexistentes); 2 cenários que devem falhar (12, 21) |
| IX. Dinheiro BRL | `Numeric(10,2)`/`Decimal` em `teto_autorizado`; tela por `formatBRL` |
| X. Mobile-first público | não toca superfície pública; a faixa e o card são conferidos em 375×812 porque o Casting usa o celular |
| XI. Framer Motion | faixa entra sem animação nova (as vizinhas não animam); nada a acrescentar |
| XII. Combobox / Maps | não se aplica |
| XIII. RBAC declarado | `POST /api/notificacoes/<id>/ciente`: login, escopo por dono, 404 alheio; portas alteradas mantêm o gate de hoje; `teto_autorizado*` só para Superadmin no serializer (mesmo corte de `cache_cap`); linhas em `docs/01` §4.3 |
| XIV. Config / efeito externo | nenhuma env nova; escrita no Google sem trava é dívida existente (`config.py:167-169`) — o verify a cobre com `GoogleFalso`, e o push só acontece em ação de usuário ou em título que de fato mudou |
| XV. Texto por superfície | superfície interna: textos do sino, da faixa, do card e dos `warnings` listados em `research.md` (R7) e revisados na tela aberta; glossário: "Cachê", "Escala", "Ensaio", "Vaga", "limite" (o Casting não vê "teto"); nenhum texto comparado pelo frontend |
| Stack | migration à mão, `down_revision = "d323b5a1c0e7"`; sem Jinja novo; sem segredo |
| Operação e Deploy | não toca `startCommand`; migration aditiva com `UPDATE` de preenchimento (sem ensaio destrutivo); colisão de `down_revision` com 328/329/330/332–335/338 no merge (`research.md` R8); publicar fora do horário da equipe |

**Gate (pré-pesquisa)**: aprovado. **Reavaliado após a Phase 1**: aprovado, sem violação a justificar.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/339-evento-mudou-avisa-casting/
├── spec.md              # /speckit-specify + clarify
├── plan.md              # este arquivo
├── research.md          # Phase 0 (R1–R9)
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/api.md     # Phase 1
├── checklists/          # requirements.md (+ /speckit-checklist)
├── tasks.md             # /speckit-tasks
└── verify_339.py        # Princípio VIII — escrito antes do núcleo
```

### Código

```text
migrations/versions/<rev>_teto_autorizado_e_ciente.py   # nova, à mão
app/models.py                                  # EventRole: teto_autorizado*, sobrando_desde; Notification.ciente_em
app/calendar/teto_ops.py                       # NOVO: teto_efetivo, gravar_teto_autorizado, recalcular_tetos_pelo_tipo
app/calendar/titulo_ops.py                     # NOVO: contar_personagens, tirar/acrescentar ocorrência,
                                               #       reconciliar_vagas_pelo_titulo, resolver_sobra,
                                               #       ajustar_titulo_apos_remocao/inclusao, propagar_titulo_aos_ensaios,
                                               #       empurrar_titulos_ao_google
app/calendar/casting_ops.py                    # assign_role (teto autorizado, sobra), add_role/delete_role (título)
app/calendar/event_ops.py                      # _entrar_em_show/_sair_de_show (recálculo, aviso, e-mail do Ensaio);
                                               # update_event_core/basics (reconciliação, ensaios)
app/calendar/orcamento_evento_ops.py           # aplicar_equipe_do_orcamento(reescrever_tetos), set_event_orcamento
app/calendar/routes.py                         # sync_events: reconciliação antes do guard da plataforma; ramo de
                                               # remoção sem apagar vaga ocupada; propagação aos ensaios
app/notificacoes/notificacoes_ops.py           # kinds, KINDS_COM_CIENTE, produtores, marcar_ciente, retenção, serializar
app/api/notificacoes_write.py                  # POST /api/notificacoes/<id>/ciente
app/api/agenda_read.py                         # avisos no detalhe; _serialize_role: sobrando, teto_autorizado*, cache_cap_efetivo
app/api/agenda_write.py                        # warnings em assign/add/delete de vaga
frontend/apps/internal/src/components/EventDetail/AvisosDoEvento.tsx   # NOVO: faixa com "Ciente"
frontend/apps/internal/src/components/EventDetail/EventHeader.tsx      # renderiza a faixa; mutação do Ciente
frontend/apps/internal/src/components/EventDetail/CastingSection.tsx   # marca de sobra; linha do teto autorizado
frontend/apps/internal/src/components/notificacoes/NotificacaoItem.tsx # ícones dos kinds novos
frontend/apps/internal/src/lib/agenda.ts       # tipos opcionais novos
frontend/apps/internal/src/lib/casting.ts      # warnings em add/delete/assign
frontend/apps/internal/src/lib/notificacoes.ts # useMarcarCiente
```

**Decisão de estrutura**: a regra nova não entra em `calendar/routes.py` (3.910 linhas, `docs/00` §7);
ele só ganha as chamadas no `sync_events`. Teto e título ficam em módulos separados porque são
consumidos por portas diferentes (assign × add/delete/sync) e o verify testa cada um sozinho.

## Ordem sugerida (para o `/speckit-tasks`)

1. **Foundational**: migration + models; `verify_339.py` (falhando); `teto_ops.teto_efetivo` e
   `titulo_ops.contar_personagens` (base de todas as histórias).
2. **H1** teto autorizado (assign + serializer + card do Superadmin).
3. **H3** "Ciente" (coluna, endpoint, faixa genérica) — antes da H2/H4, que só produzem avisos.
4. **H2** troca de tipo (recálculo + aviso + e-mail do Ensaio + `warnings`).
5. **H6** título ↔ vagas ↔ ensaio (add/delete + propagação + push).
6. **H4** vaga a mais (reconciliação no sync e no PATCH; ramo do sync sem apagar ocupada; resolução).
7. **H5** vínculo reescreve tetos.
8. Tela aberta, docs (`docs/01`, `02`, `03`, `04`, `05`), converge.

## Rastreamento de complexidade

Sem violação a justificar.

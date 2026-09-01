# Tarefas — Feature 266

**Spec**: `spec.md` · **Plano**: `plan.md` · **Branch**: `266-costuras-funil`

Ordem obedece ao Princípio VIII (verificação escrita antes do núcleo) e às dependências reais do
`plan.md` §2. `[P]` = paralelizável com as irmãs do mesmo bloco.

---

## Bloco 0 — Verificação primeiro

- [ ] **T001** Escrever `specs/266-costuras-funil/verify_266.py` contra `manto_local`, cobrindo os
  casos da spec §Verificação. Login só pela API (padrão `manto_verify_script_padrao`); toda asserção
  de escrita confere **por conexão separada**. O script deve falhar agora — é o que prova que ele
  testa algo.
- [ ] **T002** Rodar `.\scripts\db\run-local.ps1` e confirmar que `verify_266.py` falha nos pontos
  esperados (auto-associação ausente, bloco `formularios` ausente no dashboard, `IntegrityError` ao
  excluir cliente com formulário). Registrar a saída.

## Bloco 1 — Migration

- [ ] **T010** Migration manual: `client_link_source` (`String(20)`, nullable) em `form_responses`.
  `down_revision` = head atual (`flask db heads` — esperado `e08e454c4780`). Sem backfill.
- [ ] **T011** Campo no model (`FormResponse`, junto de `event_link_source`) com comentário `#:`
  documentando os valores `'auto_phone' | 'manual' | None`, no padrão do vizinho.
- [ ] **T012** Ensaio da migration: restaurar o dump mais recente num banco descartável e rodar o
  `startCommand` inteiro (`flask db upgrade && python seed.py`).

## Bloco 2 — Backend: vínculo de cliente

- [ ] **T020** `_attempt_auto_link_client(response) -> str | None` em `formularios_ops.py` (após
  `_attempt_auto_link`, :609). Sem commit, type hints, docstring Google. **Nunca cria `Client`.**
- [ ] **T021** Ligar no `formularios_write.py` dentro do `try` best-effort (:98-104): gravar
  `client_link_source`, chamar `ensure_event_client` **só** se o vínculo de evento também ocorreu,
  ajustar a condição de commit e ampliar a mensagem do `logger.exception`.
- [ ] **T022** `associate_client` grava `client_link_source="manual"`; `dissociate_client` (:246-249)
  zera o campo junto com `client_id`.
- [ ] **T023** **`delete_client` limpa `FormResponse.client_id` e `client_link_source`**
  (`client_ops.py:232-237`) — sem isso a T020 quebra a exclusão de clientes (plan §3.8b).
- [ ] **T024** `client_link_source` em `_response_summary` (`formularios_admin_read.py:36-53`) e no
  tipo `FormResponseSummary` (`lib/formulariosAdmin.ts:4-19`).
- [ ] **T025** `source="formulario"` em `formularios_ops.py:234` **e** a chave no mapa de
  `client_ops.py:200` — *uma só mudança, indivisível*. Atualizar o comentário de `models.py:1823`.
- [ ] **T026** `useAssociateClient` invalida também a chave das métricas de clientes.

⚠️ **T020 não toca `retry_auto_link_pending`.** O filtro dele é `event_link_locked`, que não sabe
nada sobre cliente — estendê-lo religaria a cada ciclo de sync o vínculo que a comercial desfez.

## Bloco 3 — Backend: Home e e-mail

- [ ] **T030** `formularios_ops.py:145`: `date.today()` → `now_sp().date()` (+ import de
  `app.constants`). Não mexer em `dashboard_cutoff` nem `resolve_performance_period`.
- [ ] **T031** Bloco `formularios` em `build_dashboard_summary` (após :538) com
  `show_formularios = show_comercial` e import local de `formularios_ops`; chave no dict de retorno
  (:580-591).
- [ ] **T032** [P] `send_form_response_email` em `email_service.py` com os helpers de layout
  existentes; destinatários = usuários ativos `COMERCIAL`/`SUPERADMIN`.
- [ ] **T033** [P] Disparo por `send_async` no fluxo do POST público, fora do caminho crítico — falha
  de SMTP não altera o 201.

## Bloco 4 — Frontend: deep-link (pré-requisito do bloco 5)

- [ ] **T040** `FormulariosAdminPage.tsx`: `useSearchParams` no lugar do `useState` de `selected`
  (:668); `abrirResposta`/`fecharResposta` com `new URLSearchParams(searchParams)`; ligar em :774 e
  :780. **Guarda de inteiro positivo** no parse (`Number("abc")` → `NaN` → 404 HTML → `JSON.parse`
  estoura). Abrir com push, fechar com replace; fechar limpa o parâmetro **inclusive na exclusão**.

## Bloco 5 — Frontend: travessias

- [ ] **T050** [P] `ComercialSection.tsx`: nome do cliente (:413) vira `<Link>` para `/clientes/:id`;
  mantém `<span>` quando o nome é nulo.
- [ ] **T051** [P] `ComercialSection.tsx`: pré-contrato vira link **nos dois ramos** — o `DataRow`
  (:434, somente-leitura) e uma linha "Ver resposta completa" abaixo do `FormResponsePicker`
  (:447-455, editável). *Mexer só no `DataRow` deixa o comercial sem o link.*
- [ ] **T052** [P] `CastingSection.tsx`: `import { Link }` (novo); link no avatar (:227, com
  `aria-label` e `flex-none`) e no nome (:266), usando `role.talent.id` — **não** `role.talent_id`,
  que não existe. Mesmo tratamento no `PresencaCard` (:173-187).
- [ ] **T053** [P] `ClientDetailPage.tsx`: `form_type_label` (:220) vira link para
  `/formularios?resposta=<id>`; alinhar com o badge "na agenda"/"só formulário".
- [ ] **T054** [P] `ClientDetailPage.tsx`: componente local `AvaliacoesCard` com
  `useClientFeedback({ period: "all", client_id })`. Renderizar **só dentro do bloco de dados
  carregados** (o hook não tem `enabled`; com `NaN` o parâmetro some e o card mostraria as avaliações
  de todas as clientes). Skeleton + erro com "Tentar novamente". Estado vazio: *"nenhuma avaliação
  nos eventos em que ela é a contratante"*.
- [ ] **T055** [P] `OrcamentoResultadoPage.tsx`: 4º botão na barra `actions` (:180) →
  `/events/new?orcamento_id=${entryId}`, variante sólida, `Button asChild` + `Link`.

## Bloco 6 — Frontend: card da Home

- [ ] **T060** `lib/types.ts`: interface dos contadores (alinhada com o `StatusCounts` existente em
  `formulariosAdmin.ts:29-35`, sem descrever o mesmo shape de dois jeitos) + chave em
  `DashboardSummary`.
- [ ] **T061** `DashboardPage.tsx`: `| "formularios"` em `SectionKey`; stat na visão geral; painel
  `SectorPanel` **dentro da grid** (:664, fecha em :882) embrulhado em
  `<div {...propsSecao("formularios")}>`; `!data.formularios &&` na guarda do "Tudo em dia!".
- [ ] **T062** `formulariosAdmin.ts`: `invalidateResponse` (:76) e `useDeleteFormResponse` (:130)
  passam a invalidar `["dashboard"]` (casa por prefixo).

## Bloco 7 — Portões e fechamento

- [ ] **T070** `verify_266.py` passa 100% contra o `manto_local`.
- [ ] **T071** `cd frontend && npm run typecheck` limpo nos **três** apps (não `npx tsc` app a app —
  esquece o portal).
- [ ] **T072** `ruff check` limpo nos arquivos Python tocados.
- [ ] **T073** Conferência na tela (superadmin, desktop **e** mobile) da lista da spec §Verificação,
  incluindo "Ver como CASTING" para o card sumir.
- [ ] **T074** `docs/01` (chave nova no contrato de `GET /api/dashboard` + coluna nova), `docs/02`
  (painel da Home, deep-link `?resposta=`, card de avaliações, vínculos novos), `docs/03` (entrada no
  **topo**, incluindo a nota de que a sugestão de cliente some por design).
- [ ] **T075** Corrigir as três referências mortas achadas na análise: auto-vínculo apontado para
  `app/formularios/routes.py:246` em `docs/00:68` e `docs/04:396`; "4 threads" quando há 7; e as três
  armadilhas de `docs/04` §1 já resolvidas pelas features 246 e 253.

---

## Fora desta lista, por decisão registrada

Deep-link para `/financeiro/comissoes` (decisão 18 → feature 267) · badge de "não lida" (decisão 2) ·
unificação do filtro de avaliações contratante × `EventClient` (decisão 19) · demais relógios UTC.

## Nota de deploy

A branch `265-nfc-revisao-videos` tem 2 commits **ainda não pushados**. A 266 nasceu da `main` e não
os carrega — as duas precisam de merge próprio. Como deploy abre janela de 502
(`manto_deploys_janela_502`), vale subir as duas juntas, fora do horário comercial.

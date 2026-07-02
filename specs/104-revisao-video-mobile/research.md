# Research — Revisão de Vídeo Profissional Mobile-First (104)

Fase 0 do plano. Nenhum `NEEDS CLARIFICATION` restou na spec; abaixo, as decisões técnicas
com alternativas consideradas.

## R1. Como modelar o histórico de versões

**Decision**: novo modelo `ReviewAssetVersion` que guarda **apenas versões anteriores**
(snapshot criado no instante da substituição). `ReviewAsset` permanece a fonte da versão
atual, com os campos existentes (`file_path`, `original_name`, `version`, `expires_at`,
`file_removed`) intocados.

**Rationale**:
- Zero impacto nos fluxos existentes: upload, expiração (`cleanup.py`), finalização e
  templates continuam lendo `ReviewAsset` como hoje (Princípio IV — não quebrar).
- Nenhum backfill de arquivos na migration: materiais existentes simplesmente começam a
  acumular histórico a partir da próxima substituição (o passado deles já foi apagado pela
  lógica antiga — irrecuperável de qualquer forma).
- O snapshot é criado num ponto único (`replace_asset`), fácil de manter como fonte de verdade.

**Alternatives considered**:
- *Normalizar tudo em `ReviewAssetVersion` (inclusive a atual)*: mais "puro", porém exigiria
  reescrever cleanup, finalize, templates de card e backfill de todos os assets — muito mais
  superfície de quebra para o mesmo resultado funcional. Rejeitado (YAGNI).
- *JSON de histórico dentro do asset*: sem integridade referencial, ruim para consultar autor
  (FK users) e para o cleanup varrer expirados. Rejeitado.

## R2. Como vincular comentário à versão

**Decision**: coluna inteira `version_number` em `review_comments`, carimbada com
`asset.version` no INSERT. Backfill dos comentários existentes com a versão atual do seu
material. A listagem principal filtra `version_number == asset.version`; a visualização de
versão antiga filtra pelo número dela.

**Rationale**: um inteiro simples cobre os dois lados (asset atual e snapshots) sem FK dupla;
o backfill é um `UPDATE ... FROM` trivial; satisfaz FR-013/FR-017.

**Alternatives considered**: FK para `review_asset_versions` — impossível para a versão
atual (que não tem linha lá) e obrigaria a criar linhas para todos os assets existentes.
Rejeitado.

## R3. Registro de conclusão (quem/quando)

**Decision**: adicionar `resolved_by` (FK `users.id`, nullable) e `resolved_at` (DateTime,
nullable) em `review_comments`, mantendo o bool `resolved` como fonte do estado. Concluir
preenche os três; reabrir limpa. JSON do comentário passa a incluir `resolved_by_name` e
`resolved_at`.

**Rationale**: aditivo e retrocompatível (comentários já resolvidos ficam com autor/data
nulos e exibem só o badge "concluído"); espelha o par `finalized_at`/`file_removed` já usado
no módulo.

**Alternatives considered**: tabela de eventos de auditoria por comentário — sobre-engenharia
para a necessidade ("quem concluiu e quando"). Rejeitado.

## R4. Permissões (FR-010 / FR-011)

**Decision**:
- Concluir/reabrir: criador do espaço, super admin **ou autor do comentário**
  (`_can_resolve(comment)`).
- Excluir: **somente** autor do comentário ou super admin (`_can_delete(comment)`) — o
  criador do espaço perde o poder de excluir comentários alheios (hoje ele tem); em troca,
  conclui.

**Rationale**: exatamente o processo pedido — a Erika (criadora) conclui em vez de excluir;
exclusão vira correção de erro do próprio autor. Mantém `_can_view` como guarda de leitura.

## R5. Visualização de versão antiga

**Decision**: reusar a rota `GET /revisao/<space_id>/asset/<asset_id>` com query param
`?v=N`. Sem `v` (ou `v` == versão atual) → tela normal. Com `v` antigo → busca o snapshot,
renderiza player/imagem/PDF da versão (se `file_removed=False`), oculta o composer e mostra
banner "Você está vendo a versão N de M — voltar para a atual".

**Rationale**: uma única tela/template para os dois modos evita duplicar o visualizador
(Princípio I); URL compartilhável; `list_comments` ganha o mesmo param `?v=`.

**Alternatives considered**: rota dedicada `/versao/<n>` — template quase idêntico duplicado
ou mais um branch de include; sem ganho. Rejeitado.

## R6. Expiração e limpeza de versões antigas

**Decision**: o snapshot herda o `expires_at` que a versão tinha quando era atual (não
renova). `cleanup_expired_review_files()` ganha uma segunda varredura sobre
`review_asset_versions` (mesmo padrão: `delete_file` + `file_removed=True`). `finalize_asset`
e `delete_asset`/`delete_space` também removem arquivos de snapshots não removidos.

**Rationale**: mantém a promessa da feature 090 (nenhum arquivo vive mais que seu prazo);
sem prazo novo, o custo de armazenamento fica igual ao de hoje no pior caso (o arquivo já
existiria se não tivesse sido substituído).

## R7. Layout mobile-first estilo Vimeo

**Decision**: reescrever `asset.html` com estrutura em coluna única (base mobile):

1. Player full-width no topo com `position: sticky; top: 0` (vídeo continua visível ao rolar
   comentários) + timeline de marcadores logo abaixo dele.
2. Cabeçalho compacto do material: nome, badge de versão (abre o histórico), badge de
   expiração/finalizado.
3. Lista de comentários com **abas** "Pendentes (n)" / "Concluídos (m)" — concluídos
   recolhidos por padrão (FR-008); cada card: autor, data, chip de time code (alvo ≥ 44px),
   corpo, e ações (concluir/reabrir; excluir só quando permitido, com confirmação).
4. **Composer fixo no rodapé** (`position: sticky; bottom: 0`): chip com o time code
   congelado no `focus` do textarea + botão enviar com estado de loading. `focus` captura
   `player.currentTime` e pausa o vídeo (padrão Vimeo), evitando que o tempo "escorra"
   enquanto digita.
5. Desktop (`@media (min-width: 900px)`): grid de 2 colunas (player 1fr + painel 400px),
   composer volta a viver no painel.

**Rationale**: `sticky` bottom convive melhor com teclado virtual do que `fixed` (iOS Safari
recalcula o viewport visual); abas resolvem o agrupamento pendente/concluído sem esconder
informação; tokens de `style.css` (`--accent #544596`, `--panel`, `--line`, `--r-md`)
garantem a identidade visual (FR-003).

**Alternatives considered**: bottom-sheet de comentários sobreposto ao player (app-like) —
mais JS, mais estados quebráveis em navegador móvel, sem framework. Rejeitado a favor de
fluxo de documento com sticky.

## R8. Migration manual

**Decision**: migration escrita à mão (`flask db migrate` está quebrado por drift):
`a3b4c5d6e7f8_review_versions_resolution.py`, `down_revision = "e7b8c9d0f1a2"` (head atual).
Conteúdo: `create_table review_asset_versions`; `add_column` em `review_comments`
(`version_number` int NOT NULL server_default "1", `resolved_by` int FK nullable,
`resolved_at` datetime nullable); backfill `UPDATE review_comments SET version_number =
(SELECT version FROM review_assets WHERE ...)`; índices em `asset_id` da nova tabela.

**Rationale**: prática registrada do projeto (memória: autogenerate quebrado). Backfill em
SQL puro roda igual em SQLite e Postgres.

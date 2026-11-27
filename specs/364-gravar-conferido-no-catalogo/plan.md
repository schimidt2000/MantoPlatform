# Plano de implementação: Gravar no catálogo o conferido (364)

**Branch**: `364-gravar-conferido-no-catalogo` | **Data**: 2026-11-27 | **Spec**: [spec.md](./spec.md)

## Resumo

Núcleo novo `app/admin/catalog_gravacao_ops.py` lê `catalog_conferencias` conferidas e ainda na fila e
escreve no catálogo: `CatalogCharacter` por personagem "criar" (foto recortada com Pillow a partir do
arquivo em disco, salva por `storage.save_bytes`) e `figurino_sheet_id` no avulso com ficha. Anda em
lotes, por `POST …/conferencia/gravar`, que a fila chama em laço. Antes do primeiro lote aplica os ajustes
das observações (`app/admin/dados/ajustes_conferencia.json`).

## Contexto técnico

**Dependências**: as da casa; Pillow já é dependência (`app/imaging.py`, `app/storage.py`).

**Armazenamento**: duas colunas novas — `catalog_conferencias.gravado_em` e
`catalog_conferencia_personagens.catalog_character_id` (FK `catalog_characters`, `SET NULL`). Fotos novas
em `catalog_photos/` no disco do backend, servidas por `/catalogo/midia/`.

**Restrições**: o recorte lê o arquivo do disco, então só roda dentro do backend (memória "CLI local não
migra arquivo"); requisição curta (lote de 10 itens) para não bater no timeout do gunicorn; nunca dois
lotes ao mesmo tempo (`pg_advisory_xact_lock`); commit por item.

**Escala**: ~224 temas e duplas, ~904 personagens, 25 avulsos com ficha; 2 rotas; 1 bloco na fila.

## Constitution Check

| Princípio | Como o plano cumpre |
|---|---|
| I. Reutilizar | `filtro_da_fila` (360), `unique_character_slug`, `_rewrite_public_url`, `save_bytes`, `caminho_local`, `catalog_ops.set_item_figurino`; gate de `admin_catalogo_read` |
| II. Padrões | type hints, docstrings, funções curtas; `ruff` nos tocados |
| III. Camadas | `catalog_gravacao_ops.py` puro; rotas nos módulos `admin_catalogo_conferencia_{read,write}.py` já registrados |
| IV. Não quebrar | só acrescenta personagem a item SEM elenco e ficha a item SEM ficha (a própria regra da fila garante); nada é apagado; FK nova com `SET NULL` e sem backref |
| V. UI | botão com `loading`, andamento "N de M", falhas listadas |
| VI/VII/VIII | esteira, spec antes do código, verify na fase Foundational |
| XI | bloco entra com a transição já usada na fila; sem lista animada nova |
| XIII | SUPERADMIN nas duas rotas; linha em `docs/01` §4.3 |
| XIV | sem env nova; sem serviço externo |
| XV | textos: "Gravar no catálogo", "Gravando… N de M itens", "Gravação concluída: …" |
| Stack/Deploy | migration à mão `f364a1b2c3d4` sobre `f360a1b2c3d4`; aditiva; backend + frontend |

## Decisões

1. **Cria `CatalogCharacter` direto, sem `create_character`**: aquela função recebe upload do Flask e faz
   commit por personagem; aqui o item inteiro é uma transação (savepoint), para falha desfazer o item.
2. **Idempotência por vínculo**: `catalog_character_id` no personagem proposto e `gravado_em` no item.
3. **Ordem de segurança**: item só é gravado se ainda passa em `filtro_da_fila` (sem elenco, sem ficha).
4. **Ajustes por `(item_id, nome)`**, não por id: os ids da conferência diferem entre espelho e produção
   só para o que foi criado depois do dump. Ajuste com `criar: true` acrescenta o personagem (item 898) e
   muda o tipo para `tema`.
5. **Arquivo ausente → sem foto**, com `logger.warning`; nunca falha o lote.

## Rastreamento de complexidade

| Violação | Por quê | Alternativa rejeitada |
|---|---|---|
| Verify contra `manto_364`, não `manto_local` | precisa das tabelas e dos dados da conferência (produção de 26/11) | `manto_local` está em outubro e é compartilhado |
| Ajustes em arquivo versionado | 32 recortes definidos por leitura de foto, fora do sistema | tela de recorte: é a feature que o dono dispensou |

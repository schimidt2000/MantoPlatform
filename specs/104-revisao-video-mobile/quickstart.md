# Quickstart — Revisão 104

## Rodar (sempre contra a cópia local Postgres)

```powershell
# 1. Garantir cópia local atualizada (opcional, se estiver velha)
.\scripts\db\refresh-local-db.ps1

# 2. Aplicar a migration nova na cópia local
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
python -m flask db upgrade

# 3. Rodar o app contra a cópia local
.\scripts\db\run-local.ps1
```

## Roteiro de verificação manual

Usuários: um criador (MARKETING/SUPERADMIN) e um revisor comum.

### US1 — Mobile (DevTools, viewport 390×844)

1. Abrir `/revisao/<id>/asset/<id>` de um vídeo → player no topo, largura total, sem scroll
   horizontal; lista de comentários abaixo; composer fixo visível.
2. Dar play, focar o campo de comentário aos ~0:05 → vídeo pausa e chip mostra "0:05";
   digitar por 10s (o chip NÃO muda), enviar → comentário aparece com âncora 0:05 e marcador
   na timeline.
3. Tocar no time code de um comentário → player salta para o instante.
4. Alargar para desktop (≥ 900px) → layout 2 colunas, mesmas funções.

### US2 — Conclusão

1. Como revisor: criar 2 comentários. Como criador: concluir 1 → some da aba "Pendentes",
   aparece em "Concluídos (1)" com "Concluído por <nome> em <data>".
2. Como revisor: ver o comentário concluído (autor/data da conclusão visíveis); NÃO ver
   botão excluir em comentário alheio; ver "concluir" no próprio.
3. Reabrir o comentário (criador) → volta a pendente, sem autor/data de conclusão.
4. Excluir: só autor do comentário ou superadmin, com confirmação.

### US3 — Versões

1. Como criador: substituir o arquivo do vídeo → material vira v2; comentários da v1 somem
   da tela principal.
2. Abrir o histórico (badge de versão) → v1 listada com data/autor; abrir v1 → arquivo da v1
   reproduz, comentários da v1 visíveis, banner "versão antiga", sem composer.
3. Comentar na v2 → aparece só na v2.
4. Conferir no banco: `review_asset_versions` tem a linha da v1 com `expires_at` herdado.

### Regressão (feature 090)

- Finalizar material → arquivo atual E arquivos de versões antigas removidos; registros e
  comentários permanecem.
- Rodar cleanup manualmente num shell Flask:
  `from app.revisao.cleanup import cleanup_expired_review_files; cleanup_expired_review_files()`
  → versões antigas vencidas têm arquivo removido, entrada do histórico permanece.

## Portões de qualidade

```powershell
mypy app/
ruff format app/ --check
ruff check app/
```

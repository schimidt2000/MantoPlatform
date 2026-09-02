# Plano — Feature 270: miniaturas por largura (catálogo público + Banco de Talentos)

**Spec**: `spec.md` · **Branch**: `270-miniaturas-catalogo` · **Migration**: nenhuma
**Pré-requisito em produção**: `flask compress-images --execute` já rodou (01/09/2026) — as
variantes nascem de originais de ≤1200px, não de 4 MB.

## Resumo técnico

Generalizar o motor de `app/catalogo/og_ops.py` por uma `Receita` (tentativas × qualidade, teto de
bytes, redimensionar pela largura ou pelo lado maior) e expor duas rotas de variante por caminho —
uma pública para o catálogo, uma com login para fotos de talento. No frontend, `assetUrl()` ganha
`{ largura }` e um irmão `assetSrcSet()`; três cards e a tira de miniaturas passam a pedir a
variante certa. Um comando `flask warm-thumbnails` gera tudo em lote depois do deploy.

## Backend

| Onde | O quê |
|---|---|
| `app/catalogo/og_ops.py` | `Receita` (NamedTuple) · `RECEITA_OG` (chave `"1"`, preserva o cache atual) · `receita_variante(largura)` · `LARGURAS_PERMITIDAS = (128, 320, 480, 640)` · `cache_digest/find_cached/build_thumbnail/cached_thumbnail` recebem `receita` (default OG → API antiga intacta) · `_redimensionar` por largura ou lado maior · `pastas_da_variante(url)` (só `/catalogo/midia/<arq>` e `/uploads/talent_photos/<arq>`; URL absoluta e `talent_docs` ficam de fora) · `resolve_variante(url, largura, uploads)` · `variante_em_cache` (consulta sem gerar, para o CLI) |
| `app/catalogo/routes.py` | `GET /catalogo/midia/t/<int:largura>/<filename>` declarada ANTES de `midia` · 404 fora da allowlist ou arquivo ausente (nada gravado) · `Cache-Control: public, max-age=31536000, immutable` |
| `app/__init__.py` | `GET /uploads/t/<int:largura>/<path:filename>` (`login_required`; só `talent_photos/<arq>`; passa por `_can_read_upload`) · `uploaded_file` carimba `Cache-Control: private, max-age=31536000, immutable` **só** quando a subpasta é `talent_photos` (`_subpasta_do_upload`) · `send_file` importado |
| `app/cli.py` | `flask warm-thumbnails`: todas as fotos de item a 128; capas de item e fotos de personagem a 320/480/640; fotos de rosto de talento a 320/480/640; idempotente; relata geradas/existentes/sem variante (URL externa)/falhas |

Cache em disco: `uploads/catalog_thumbs/<largura>/{digest}_{w}x{h}.jpg` e
`uploads/talent_thumbs/<largura>/…`, digest = `md5("t<largura>|<url>")`. Pasta por largura para que
aposentar um tamanho seja um `rm -r`.

## Frontend

| Onde | O quê |
|---|---|
| `packages/api-client/src/client.ts` | `assetUrl(path, { largura })` · `assetSrcSet(path, [320, 640])` · `comVariante()` com a MESMA regra de prefixos de `pastas_da_variante` · tipos `LarguraMiniatura`, `AssetUrlOptions` |
| `apps/public/.../ProductGallery.tsx` | tira de miniaturas → `assetUrl(url, { largura: 128 })`; palco continua no original |
| `apps/public/.../ProductCard.tsx` | `src` 640 + `srcSet` 320/480/640 + `sizes` da grade real (`SIZES_GRADE` / `SIZES_CATEGORIA`; no celular `calc(50vw - 32px)`) |
| `apps/public/.../CharacterCard.tsx` | idem, grade do `CharacterGrid` |
| `apps/internal/.../TalentMosaic.tsx` | idem, grade de 2–6 colunas, `loading="lazy"` |

Nenhum proxy muda: `/catalogo/midia` e `/uploads` já são prefixos repassados pelo `frontend/server.js`
e pelos `vite.config.ts` — as rotas novas vivem debaixo deles de propósito (gap de proxy por app,
feature 182).

## Ordem de execução

1. `og_ops.py` (motor) → 2. rotas (catálogo, `/uploads`) → 3. CLI → 4. `verify_270.py` 10/10 →
5. api-client + componentes → 6. `npm run typecheck` nos três apps → 7. conferência na tela
(aba de rede: tira baixa 8× ~5 KB; grade pede 320 no celular e 640 no desktop; grade de talentos
não refaz requisição de foto na 2ª abertura) → 8. docs 01/02/03.

## Pós-deploy (operação)

```
ssh -i ~/.ssh/render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com
cd /opt/render/project/src && FLASK_ENV=development PYTHONPATH=$PWD .venv/bin/flask warm-thumbnails
```
~2.700 fotos de item a 128 + ~680 capas/personagens a 320/480/640 + ~260 rostos a 320/480/640 ≈
5.500 arquivos pequenos; roda em poucos minutos e é idempotente.

## Riscos e mitigação

- **Rota de variante como gerador de trabalho arbitrário** → allowlist fechada de larguras; 404
  sem gravar nada para largura ou arquivo inválidos (verify cenários 3 e 4).
- **Duas requisições gerando a mesma variante** → `os.replace` atômico do motor; verify cenário 6
  com 8 threads.
- **Cache `public` em recurso com login** → fotos de talento saem com `private`; o resto de
  `/uploads` não ganha cache longo (verify cenário 8).
- **Digest colidir entre OG e variante** → a chave da receita entra no digest (`"1|url"` vs
  `"t128|url"`), e o cache OG existente em produção continua válido (cenário 5).
- **Werkzeug escolher `<path:filename>` para `t/128/x.jpg`** → rota específica declarada antes, e o
  verify prova que `/t/128/` cai na rota certa.

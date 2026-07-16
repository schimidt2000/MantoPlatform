# Implementation Plan: Catálogo Público de Personagens (133)

**Branch**: `133-catalogo-publico` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)

## Summary

Novo blueprint público `catalogo_bp` (sem login) + 3 tabelas novas (`CatalogCategory`,
`CatalogItem`, `CatalogItemImage`) + um comando CLI de importação (`flask
import-wordpress-catalog`) que lê o CSV do WooCommerce, baixa e comprime as fotos
(reaproveitando `app.storage.save_file`, que já redimensiona/comprime imagens), re-hospeda
tudo dentro do próprio sistema e reporta fotos que continuem pesadas. A página pública tem
identidade visual própria (não usa `style.css`/`base.html` do sistema), busca client-side
por nome/categoria/tag, alternância "ver tudo"/seções, e cada item tem página própria com
metatags Open Graph para gerar miniatura ao compartilhar no WhatsApp.

## Technical Context

**Stack**: Flask + SQLAlchemy + Jinja2 + JS vanilla (o existente); `Pillow` (já é
dependência, usado por `app.storage._compress_image`) e `requests` (já instalado
transitivamente — passa a ser dependência direta, adicionada ao `requirements.txt`).

**Storage**: 3 tabelas novas, aditivas (nenhuma tabela existente é alterada):

- `catalog_categories` — `id`, `name` (único), `slug`.
- `catalog_items` — `id`, `wp_product_id` (int, único, nullable — chave de dedup para
  reimportação, FR-005), `name`, `slug` (único), `short_description_html` (Text,
  nullable), `tags` (Text, JSON — lista de strings, só para busca), `is_active` (Boolean,
  default True — não editável nesta feature, mas evita reescrever schema quando a tela de
  edição futura chegar), `imported_at`.
- `catalog_item_images` — `id`, `item_id` (FK), `url` (a URL pública servida pelo próprio
  sistema), `original_url` (a URL original do WordPress, guardada para rastreabilidade),
  `position` (ordem original do CSV — posição 0 é a capa/imagem usada no Open Graph),
  `file_size_bytes` (tamanho final após compressão — alimenta o relatório de "imagens
  pesadas", FR-004).
- `catalog_item_categories` — tabela de associação pura (`item_id`, `category_id`), mesmo
  padrão já usado por `user_roles` em `app/models.py` (m2m sem atributos extras).

**Arquivos**:

- `migrations/versions/<hash>_catalogo.py` — cria as 4 tabelas.
- `app/models.py` — `CatalogCategory`, `CatalogItem` (`categories` via
  `db.relationship(..., secondary=catalog_item_categories)`, `images` via
  `db.relationship("CatalogItemImage", ..., order_by="CatalogItemImage.position")`),
  `CatalogItemImage`.
- `app/catalogo/__init__.py`, `app/catalogo/importer.py` — `run_import(csv_path,
  limit=0, echo=None) -> dict`:
  - Lê o CSV com `csv.DictReader` (`encoding="utf-8-sig"`, cuida do BOM confirmado no
    arquivo real).
  - Filtra por `Publicado == "1"` (resolve genericamente o único rascunho descartável do
    CSV real, sem precisar de uma regra hardcoded pelo nome do produto) e por nome +
    (categoria OU imagem) presentes (FR-006).
  - Pula produtos cujo `wp_product_id` (coluna `ID` do CSV) já foi importado antes
    (FR-005 — reimportação segura).
  - Gera slug a partir do nome (`strip_accents_lower` já existente em `app/utils.py` +
    hifenização); em colisão de slug entre produtos DIFERENTES (ex.: os 2 produtos reais
    chamados "Round 6"), desambigua com o `wp_product_id` no sufixo — resolve o Edge Case
    do spec sem tratar nomes repetidos como duplicata.
  - Categorias: `get_or_create` por nome em `CatalogCategory`.
  - Descrição: remove artefatos de escape (`\n` literal do export do WooCommerce, visto
    no CSV real) mantendo o HTML simples (`<b>`, `<span>`) — renderizado com `|safe` no
    template (mesmo nível de confiança de conteúdo já usado para `event.description`,
    conteúdo nosso, não enviado por terceiros).
  - Imagens: baixa cada URL (`requests.get`, timeout 30s, tolera falha de uma imagem sem
    abortar o item — mesma filosofia de `app/drive_migration.py::run_drive_migration`),
    embrulha em `werkzeug.datastructures.FileStorage` e chama `save_file(fs,
    "catalog_photos")` — reaproveita a compressão já existente (`_MAX_PX=1200`,
    `_QUALITY=85`), sem inventar um pipeline de imagem novo (FR-003).
  - Em modo local (`USE_S3=false`), a URL devolvida por `save_file` é
    `/uploads/catalog_photos/<arquivo>` (rota autenticada) — reescreve para
    `/catalogo/midia/<arquivo>` antes de salvar no banco, já que o catálogo é público
    (ver Decisão 2). Em modo S3, a URL já é absoluta e pública — usada como está.
  - Mede o tamanho final do arquivo salvo (`os.path.getsize` em modo local;
    `requests.head(...)` + `Content-Length` em modo S3, já que ali a URL é publicamente
    alcançável independente do processo Flask) e registra em `file_size_bytes`; acima de
    300KB entra no relatório de "imagens pesadas" (FR-004) — sem recomprimir com um
    segundo pipeline mais agressivo (fica para revisão manual, ver Decisão 3).
  - Item sem nenhuma imagem baixada com sucesso é descartado da importação (Edge Case do
    spec) e contabilizado no relatório.
  - Retorna um dicionário de contagens (processados, importados, pulados por tipo,
    imagens baixadas/falhas/pesadas) — mesmo formato de retorno de `run_drive_migration`.
- `app/cli.py` — `flask import-wordpress-catalog <path> [--limit N]`, mesmo padrão de
  `migrate-drive-to-volume` (chama `run_import`, imprime relatório final).
- `requirements.txt` — adiciona `requests` como dependência direta (hoje só transitiva).
- `app/catalogo/routes.py` — `catalogo_bp = Blueprint("catalogo", __name__,
  url_prefix="/catalogo")`, **sem `@login_required` em nenhuma rota**:
  - `GET /catalogo/` — lista todos os `CatalogItem` ativos com categorias/capa
    pré-carregadas; renderiza `catalogo/index.html`.
  - `GET /catalogo/<slug>` — item por slug; 404 amigável (`catalogo/invalid.html`, mesmo
    espírito de `feedback/invalid.html`) se não existir/inativo; renderiza
    `catalogo/detail.html` com metatags Open Graph (`og:title`, `og:description`
    truncada sem HTML, `og:image` **absoluta** via `request.url_root` + capa,
    `og:url`, `twitter:card=summary_large_image`).
  - `GET /catalogo/midia/<path:filename>` — serve arquivos só da subpasta
    `catalog_photos` (`send_from_directory`, que já previne path traversal) — rota
    pública dedicada, nunca reaproveita nem afrouxa a rota `/uploads` existente (login-
    obrigatório, serve contratos/documentos — ver Decisão 2).
- `app/templates/catalogo/_head_shared.html` — bloco `<style>` compartilhado (paleta,
  tipografia, tokens) incluído por `index.html` e `detail.html`, evitando duplicar a
  declaração de fontes/paleta entre as duas páginas (Princípio I).
- `app/templates/catalogo/index.html` — página HTML própria (não estende `base.html` do
  sistema — FR-013): busca (JS client-side, normaliza acento/caixa, casa contra nome +
  tags + categorias via `data-search`), abas de seção ("Todos" + cada categoria, ordenadas
  por quantidade de itens), grade de cards (capa, nome, chips de categoria), estado vazio
  quando busca/seção não bate com nada (FR-014).
- `app/templates/catalogo/detail.html` — galeria completa, descrição, chips de categoria,
  botão "copiar link" (mesma técnica de `copiar()` já usada em `event_detail.html`,
  inline nesta página por ser standalone).
- `app/templates/catalogo/invalid.html` — item não encontrado, mesmo padrão de
  `feedback/invalid.html`.
- `app/__init__.py` — `app.register_blueprint(catalogo_bp)`.
- `app/templates/base.html` — link "📖 Catálogo" no grupo Comercial da sidebar,
  `target="_blank"` para `/catalogo/` (achado rápido pela equipe; não faz parte da
  navegação pública).

**Testing**: verificação funcional vs `manto_local` — importar um CSV de amostra (poucas
linhas, reaproveitando a estrutura real) e conferir: itens válidos criados, rascunho
descartado, reimportação não duplica, produtos de nome repetido viram itens distintos com
slugs diferentes, imagens baixadas/comprimidas com URL pública funcional (sem login),
relatório de imagens pesadas aparece quando esperado; página `/catalogo/` acessível sem
sessão, busca por tag encontra item, alternância seção/tudo funciona, estado vazio
correto; página de item tem metatags Open Graph com URL absoluta de imagem; rota de mídia
não serve arquivo fora de `catalog_photos`; cabeçalho `X-Robots-Tag: noindex` presente
(automático, sem código extra — ver Decisão 1).

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Compressão de imagem reaproveita `app.storage.save_file` (nenhum pipeline de imagem novo). Download tolerante a falha por item copia o padrão já testado de `app/drive_migration.py`. Slug usa `strip_accents_lower` já existente. CLI segue o padrão de `migrate-drive-to-volume`/`import-kommo-clients`. Página de erro segue o padrão de `feedback/invalid.html`. |
| II. Segurança | ✅ Nova rota pública de mídia (`/catalogo/midia/`) é estritamente escopada à subpasta `catalog_photos` — a rota `/uploads` existente (que serve contratos, documentos de talento, comprovantes) **não é tocada nem afrouxada** (Decisão 2). |
| IV. Não quebrar | ✅ Feature 100% aditiva — 3 tabelas novas, 1 blueprint novo, 1 link a mais na sidebar. Nenhuma rota/tabela existente muda. `X-Robots-Tag: noindex` já é `setdefault` global (feature 127) — o catálogo herda automaticamente, sem precisar de código novo, e sem risco de alguém remover isso por engano depois (FR-008 cumprido "de graça"). |
| V. UI/UX | ✅ Estado vazio explícito na busca/seção (FR-014). Botão "copiar link" com feedback visual (mesma técnica já validada). Import reporta erros por item sem abortar o lote inteiro. |
| VI. Planejar | ✅ Este plano segue um brainstorm dedicado com o usuário (não pulou direto pra spec) e uma análise real do CSV (451 linhas, 38 categorias, cobertura de campos) antes de qualquer decisão de modelagem. |
| VIII. Mobile-first | ✅ Aplica-se diretamente — é a superfície pública mais visível desta sessão (cliente final navega pelo celular, inclusive vinda de um link do WhatsApp). Layout desenhado mobile-first, com o mesmo cuidado dado a `feedback/public.html`. |

**Gate: PASS.**

## Decisões

1. **Nenhum código novo para bloquear indexação**: a feature 127 já aplica
   `X-Robots-Tag: noindex, nofollow, noarchive` globalmente via `setdefault` em
   `_security_headers` (`app/__init__.py`) — o catálogo herda isso automaticamente por
   ser só mais uma rota Flask do mesmo app. Documentado aqui para não ser "redescoberto"
   como pendência numa revisão futura.
2. **Rota de mídia pública dedicada, nunca a rota `/uploads` existente**: `/uploads/
   <path:filename>` exige login porque serve contratos, documentos de identidade e
   comprovantes de pagamento — remover esse `@login_required` (ou reaproveitar a rota
   para o catálogo) exporia esses arquivos. Em vez disso, `/catalogo/midia/<filename>` é
   uma rota nova, pública, mas hardcoded para servir só da subpasta `catalog_photos` — o
   único jeito de expor uma foto de catálogo por essa rota é ela já estar salva ali pelo
   próprio importador.
3. **"Leve o bastante" é medido e reportado, não forçado com uma segunda compressão mais
   agressiva**: a compressão padrão de `save_file` (1200px, JPEG q85) já cobre a maioria
   dos casos; imagens que ainda ficarem pesadas entram num relatório para decisão humana
   (recortar, reduzir mais, ou aceitar) em vez de arriscar degradar demais a qualidade
   visual de um catálogo cujo objetivo é justamente impressionar visualmente a cliente.
4. **Filtro por `Publicado == "1"`, não por nome específico**: resolve o único rascunho
   descartável do CSV real de forma genérica (funciona em qualquer reimportação futura),
   em vez de uma regra hardcoded ("descartar produto chamado X") que quebraria na
   primeira mudança de conteúdo.
5. **Página pública com HTML/CSS próprios, sem estender `base.html`**: pedido explícito
   do usuário (FR-013) — mesmo padrão já usado em `feedback/public.html` (página
   standalone, própria tipografia/paleta), aqui levado a um nível de acabamento mais
   editorial por ser a vitrine que a cliente final vê.
6. **Sem tela de edição/criação de itens, sem integração com orçamento/estoque nesta
   feature**: explicitamente adiado pelo próprio usuário ("futuramente") — a modelagem
   de dados (item com id/slug estável, galeria em tabela própria) já deixa espaço para
   essas adições sem precisar reescrever o schema, mas nenhuma interface é construída
   agora (evita escopo inflar além do que foi pedido).

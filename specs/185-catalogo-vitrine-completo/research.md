# Research: Catálogo Vitrine Completo

## 1. Suporte a vídeo — como reproduzir Drive/MP4/Vimeo com controle customizado

**Decision**: Duas estratégias por tipo de URL, decididas na classificação da URL (`classify_video_url`):
- **MP4 direto** e **Google Drive** (normalizado para `https://drive.google.com/uc?export=download&id=<ID>`) → elemento `<video>` nativo, com controles 100% customizados (mute toggle, fullscreen via `element.requestFullscreen()`), atendendo FR-006 por completo.
- **Vimeo** → `<iframe>` com o player oficial da Vimeo, usando os parâmetros nativos de embed (`autoplay=1&muted=1&loop=1&background=1&playsinline=1`), que já cobrem autoplay/mute/loop/playsinline sem JS adicional. O botão de som/fullscreen customizado da vitrine não se aplica a este caso — o player da própria Vimeo expõe os controles equivalentes ao interagir com o iframe.

**Rationale**: Vimeo não expõe URL de arquivo de vídeo bruto sem plano pago/API adicional; envolver o Vimeo Player SDK (JS, comunicação via `postMessage`) só para replicar controles que o próprio embed da Vimeo já oferece nativamente via query params é complexidade não justificada (Governança da constituição, YAGNI). Google Drive não tem player embutido com os parâmetros de autoplay/mute/loop que o requisito pede — por isso vira `<video src>` direto como o MP4.

**Alternatives considered**:
- Vimeo Player SDK (`@vimeo/player`) para unificar 100% dos controles customizados em todos os provedores — rejeitado por complexidade extra (nova dependência, comunicação assíncrona por postMessage) sem ganho perceptível para o cliente final.
- Proxy do vídeo do Drive pelo backend (baixar e re-servir) — rejeitado explicitamente pelo pedido do usuário ("não sobrecarregar o armazenamento do servidor") e pela FR-002 (mídia via streaming/link externo).

**Known limitation (documentar, não bloqueia)**: Google Drive pode servir uma página de confirmação/rate-limit para arquivos grandes ou com muitos acessos simultâneos — fora do controle do sistema. Vídeos de produção recomendados via Vimeo ou CDN; Drive é conveniência para prévias rápidas.

## 2. Validação de URL de vídeo

**Decision**: Função pura `classify_video_url(url: str) -> Literal["mp4", "drive", "vimeo"] | None` em `app/catalogo/media.py` (novo módulo pequeno, sem `request`/`render_template`), usada tanto pelo `catalog_ops`/novo `catalog_character_ops` quanto por um teste unitário. Padrões:
- `drive`: `https://drive.google.com/file/d/<ID>/...` ou `https://drive.google.com/open?id=<ID>` ou `https://drive.google.com/uc?...id=<ID>...`
- `vimeo`: `https://vimeo.com/<numeric_id>` ou `https://player.vimeo.com/video/<numeric_id>`
- `mp4`: URL terminando em `.mp4` (com ou sem querystring) servida via `https://`
- Qualquer outro formato → `None`, e a camada `*_ops` recusa com `CatalogValidationError("video_url", "...")`.

**Rationale**: Mesma forma de validação já usada no projeto (`CatalogValidationError` com `field`+`message`, consumida por `json_error(..., fields=...)` — contrato de erro já padronizado em `specs/144-migracao-react-spa/contracts/api-conventions.md`).

## 3. Modelo de dados — Tema/Personagem

**Decision**: Uma única URL de vídeo por Tema e uma única URL de vídeo por Personagem (não uma lista). A spec pede "suporte a vídeo" no Tema e no Personagem, no singular, e o pedido original não menciona múltiplos vídeos por entidade — uma lista abriria uma tela de gerenciamento de mídia adicional não pedida (YAGNI, Governança da constituição). Se o negócio precisar de múltiplos vídeos por item no futuro, é uma decisão de escopo nova, não implícita nesta.

**Rationale**: Reduz a migration a uma coluna nova em `catalog_items` + uma tabela nova `catalog_characters`, mantendo a galeria pública simples (N fotos + 0/1 vídeo por entidade).

**Alternatives considered**: Tabela `catalog_item_videos` genérica (many-to-many com Tema/Personagem) — rejeitada por complexidade não pedida.

## 4. Slug do Personagem (para link direto e lista de interesse)

**Decision**: Cada `CatalogCharacter` recebe um `slug` próprio, globalmente único, gerado como `<slug-do-tema>-<slug-do-nome>` com o mesmo algoritmo de desambiguação (`-2`, `-3`, ...) já usado em `unique_catalog_slug`/`_slugify` (`app/catalogo/importer.py`). A vitrine pública não ganha uma rota própria por Personagem — o link direto de um Personagem é `/catalogo/<tema-slug>?personagem=<personagem-slug>` (query param), que faz a página do Tema abrir com scroll automático e destaque no card do Personagem.

**Rationale**: Evita duplicar toda a lógica de Open Graph/meta tags/roteamento de uma página de detalhe nova para uma entidade que sempre existe no contexto do Tema pai — mais simples e ainda cumpre "Copiar link" individual (FR do gerenciador) e a distinção Tema-vs-Personagem na lista de interesse (FR-005).

**Alternatives considered**: Rota dedicada `/catalogo/personagem/<slug>` — rejeitada por não haver requisito de SEO/compartilhamento individual (a feature já pede `noindex` em toda a superfície) e por duplicar a página de detalhe do Tema quase inteiramente.

## 5. Lista de interesse (wishlist) — extensão para Personagens

**Decision**: `frontend/apps/public/src/lib/wishlist.ts` (100% client-side, `localStorage`, feature 140) ganha um campo opcional `kind: "tema" | "personagem"` (default implícito `"tema"` para itens já salvos, sem migração de dado necessária) e `parentSlug?: string` (preenchido apenas quando `kind === "personagem"`). `buildMessage()`/`whatsappUrl()` passam a montar o link de cada item conforme o tipo (`/${slug}` para Tema, `/${parentSlug}?personagem=${slug}` para Personagem).

**Rationale**: Não existe conta de cliente na parte pública — manter 100% client-side é consistente com a decisão já tomada na feature 140 (ver `frontend/apps/public/src/lib/wishlist.ts` linha 1-7). Estender o mesmo arquivo em vez de criar um sistema de carrinho novo cumpre o Princípio I (reutilizar antes de criar).

## 6. Vínculo de Personagem → Ficha de Figurino, e auto-vínculo em Novo Evento

**Decision**: `CatalogCharacter.figurino_sheet_id` é FK nullable para `figurino_sheets.id` (`ON DELETE SET NULL` — degrada com segurança se a ficha for excluída, conforme Edge Case da spec). No formulário de Novo Evento (`frontend/apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx`), cada linha de personagem (`CharacterInput` — já tem `name`, `figurino_sheet_id`, `talent_id`, `cache_value`, `needs_makeup`, `is_singer`) ganha uma ação "Escolher do catálogo" que, ao selecionar um Personagem, **preenche** `name` e `figurino_sheet_id` daquela linha uma única vez (prefill, não vínculo persistente) — exatamente como hoje o comercial já preenche esses campos manualmente. Isso cumpre FR-013 (auto-vínculo) e FR-014 (remoção manual não é reaplicada) sem nenhuma mudança de schema em `EventRole`.

**Rationale**: O modelo `EventRole` (`app/models.py:447`) já tem `character_name` + `figurino_sheet_id` — a ficha hoje é escolhida manualmente num `<select>` alimentado por `useFigurinoSheets()` (`frontend/apps/internal/src/lib/figurino.ts:31`, já busca a lista completa de fichas). Reaproveitar esse mesmo hook/fluxo para a busca de figurino evita criar um segundo endpoint de busca de fichas (Princípio I).

**Alternatives considered**: Persistir um vínculo Evento↔CatalogCharacter separado para poder "reaplicar" o vínculo depois — rejeitado pela spec (FR-014 exige que a remoção manual NÃO seja desfeita) e por não haver requisito de rastrear a origem do preenchimento depois de salvo.

## 7. `noindex` nas páginas públicas do catálogo

**Decision**: Tag `<meta name="robots" content="noindex, nofollow" />` injetada via `document.head` (mesmo padrão de `document.title` já usado em `ProductDetailPage.tsx`, linhas 15-22) num hook compartilhado `useNoIndex()` em `frontend/apps/public/src/lib/seo.ts` (novo arquivo pequeno), chamado por `CatalogGridPage` e `ProductDetailPage`. Índex.html do app `public` não pode ganhar a tag estática porque outras rotas do mesmo app (`/cadastro`, formulários, feedback) não fazem parte do escopo desta feature e não devem mudar de comportamento de SEO.

**Rationale**: Consistente com o padrão já existente de manipulação de `<head>` no próprio `ProductDetailPage.tsx`; evita tocar `index.html` (compartilhado por todas as rotas do app `public`).

## 8. Design vibrante — paleta já existe, não precisa criar

**Decision**: Não introduzir paleta nova. `frontend/apps/public/tailwind.config.ts` (e `frontend/packages/ui/tailwind-preset.ts`) já define `accent` (#4a2f6b, roxo escuro) e `gold` (#b1793a) como tokens do catálogo público — exatamente "roxo/dourado" pedido. O trabalho de "vibrante e elegante" é de **aplicação** (botões maiores/mais chamativos, sombras `shadow-lg`/`shadow-md` já existentes, bordas com `rounded-xl`/`rounded-lg` já no tema) e não de definição de cor nova.

**Rationale**: Cumpre a Governança da constituição (menor complexidade suficiente) e o Princípio I — o design system já resolve o requisito de marca.

## 9. Migration — ponta da cadeia

**Decision**: `down_revision = "4e6f8a1c2d5b"` (head atual, `4e6f8a1c2d5b_figurino_sheet_tags.py`). Nova migration cria `catalog_characters` e adiciona `catalog_items.video_url` (nullable). 100% aditivo — nenhuma coluna/tabela existente é alterada ou removida, upgrade/downgrade completos e manuais (padrão do projeto).

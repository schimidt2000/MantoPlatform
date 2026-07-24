# Research: Resumo das Avaliações — fidelidade visual e RBAC

Nenhum `[NEEDS CLARIFICATION]` restou da spec — este documento registra as decisões técnicas já
levantadas por inspeção direta do código existente (não há incerteza real a pesquisar, apenas a
consolidar).

## Decisão 1: Onde adicionar o preset "última semana" (7 dias)

- **Decision**: Adicionar `"7d": 7` em `_PERIOD_PRESETS` e `"7d": "última semana"` em
  `PERIOD_LABELS`, ambos em `app/talents/rating_ops.py`. Nenhuma outra função muda —
  `parse_period()` já resolve qualquer chave presente em `_PERIOD_PRESETS` genericamente
  (`_now_sp() - timedelta(days=_PERIOD_PRESETS[period])`).
- **Rationale**: É o único ponto de verdade do cálculo de período, já reusado por
  `app/api/ratings_read.py` (React) e por `app/talents/routes.py::avaliacoes()` (Jinja). Adição
  aditiva — nenhuma chamada existente passa `period="7d"` hoje, então nada quebra.
- **Alternatives considered**: Calcular o período "7d" só no frontend e mandar `from`/`to`
  explícitos (usando o modo `custom`) — rejeitado porque duplicaria a lógica de "hoje menos N
  dias" que já existe no backend para os outros presets, e perderia o rótulo padronizado
  (`recorte_label`) que o backend monta a partir de `PERIOD_LABELS`.

## Decisão 2: Não introduzir biblioteca de gráficos

- **Decision**: Replicar os gráficos do Jinja (barras de tendência mensal, barras horizontais de
  distribuição, barras de categoria) com `<div>`s e Tailwind (largura/altura calculada a partir
  dos dados), no mesmo espírito do `DonutChart` (`conic-gradient` puro) já entregue na feature 174.
- **Rationale**: Constituição (Princípio I) exige reutilizar padrões existentes; o projeto já
  provou que gráficos simples em CSS puro atendem à necessidade sem aumentar a superfície de
  dependências. Os gráficos desta tela (barras) são mais simples que o donut já implementado.
- **Alternatives considered**: `recharts`/`visx` — rejeitado por ser complexidade desnecessária
  (YAGNI) para barras simples, e por divergir do padrão já estabelecido no repo.

## Decisão 3: Componente de "pill" de filtro

- **Decision**: Reusar `Button` do design system com `variant={ativo ? "default" : "outline"}` e
  `size="sm"`, exatamente como `FinanceiroDashboardPage.tsx` (período) e `AdminDesempenhoPage.tsx`
  já fazem.
- **Rationale**: Já é o padrão visual estabelecido para "pills" nesta mesma aplicação — criar um
  componente `FilterPill` novo duplicaria o botão existente (viola Princípio I).
- **Alternatives considered**: Novo componente `Pill` em `@manto/ui` — considerado, mas adiado:
  não há ainda um segundo consumidor real que justifique extrair um componente compartilhado
  (constituição: "reutilize antes de criar", não "abstraia preventivamente").

## Decisão 4: Onde a regra de anonimato é aplicada

- **Decision**: Nenhuma lógica de anonimato no frontend. O campo `author` já vem calculado pelo
  backend (`rating_ops._comment_item`): `"Anônimo"` quando `show_authors` é falso,
  nome real quando verdadeiro. O frontend só decide se renderiza o *controle* de toggle
  (`is_superadmin`), nunca decide o texto de autoria.
- **Rationale**: Fonte única da regra de RBAC (Princípio I e III — regra de negócio não duplicada
  entre camadas). Já verificado em `app/talents/rating_ops.py:145-147,200-206` e
  `app/api/ratings_write.py:20-21` que o backend já impõe corretamente:
  `show_authors = viewer_is_superadmin and not fully_anonymous`, e que
  `POST /api/ratings/modo-anonimo` retorna 403 para não-SUPERADMIN.
- **Alternatives considered**: Adicionar uma checagem redundante de papel no frontend antes de
  exibir `c.author` — rejeitado: o dado já chega correto da API; uma checagem duplicada no
  frontend criaria uma segunda fonte de verdade da regra de privacidade, o oposto do que a
  feature pede ("corrigir" = garantir consistência, não "reimplementar").

## Decisão 5: Layout widescreen

- **Decision**: `<div className="w-full px-6 py-6 sm:px-8">` como container raiz, mesmo padrão de
  `DashboardPage.tsx` e `AgendaPage.tsx` (as duas telas já redesenhadas na feature 174 para serem
  widescreen).
- **Rationale**: Consistência de layout entre páginas já redesenhadas; não há motivo para esta
  tela usar uma variação própria de padding/largura.
- **Alternatives considered**: `max-w-[1600px] mx-auto` (padrão usado em `TalentsListPage.tsx`,
  por causa do mosaico de fotos) — rejeitado aqui porque esta tela não tem um mosaico de imagens
  com largura ideal de card; um grid de KPIs/gráficos se beneficia mais de `w-full`.

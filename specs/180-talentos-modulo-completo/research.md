# Research — Reestruturação do Módulo de Talentos

## 1. Unificar rota de edição na tela de detalhe

**Decisão**: `TalentDetailPage` ganha um estado de modo (`"read" | "edit"`) sincronizado com o
parâmetro de busca `?edit=1` na própria URL `/talents/:id` (via `useSearchParams`). A rota
`/talents/:id/edit` deixa de renderizar `TalentEditPage` e passa a ser um `<Navigate>` para
`/talents/:id?edit=1`, preservando qualquer link/atalho existente. `TalentEditPage.tsx` é
removida — toda a lógica de formulário (estado, `fieldErrors`, `useUpdateTalent`) migra para
dentro de `TalentDetailPage.tsx`, condicionada ao modo.

**Alternativas consideradas**:
- Manter duas telas e só adicionar um link cruzado — rejeitada: contraria o pedido explícito do
  usuário ("separador rígido... na própria tela") e perpetua duplicação de estrutura visual entre
  leitura e edição (dados em ordens/seções diferentes nas duas telas hoje).
- Modal de edição sobre a tela de leitura — rejeitada: o pedido é explícito sobre alternância na
  mesma página/layout, e um modal não comporta o formulário inteiro (fotos + todos os campos) sem
  virar uma segunda rolagem dentro da primeira.

## 2. Operador de altura "="

**Decisão**: estender `search_talents()` em `talent_ops.py` para aceitar `height_op="eq"`,
filtrando `Talent.height_cm == height_num`. É uma adição de 2 linhas ao `if/elif` já existente
(`gte`/`lte`), sem quebrar os dois valores atuais (default continua `"gte"`).

**Alternativas consideradas**: mapear "=" para `gte(v) AND lte(v)` no frontend sem tocar o
backend — rejeitada: o backend já centraliza toda a lógica de filtro (fonte única, Princípio I);
duplicar a regra de igualdade no cliente quebraria esse padrão à toa.

## 3. "Último evento" no histórico do perfil

**Decisão**: `get_talent_profile()` já ordena o histórico por `CalendarEvent.start_at desc()` —
o primeiro item da lista (`history[0]`, quando existente) é o último evento. Adiciona-se ao dict
retornado um bloco `"last_event"`: `{"event_id", "event_title", "character_name", "start_at"}` ou
`None` se não houver histórico. Nenhuma query nova — é derivado da mesma lista já calculada.

## 4. Seção "Avaliações e Notas" — exposição de dados que a spec 154 excluiu deliberadamente

**Decisão**: nova função `get_talent_ratings_overview(talent, *, viewer_is_superadmin)` em
`app/talents/rating_ops.py` (mesmo módulo que já centraliza `EventRating`/`EventSubRating`/modo
anônimo — evita duplicar a regra `show_authors`/`fully_anonymous` em `talent_ops.py`, que é de
outro domínio). Retorna dois grupos:
- **`received`**: `EventSubRating` onde `subject_talent_id == talent.id` — categoria, nota,
  comentário, evento, data. Nome de quem avaliou (`rating.talent.full_name`) só é incluído se
  `show_authors` (mesma regra já usada em `avaliacoes()`/`build_overview`: `viewer_is_superadmin
  and not fully_anonymous`) — senão, `"Anônimo"`.
- **`given`**: `EventRating` onde `talent_id == talent.id` — nota geral, comentário, evento,
  data, `edited_at`, `edit_count`. Autoria não se aplica aqui (é o próprio talento sendo visto);
  sempre exibido a quem já tem acesso de leitura ao perfil.

Novo endpoint dedicado `GET /api/talents/<id>/ratings` (não embutido no payload principal de
`GET /api/talents/<id>`) — mesma leitura aberta (`@api_login_required`, sem gate de papel,
paridade com o restante da leitura de talentos). Motivo de ser endpoint separado, não campo a
mais no payload principal: mantém `get_talent_profile()` enxuto e testável isoladamente (já é
reusado pelo Jinja legado, que **não** precisa desse bloco); o React busca os dois em paralelo
via TanStack Query (duas queries independentes, ambas com skeleton próprio) sem acoplar os dois
domínios de dados no backend.

**Alternativas consideradas**: acrescentar `received_sub_ratings`/`given_ratings` direto em
`get_talent_profile()` — rejeitada porque essa função é a mesma usada pelo handler Jinja
`talent_detail()`, que já calcula esses dois blocos separadamente com sua própria query; embutir
ali obrigaria o Jinja a descartar um payload que não usa, ou a duplicar a chamada. Endpoint
próprio evita as duas coisas.

## 5. Sugestão de personagens (dropdown de "Personagem")

**Decisão**: extrair a query de `character_suggestions()` (`app/talents/routes.py:372-391`) para
`suggest_characters(q: str) -> list[dict]` em `talent_ops.py` (mesma forma de retorno:
`[{"name":..., "count":...}]`). O handler Jinja passa a só chamar essa função e fazer
`jsonify(...)` — comportamento idêntico, zero mudança perceptível na rota `/talents/character-suggestions`
já usada pelo Jinja. Novo endpoint espelho `GET /api/talents/character-suggestions` em
`talents_read.py`, mesma função, mesma resposta, dentro do namespace `/api/*` (paridade com a
convenção do projeto de toda leitura nova nascer em `app/api`).

**Nota sobre o escopo "Jinja legado intacto"**: esta é a única linha tocada em
`app/talents/routes.py`, e é uma extração sem mudança de comportamento (mesmo padrão já usado em
100% dos outros endpoints deste arquivo, que já delegam para `*_ops.py`). Não altera nenhum
template, nenhuma resposta HTTP, nenhuma tela Jinja.

**Alternativas consideradas**: React chamar diretamente `/talents/character-suggestions` (rota
Jinja) via `fetch` — rejeitada: a constituição proíbe o frontend depender de rotas fora de
`/api/*`, e mistura os dois mundos (sessão de página vs. API JSON) que o projeto mantém
deliberadamente separados.

## 6. Componente de dropdown de filtro reutilizável

**Decisão**: novo `FilterDropdown` em `frontend/packages/ui/src/components/filter-dropdown.tsx`
— botão-gatilho + painel posicionado (Framer Motion `AnimatePresence`, fecha ao clicar fora/Esc),
aceita `children` para o conteúdo (permite tanto uma lista de checkboxes simples quanto o caso
especial de "Tamanho" com duas subseções). Um componente auxiliar `CheckboxList` cobre o padrão
comum (lista de opções + busca interna opcional) usado por Idioma/Raça/Calçado/Passaporte/Tags.
Sem dependência nova (não introduz Radix/Popover — implementação própria enxuta, consistente com
o restante do design system que hoje não usa nenhuma lib de overlay).

**Alternativas consideradas**: adotar `@radix-ui/react-popover` — rejeitada por ora: nenhuma
outra parte do design system usa Radix, e o padrão de overlay necessário aqui (painel ancorado,
fecha fora/Esc) é simples o suficiente para não justificar a dependência nova (YAGNI, Governança
da constituição).

## 7. Reaproveitar `FileUpload` do design system em vez de `TalentPhotoField`

**Decisão**: estender `FileUpload` (`frontend/packages/ui/src/components/file-upload.tsx`) com
três props opcionais — `existingUrl`, `existingLabel` (ex.: nome do arquivo já salvo) e
`onRemoveExisting` — para cobrir o caso "já existe um arquivo cadastrado, mostre-o com opção de
remover, mesmo antes de escolher um novo". `TalentPhotoField` (hoje duplicado dentro de
`TalentDetailPage.tsx`) é removido; o modo edição do perfil passa a usar `FileUpload` diretamente
para os 4 campos (rosto, corpo inteiro, documento, CNH), com o `onChange` disparando
`useUploadTalentPhoto` e `onRemoveExisting` disparando `useRemoveTalentPhoto` — mesmos hooks já
existentes em `lib/talents.ts`.

**Alternativas consideradas**: manter `TalentPhotoField` como está — rejeitada: viola
explicitamente o Princípio I (reutilizar antes de criar), citado no próprio pedido do usuário.

## 8. Playwright — introdução do zero

**Decisão**: `@playwright/test` como devDependency de `frontend/apps/internal` (escopo do app
tocado, não a raiz do workspace — os demais apps/`public` não são tocados por esta feature).
`playwright.config.ts` com `webServer` apontando para `npm run dev` (Vite, proxy `/api` → Flask
já configurado) e `reuseExistingServer: true` em dev local. O backend Flask **não** é subido pelo
Playwright — é responsabilidade do desenvolvedor/CI já tê-lo rodando contra `manto_local`
(`.\scripts\db\run-local.ps1`), mesma premissa que todo o resto da verificação funcional do
projeto já assume. Autenticação nos testes: um `global-setup.ts` faz login via
`POST /api/auth/login` com um usuário de teste já existente em `manto_local` e salva o
`storageState` (cookie de sessão) para reuso entre specs, evitando login manual em cada teste.

Dados de teste: os specs de detalhe/edição criam e removem um talento próprio via chamadas diretas
à API (`POST` de cadastro público ou fixture equivalente) dentro do próprio teste, para não
mutar talentos reais da cópia de produção. Os specs de listagem/filtro são só leitura e podem
rodar contra os dados reais de `manto_local` sem side effects.

**Alternativas consideradas**: Cypress — rejeitada, sem uso prévio no projeto e Playwright já é o
padrão de fato mais moderno para stacks Vite/React sem justificar a escolha de outra ferramenta;
mockar a API no e2e — rejeitada, o pedido explícito do usuário é rodar contra `manto_local`
(banco real), e mocks não pegariam divergências de contrato JSON reais (mesma razão pela qual o
projeto todo evita SQLite vazio para verificação).

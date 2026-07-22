# Research: Feedback Público por Token em React

## §1 — Reaproveitar constantes/helper por import direto (sem extrair `_ops`)

**Decisão**: `app/api/feedback_write.py` importa `POSITIVE_TAGS`, `ATTENTION_TAGS` e
`_tags_for_score` de `app/feedback/routes.py` — sem copiar. A validação de nome/nota e a
montagem do `ClientFeedback` (curtas, ~15 linhas) ficam escritas diretamente no endpoint novo.

**Razão**: mesmo raciocínio da 163 (`research.md` §2) — `app/feedback/routes.py` já separa as
constantes/regra de filtro de etiqueta em unidades reaproveitáveis; a lógica de validação
restante é pequena o bastante (bem abaixo do limiar de ~30 linhas por função da constituição)
para não justificar uma extração `_ops` só para dois chamadores. Extrair aqui seria
over-engineering para um bloco de código já curto e único.

**Alternativas consideradas**: extrair a validação/persistência para `feedback_ops.py` — rejeitado
por não resolver duplicação nenhuma real (o corpo é pequeno, a única coisa reaproveitável já são
as constantes/`_tags_for_score`, que já são importáveis sem mudança).

## §2 — Um único componente para os 3 estados (formulário / agradecimento / inválido)

**Decisão**: `AvaliarPage.tsx` busca o evento pelo token (`useFeedbackEvent(token)`); se a busca
404, renderiza o estado de link inválido; caso contrário, renderiza o formulário e, após envio
bem-sucedido, troca para o estado de agradecimento (estado local `submitted`, sem navegação de
rota) — paridade exata com o Jinja hoje, que resolve os mesmos 3 estados dentro do mesmo
`render_template` (`invalid.html` para 404; `public.html` alternando por `submitted`).

**Razão**: replicar a mesma divisão de estados que já existe evita inventar uma arquitetura de
rotas nova (ex.: rotas separadas `/avaliar/:token/obrigado`) para um fluxo que hoje é
propositalmente uma única tela — o link enviado à cliente é sempre o mesmo, antes e depois do
envio.

**Alternativas consideradas**: rota separada para a tela de agradecimento — rejeitado por não
ter necessidade real (não há nada para persistir na URL após o envio; um estado local é
suficiente e mais simples).

## §3 — Grupo de estrelas em React (substitui o truque CSS `flex-direction: row-reverse` + `~`)

**Decisão**: `StarRating.tsx` é um grupo de 5 botões (não inputs `radio` escondidos) que atualiza
um estado `score: number` via `onClick`, com preenchimento visual condicionado a
`starValue <= (hoverValue ?? score)` — substitui o hover em CSS puro por estado React
(`hoveredValue`), mesmo efeito visual (preenche até a estrela sob o cursor, ou até a nota
escolhida quando não há hover).

**Razão**: o truque do Jinja (`input:checked ~ label` + `flex-direction: row-reverse`) é uma
solução puramente CSS que não tem equivalente direto idiomático em componentes React
controlados — replicar com estado local é mais simples de entender e manter, com o mesmo
resultado visual e a mesma faixa de toque (botões, não radios escondidos, o que também melhora a
acessibilidade em touch — alvo de toque ≥44px, Princípio VIII).

**Alternativas consideradas**: manter `input[type=radio]` + CSS `~` sibling selector dentro do
React — tecnicamente possível, mas foge do padrão idiomático de componentes controlados já usado
no resto do app React (ex.: `WishlistButton`, `CpfField`), sem ganho real.

## §4 — Revelação do bloco de etiquetas com Framer Motion

**Decisão**: o bloco de etiquetas (positivas ou de atenção, conforme a nota) usa
`AnimatePresence`/`motion.div` com altura animada ao aparecer, substituindo a transição CSS
`max-height`/`opacity` do Jinja — mesmo efeito, via Framer Motion (Princípio IX,
`useReducedMotion()` desliga a transição).

**Razão**: princípio IX exige Framer Motion para revelação de blocos em superfícies públicas; o
Jinja já tinha uma transição equivalente (não é uma animação nova sendo introduzida, só migrada
para o padrão do projeto).

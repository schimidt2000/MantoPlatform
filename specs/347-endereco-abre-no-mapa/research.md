# Pesquisa — Feature 347

## R1. Que link abre cada app de mapas

**Decisão**: links universais HTTPS, com o endereço passado por `encodeURIComponent` (depois de
`trim`), mostrando o **local** (busca), não a rota:

| Opção | URL |
|---|---|
| Google Maps | `https://www.google.com/maps/search/?api=1&query=<endereço>` |
| Apple Mapas | `https://maps.apple.com/?q=<endereço>` |
| Waze | `https://waze.com/ul?q=<endereço>` |

**Por quê**: os três domínios são links universais. No iPhone e no Android, com o app instalado, o
sistema operacional entrega o link ao app; sem o app, o mesmo link abre o site do serviço, que
funciona em qualquer navegador. Um link só cobre os dois casos e o computador.
`maps.apple.com/?q=` é o formato que todo iOS em uso entende (o parâmetro `q` é tratado "como se
fosse digitado na busca do Mapas"); o formato novo `maps.apple.com/search?query=` só existe nos
iOS mais recentes.

**Alternativas rejeitadas**:
- Esquemas próprios (`comgooglemaps://`, `waze://`, `maps://`): sem o app instalado o Safari mostra
  "endereço inválido" e nada abre; exigiriam detectar app instalado, o que o navegador não permite.
- Rota já iniciada (`/maps/dir/?api=1&destination=`, `?daddr=`, `navigate=yes`): escolhe sozinha o
  primeiro resultado de um texto como "Buffet Encantado", sem a pessoa ver o pino. Fica a um toque
  ("Rotas"/"Ir") dentro do app (Premissas da spec).
- Mostrar só as opções do aparelho (Apple Mapas só no iPhone): exige farejar o user-agent e o pedido
  nomeou as três. No Android e no computador, "Apple Mapas" abre o site da Apple.

## R2. Abrir em outra aba no sistema instalado na Tela de Início

**Decisão**: `<a target="_blank" rel="noopener noreferrer">`.

**Por quê**: a regra de `docs/00` §5 (arquivo do sistema nunca abre em outra aba) existe porque o
visualizador de arquivo é conteúdo do sistema e a "outra aba" no app instalado vira janela sem
saída. Aqui o objetivo é justamente **sair** para outro app. O precedente é o link do WhatsApp
(`wa.me`, também link universal), que o app interno já abre com `target="_blank"` no Dashboard e
no Casting e que a equipe usa no iPhone com o sistema instalado. Se o app de mapas não estiver
instalado, abre o navegador, e o sistema continua atrás, na mesma tela.

## R3. Que peça de interface mostra a escolha

**Decisão**: o `Dialog` de `@manto/ui` (Radix + Framer Motion), com título "Abrir endereço", o
endereço como descrição e três links de 44px de altura.

**Por quê**: já traz foco preso, Esc e toque fora fechando, botão "Fechar" com `aria-label`,
animação de 150–200 ms com `useReducedMotion` (Princípio XI) e centralização por flex (armadilha 16
de `docs/00`). Existe nas duas SPAs e nos dois temas.

**Alternativas rejeitadas**: menu suspenso (não há primitivo de popover/dropdown em `@manto/ui`, e o
`KebabMenu` mora no app interno); folha que sobe do rodapé (seria um componente novo de
movimento, sem ganho para três opções).

## R4. Onde mora a peça

**Decisão**: `@manto/ui` — `src/lib/mapas.ts` (função pura que monta as três opções) e
`src/components/endereco-no-mapa.tsx` (o gatilho + a escolha), exportados em
`packages/ui/src/index.ts`.

**Por quê**: Princípio I e FR-010 — uma peça, dois apps. A função pura separada permite o
`verify_347.py` testar os links sem navegador. Os dois apps já varrem `../../packages/*/src` no
`content` do Tailwind e usam o mesmo preset, então as classes da peça existem nos dois CSS.

## R5. Como verificar sem backend

**Decisão**: `verify_347.py` empacota `packages/ui/src/lib/mapas.ts` com o `esbuild` que já está em
`frontend/node_modules` e roda os casos no `node` (sem rede). Inclui um cenário que **deve falhar**
(um montador ingênuo, sem codificação, tem de ser reprovado pela mesma checagem), a conferência de
que a peça está exportada e usada nas quatro telas e, contra o `manto_local` e só lendo, a prova
de que o detalhe do evento e a agenda do portal entregam `location` (a dependência que o
data-model assume; Princípio VIII, achado C1 do analyze). A tela aberta no Browser pane cobre o
resto (quickstart).

**Por quê**: nada no backend muda, então não há o que conferir no `manto_local`; o núcleo desta
feature é a montagem do link (FR-004, FR-008, FR-009), e é ali que um erro passa despercebido
(um `&` no nome do buffet cortaria a busca).

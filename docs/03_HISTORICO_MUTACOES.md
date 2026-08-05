# 03 — Histórico de Mutações

> **Documento vivo — APPEND ONLY.** Cada feature concluída adiciona uma entrada **no topo** da
> seção "Registro". Nunca reescrever entradas antigas (elas são o histórico); correções entram
> como nova entrada referenciando a anterior.
>
> Última atualização: **2026-08-05** · Estado do repositório: pós-hotfix **212 (diálogos fora da
> tela)** · Head de migration: `e7a1c94f20b3`

Formato de cada entrada:

```
## <NNN> — <título>            (branch · data do merge · migration)
Motivação · O que mudou (Backend / Banco / Frontend) · Impacto em RBAC e regras de negócio ·
Rotas e endpoints novos/alterados · Riscos e pegadinhas
```

---

## Registro

### 212 — Hotfix: diálogos abrindo pela metade, fora da tela
`main` · **2026-08-05** · sem migration

**Motivação.** "Em diversas páginas o pop-up fica pela metade e não consigo mexer": o diálogo
abria com o topo no meio da tela e a metade de baixo para fora, sem rolagem que alcançasse o
resto. Atingia **11 telas** — todas as que usam o `Dialog` do design system (Novo post de
marketing, detalhe de resposta de formulário, memória de cálculo do orçamento, gastos
recorrentes, fila e acervo 3D, comissões, histórico EducaManto, cabeçalho do evento…).

**Causa.** O painel do `DialogContent` era centralizado por `left-1/2 top-1/2` +
`-translate-x-1/2 -translate-y-1/2` (Tailwind) **e** era um `motion.div` animando `scale`/`y`. O
Framer Motion escreve `transform` no **estilo inline**, que vence as classes utilitárias — a
centralização evaporava e sobrava só `left: 50%; top: 50%`, ou seja, o **canto superior esquerdo**
do diálogo no centro da tela. Confirmado no DOM: `transform: translateY(8px) scale(0.96)`.

**O que mudou.** Centralização por **flex**, não por transform: o `Content` do Radix passou a
viver dentro de `fixed inset-0 overflow-y-auto` > `flex min-h-full items-center justify-center
p-4`. Diálogo curto centraliza; diálogo mais alto que a janela faz o **container rolar** em vez de
vazar pelo rodapé. O Framer Motion continua animando `opacity`/`scale`/`y` — agora o `transform`
serve só à animação, não ao layout. Fechar clicando fora segue funcionando: quem cuida disso é o
`onPointerDownOutside` do `Content` do Radix, não o overlay.

**Pegadinha (vale para todo componente animado).** Não centralize com `translate` de utilitário um
elemento cujo `transform` é animado — a biblioteca de animação sobrescreve. Use flex/grid no
container. O `Modal` de `apps/internal/src/components/Modal.tsx` já fazia certo (flex + `max-h`),
o que explica por que só os `Dialog` quebravam.

**Verificação.** No navegador, contra a cópia de produção: "Nova postagem" (1280×720) topo 57 /
base 679, dentro da tela e centralizado; detalhe de resposta do formulário topo 74 / base 662;
mobile 375×812 dentro das margens; e o caso estrutural — painel de 1099px numa janela de 420px:
o container rola (1177px) com topo **e** rodapé alcançáveis. Typecheck e build limpos nos três
apps.

### 211 — Vitrine: quadro da foto com teto e piso
`main` · **2026-08-05** · sem migration

**Motivação.** Na página do produto, o tamanho da foto mandava no layout inteiro. "Às de Copas"
(retrato alto e de arquivo grande) tomava a tela e **espremia a coluna do texto até virar uma
tira**: título quebrado em duas linhas, tags empilhadas uma por linha e botões virando bolinhas.
"80's Neon", com foto menor, ficava correto. Cada produto abria de um jeito.

**Duas causas, não uma.**

1. **Coluna espremida** — a culpa não era da altura, era da largura. O `grid-cols-[1.1fr_1fr]`
   parece garantir a proporção, mas item de grid nasce com `min-width: auto`: a coluna **não
   encolhe abaixo da largura natural do conteúdo**. Uma foto de arquivo grande empurrava a
   coluna da direita para fora da sua fração. `min-w-0` nas duas colunas devolve o controle ao
   `1.1fr/1fr` (medido depois: 568px / 516px, como esperado).
2. **Quadro sem limites** — a galeria só tinha teto (70vh) e nenhum piso, então retrato alto
   virava parede e paisagem larga virava tira. O palco agora vive numa faixa: piso de 380px,
   teto de `min(62vh, 620px)`. A foto continua inteira (`object-contain`), o que sobra é o fundo
   do quadro.

**Onde a garantia mora.** Teto e piso são **CSS** (`min-height`/`max-height`) no elemento do
palco, não só conta em JavaScript. Assim valem antes de a foto carregar, quando ela falha, e
depois de o usuário redimensionar a janela — a altura calculada no `onLoad` é um pixel fixo que
envelhece, e não havia listener de resize. O cálculo em JS continua, para o quadro já nascer no
tamanho certo em vez de crescer na frente do cliente.

**Pegadinha.** A altura do palco saiu do `animate` do Framer Motion e virou `style` + transição
CSS. Tamanho de quadro precisa valer no primeiro quadro renderizado; entregá-lo à biblioteca de
animação deixava o palco com 24px quando a imagem falhava.

**Verificação.** Typecheck e build limpos nos três apps; proporção das colunas e a faixa aplicada
(`min-height: 380px`, `max-height: 446.4px` numa janela de 720px) conferidas no DOM. A cópia
local não tem os arquivos de mídia (só o banco vem de produção), então a conferência visual com
fotos reais foi feita na página publicada.

### 210d — Hotfix: navegador preso no bundle antigo (e vínculo de ficha mais óbvio)
`main` · **2026-08-05** · sem migration

**Motivação.** Chegou o relato "não dá para vincular ficha depois de criado o personagem", com
print do painel de Personagens sem o botão. O botão **já estava em produção desde a 209** — o
print mostrava a versão da 207 (dava para saber pelo rótulo "sem vídeo", que a 209 removeu).

**Causa raiz — deploy que não chega no usuário.** O `serve-handler` não manda `Cache-Control`
nenhum. Sem esse cabeçalho, o navegador aplica **cache heurístico** em cima do `Last-Modified` e
guarda o `index.html` — que é justamente quem aponta para o bundle com hash. Resultado: o deploy
sobe, a sondagem em produção passa (o servidor entrega o arquivo novo para quem pede), e mesmo
assim o usuário continua rodando o JavaScript velho até dar refresh forçado. Isso vale para
**todo** deploy do frontend, não só este caso.

`frontend/server.js` passou a declarar o contrato padrão de SPA com assets versionados:
`Cache-Control: no-cache` para HTML (pode guardar, mas **revalida sempre**; o arquivo tem menos
de 1 KB e vira 304 quando nada mudou) e `public, max-age=31536000, immutable` para `assets/*`
(o hash está no nome, então conteúdo novo = URL nova). A regra de `assets` vem depois de
propósito: o `serve-handler` percorre a lista inteira e a última que casar vence.

**UX.** O selo "⚠ Sem ficha vinculada" virou botão — "⚠ Sem ficha vinculada — vincular" — e abre
o mesmo painel do botão "Ficha & página". É onde o olho bate ao procurar o que falta; deixar a
ação só atrás do outro botão dava a impressão de que não dava para vincular depois de criar.

**Riscos e pegadinhas.** "Verifiquei em produção" ≠ "o usuário está com isso": a sondagem busca o
bundle direto, o navegador dele não. Quando um relato descrever uma tela que não bate com o
código, procure um texto que só existe na versão antiga antes de sair caçando bug — foi o "sem
vídeo" que resolveu este. Verificação: `frontend/scripts/verify-proxy.mjs` ganhou a seção "Cache
do navegador" (HTML das 3 SPAs com `no-cache`, asset com `immutable`) — todos os checks OK; e o
vínculo de ficha foi exercitado de ponta a ponta no navegador (vincular pelo selo, gravar,
desvincular pelo ✕).

### 210c — Hotfix: Comercial voltou a enxergar o pagamento do evento
`main` · **2026-08-05** · sem migration

**Motivação.** O Comercial criava o evento e subia o comprovante, mas não via se a cliente já
havia pagado — sumiram o painel "Comprovantes de pagamento" (com o "Recebido X de Y" e o selo
"Quitado ✓") e o de "Reembolsos".

**Causa.** Na API, `data["pagamentos"]` e `data["reembolsos"]` foram colocados no bloco
`show_financeiro` (FINANCEIRO/SUPERADMIN). No Jinja os dois painéis ficavam dentro de
`{% if show_comercial %}` (`event_detail.html` 1982-2196) — quem vende sempre viu. Incoerência
visível: `reembolsos_pendentes_total` já ia para o Comercial, então ele lia "há R$ X pendente"
sem poder ver do que se tratava.

**O que mudou.** As duas chaves passaram para o bloco `show_comercial`. Nada mudou no React: os
painéis já apareciam por presença de chave (o servidor decide), e o `PagamentosPanel` já trazia o
"Recebido/Quitado", a lista e o formulário de novo comprovante.

**RBAC — o que NÃO mudou.** Subir comprovante e registrar/cobrar reembolso sempre foram
`_CAN_EDIT_EVENT` (inclui Comercial) nos endpoints; editar valor e excluir comprovante/reembolso
seguem restritos a SUPERADMIN, checados no endpoint e escondidos no React por
`flags.is_superadmin`. `kpi` e `gastos` (lucro, cachês, despesas) continuam só no bloco
financeiro — foi só isso que sobrou lá.

**Pegadinha.** Ao migrar um bloco do Jinja para a API, o gate tem de ser o do **template**, não o
do "parece financeiro". Verificação: seção 6 do verify_210 (43/43) com usuários de papel puro
(Comercial vê pagamentos e não vê KPI; Comercial sobe comprovante → 201, mas edita/exclui → 403;
Financeiro segue com tudo; Casting segue sem ver venda nem pagamentos) e conferência na tela com
"Ver o sistema como COMERCIAL".

### 210b — Hotfix: buscador de pré-contrato mudo
`main` · **2026-08-05** · sem migration

**Motivação.** O campo "Pré-contrato (formulário recebido)" de `/events/new` e
`/events/:id/edit` não devolvia nada para nenhum termo.

**Causa.** `FormResponsePicker` chamava `${API_BASE}/formularios/respostas/search` — a rota
**Jinja**, fora de `/api`. `frontend/server.js` só repassa ao Flask os prefixos de
`BACKEND_PREFIXES`, e `/formularios` não pode entrar lá: é rota do React Router (a tela de
Formulários). Resultado: a chamada caía no fallback da SPA e recebia o `index.html` **com status
200** — `r.ok` era verdadeiro, o `JSON.parse` estourava e o `.catch(() => setResults([]))`
transformava a falha em lista vazia. Ninguém via erro nenhum.

Antes da 206 isso funcionava porque `VITE_API_BASE_URL` apontava para o domínio do Flask e a
chamada não passava por proxy nenhum. Mesma família dos gaps de proxy da migração — e o único
caso restante: `/figurinos/<id>/print` e `/figurinos/print-event/<id>` já estavam cobertos por
`BACKEND_PATTERNS`, e uma varredura em `apps/*/src` não achou outra chamada fora de `/api`.

**O que mudou.** O componente passou a usar `apiFetch("/api/formularios/respostas/search")` — o
endpoint equivalente já existia em `app/api/formularios_admin_read.py`, sem tela que o usasse. A
lista agora mostra tipo · telefone · data do evento. Estados de **buscando**, **nenhuma resposta
encontrada** e **erro** substituíram o silêncio: a lição do bug é que "lista vazia" e "a chamada
falhou" não podem se parecer.

`formularios_ops.search_responses` ganhou **busca por data do evento** (`dd/mm/aaaa`, `dd/mm/aa`,
`dd-mm-aaaa`, ISO) — o campo prometia "nome, telefone ou data" e só fazia nome e telefone. O
casamento por telefone passou a exigir 4+ dígitos: com data no jogo, um "12" digitado no meio de
`12/08/2026` casava com meio banco de telefones.

**Riscos e pegadinhas.** Ao consumir rota do Flask a partir do React, use **sempre** `/api/*`.
Fora de `/api`, só com entrada explícita no proxy (`server.js` **e** os `vite.config.ts`), e por
regex restrito quando o prefixo colide com rota do React Router. Verificação: seção 5 do
verify_210 (30/30) e os quatro caminhos conferidos no navegador (nome, telefone, data e termo sem
resultado).

### 210 — Hotfix: horário deslocado, anexo do evento e orçamento sem saída
`main` · **2026-08-05** · sem migration

**Motivação.** Três regressões críticas apareceram junto quando a 206 tornou o React a interface
primária — todas em código que já existia, mas que só virou o caminho real dos usuários agora:
horários de eventos "mudando sozinhos", comprovante falhando sempre depois de criar o evento, e a
calculadora de orçamento sem a memória de cálculo nem a tela de apresentação da proposta.

**1. Horário deslocado +3h a cada edição (o mais grave).**
`start_at`/`end_at` são **horário de parede de São Paulo** — o banco guarda naive (ver
`service.py::parse_event_datetime`) e a API serializa com `.isoformat()`, sem fuso. O
`EventEditPage` hidratava o formulário com `new Date(iso).toISOString().slice(...)`: o `Date`
interpretava a string como horário local do navegador e o `toISOString` convertia para UTC,
abrindo todo evento com **+3h**. Salvar gravava o horário deslocado no banco **e empurrava para o
Google Agenda** — por isso os dois "concordavam" no valor errado e não havia divergência para
comparar. Em evento noturno (≥ 21h) a **data** também pulava um dia, e o fim virava madrugada do
dia seguinte pela regra da meia-noite do `_build_start_end`.

Correção em `lib/horaLocal.ts` (`dataDeIsoLocal`, `horaDeIsoLocal`, `hojeYmd`): para preencher
formulário e comparar datas, **recorta a string, nunca passa por `Date`**. `GastosExtrasPage` e
`GastosRecorrentesPage` usavam `new Date().toISOString().slice(0,10)` como "hoje" — depois das 21h
isso já dava o dia seguinte; passaram a usar `hojeYmd()`.

No mesmo `reset()`, `description` era hidratada com `""` enquanto o PATCH manda a descrição
inteira: **toda edição apagava a descrição do evento** (e a do Google Agenda), inclusive os blocos
com dados da contratante. Passou a hidratar `data.event.description`.

**2. Comprovante "sempre falhou" ao criar evento.** A fase 2 do `EventCreatePage` (anexos) usava
`useAddPayment(createdEventId ?? 0)`. `setCreatedEventId` só tem efeito no render seguinte e a fase
2 dispara ainda dentro do `onSuccess` da criação — o hook continuava preso em `0` e o upload ia
para `POST /api/events/0/payments` → 404. Determinístico: o evento nascia certo e **todo** anexo
falhava. "Tentar novamente" funcionava, porque aí o estado já tinha atualizado — o que fazia
parecer instabilidade de rede. Os uploads viraram funções soltas
(`enviarComprovante`/`enviarContrato`/`enviarReembolso`/`enviarObservacaoComFoto`), que recebem o
`eventId` por argumento; os hooks passaram a ser casca fina em volta delas.

**3. Memória de cálculo virou a mensagem de WhatsApp.** O diálogo "Ver memória de cálculo" mostrava
`quote.message`. O painel do Jinja (`orcamento/index.html` + `static/js/orcamento.js`) montava a
memória **no cliente**, duplicando a conta — motivo de ela ter se perdido na migração.
`quote_ops.calculate_quote` agora emite a memória junto com o cálculo (chave `memoria`), linha a
linha e na ordem em que cada parcela entra: cachê por profissional, coordenador, subtotal, markup,
brinde, adicional noturno, técnico, maquiador, transportes, acréscimos, NF e total. A verify prova
que a soma das parcelas fecha com os totais — a memória não pode "explicar" um número diferente do
cobrado. No orçamento personalizado a memória mostra só cachê-base × multiplicador (ou o valor
digitado), porque transporte/NF/acréscimo realmente não entram ali.

**4. "Gerar Orçamento" não levava a lugar nenhum.** Só salvava e o botão virava "Orçamento salvo".
Nova rota `/orcamento/:id` (`OrcamentoResultadoPage`), sucessora de
`app/templates/orcamento/resultado.html`: mensagem de WhatsApp copiável, resumo por duração,
detalhamento do transporte, memória de cálculo, baixar PDF e enviar por e-mail. O histórico ganhou
"Abrir orçamento" apontando para ela. Nenhum endpoint novo — `historico/<id>`, `/pdf` e
`/enviar-email` já existiam sem tela que os usasse.

**Rotas.** React: `/orcamento/:id` (declarada **depois** de `/orcamento/historico` e
`/orcamento/configuracoes`, senão `:id` casaria com elas). Backend: nenhuma nova; `quote.memoria`
é chave nova em `POST /api/orcamento/calcular` e no detalhe do histórico (orçamentos salvos antes
disso não têm a chave — o React trata como "memória não registrada").

**Riscos e pegadinhas.**
- Nenhum `Date` deve tocar em `start_at`/`end_at` para produzir valor de formulário. O bug
  sobreviveu meses porque `new Date(iso)` **exibe** certo para quem está em São Paulo — só quebra
  ao voltar para string via `toISOString()`.
- Os eventos editados enquanto o bug existiu ficaram com o horário deslocado nos dois lados (banco
  e Google), então não há como detectá-los por divergência. `scripts/db/relatorio_horarios_
  deslocados.py` lista os candidatos pelo log "Editou os dados do evento" e sugere o horário
  original, para conferência humana — não corrige nada sozinho.
- Ferramenta nova de desenvolvimento: `scripts/db/run-local-sem-google.py` sobe o Flask contra
  `manto_local` com `insert/update/delete_event` do Google dublados. Sem isso, reproduzir criação
  de evento no navegador cria lixo no calendário de produção.
- Verificação: `verify_210_horario_anexo_orcamento.py` 23/23 contra `manto_local` (round-trip do
  PATCH sem deslocar em evento noturno, descrição preservada, anexo com id real ✕ id 0, memória
  fechando com os totais, PDF e e-mail). Typecheck e build limpos nos três apps.

### 209 — Catálogo como espinha organizacional (página própria + fichas + busca)
`main` · **2026-08-05** · migration `e7a1c94f20b3` (*own_item_id em catalog_characters*)

**Motivação.** O catálogo deixa de ser só vitrine e vira o início da organização: tema com
elenco embaixo (Abba), personagem com ficha de figurino vinculada (métrica de cobertura),
personagem que TAMBÉM tem página própria e buscável (Coelho Branco dentro do tema Alice), e
variação de figurino como personagem separado (Gabby Boneco ✕ Humanizada — decisão do dono:
a Humanizada mantém página vendável na busca).

**Modelo.** `catalog_characters.own_item_id` (FK catalog_items, UNIQUE, SET NULL): o
personagem aponta para o item que É a página dele. Hierarquia de UM nível, de propósito —
tema com elenco não pode virar personagem de outro tema (validação em `set_own_item`/
`adopt_item_as_character`). O relacionamento `CatalogItem.characters` precisou de
`foreign_keys` explícito (dois FKs para a mesma tabela = AmbiguousForeignKeysError no boot).

**O que mudou.**

*Ops/API* — `catalog_character_ops`: `set_own_item`, `toggle_own_page` (checkbox "Página
única" = `is_active` do item vinculado; reversível, nunca apaga), `adopt_item_as_character`
(foto COPIADA da capa via `storage.copy_file`). Endpoints SUPERADMIN:
`POST /api/admin/catalogo/personagens/<id>/pagina-propria`, `.../pagina-unica`,
`POST /api/admin/catalogo/<tema_id>/adotar-item`.

*Vitrine* — `_character_summary` público ganhou `own_item_slug` (só quando a página está
ATIVA): o tile do elenco vira link para a página própria. Detalhe do item ganhou
`parte_de_tema` → selo "✦ Parte do tema Alice" com volta ao elenco. `_item_summary` da
grade ganhou `tags` e a busca client-side passou a incluí-las — "alice" acha o Coelho pela
tag, sem personagens poluindo os resultados.

*Admin* — `FigurinoSheetPicker` novo (busca realtime sem acento + thumb da ficha; fichas
com nome batendo com o personagem sobem ao topo) substitui os DOIS `<select>` cegos (painel
de personagens e vínculo rápido da árvore). Cada personagem ganhou o bloco "Ficha & página"
(picker + controles de página própria). Painel ganhou "Adotar item existente como
personagem". Listagem ganhou o termômetro `characters_com_ficha/characters_total` por tema
+ soma no topo, e o rótulo "página única — elenco de X" nos itens adotados.

**Riscos e pegadinhas.**

1. **Adoção COPIA a foto da capa** — nunca referencia (`delete_file` é chamado em 5 pontos
   sem saber de compartilhamento; mesmo racional do drag de foto da 207).
2. **Desligar a "página única" usa `is_active` do item** — o mesmo flag do gerenciador.
   Reativar o item pelo gerenciador religa a página do personagem (comportamento desejado:
   um flag só, sem estado paralelo).
3. **manto_local está atrás da produção** (o Abba da assistente não existe na cópia local).
   Rodar `refresh-local-db.ps1` antes do mutirão de organização.
4. Regra de modelagem registrada: versão de TEMA inteiro = temas separados (Alice Desenho ✕
   Live Action); variação de FIGURINO = personagens separados no mesmo tema (Gabby Boneco ✕
   Humanizada), cada um com sua ficha — a métrica de cobertura conta certo sozinha.

### 208 — Restauração do papel ENSAIO (dashboard + agendamento + presença)
`main` · **2026-08-05** · sem migration

**Motivação.** Incidente relatado pela equipe: a home do papel ENSAIO ficou vazia
("Tudo em dia!") após a 206. A auditoria mostrou que o papel perdeu TRÊS capacidades — o
dashboard inteiro (ensaios a agendar/agendados/órfãos + presença pendente), o
**agendamento de ensaios** (create/edit/delete/link eram rotas Jinja sem equivalente
`/api`) e a **atribuição do Técnico de Som (Presença)** (no React a vaga só era editável
por casting; no Jinja era tarefa do ensaio).

**O que mudou.**

*Backend* — `event_ops.py` ganhou o núcleo extraído das rotas Jinja: `create_ensaio`,
`update_ensaio`, `delete_ensaio`, `link_ensaio_to_show`, `assign_tech_presence`,
`build_ensaio_times` (regra da meia-noite preservada) e `resolve_ensaio_location`
(dependências de `routes` importadas só em runtime — sem ciclo de boot). Endpoints novos:
`POST /api/events/<id>/ensaios`, `PATCH/DELETE /api/ensaios/<id>`,
`POST /api/ensaios/<id>/vincular`, `POST /api/events/<id>/presenca` — todos gated por
`_CAN_ENSAIO` (Ensaio/Casting/Superadmin). `dashboard_service.compute_ensaio_tasks` +
seção `ensaio` no `/api/dashboard` (gate: ENSAIO ou superadmin, paridade com a home
Jinja). `serialize_event_detail` expõe `ensaios`, `presenca` e (em eventos ENSAIO)
`ensaio_pai`.

*Frontend* — `EnsaioSection` no detalhe do evento: no SHOW lista/agenda/cancela ensaios e
define a presença (select de talentos); no próprio ENSAIO mostra o pai (ou o estado órfão
com busca de show para vincular — reusa `useAgendaSearch`), edita horário e cancela.
Dashboard ganhou o painel "🎭 Ensaio" com as quatro listas.

**Riscos e pegadinhas.**

1. **A resposta do PATCH/DELETE de ensaio é o detalhe do SHOW pai** (a tela que o painel
   refaz). Na página do próprio ensaio isso corromperia o cache se fosse para
   `setQueryData(["event", ensaioId])` — os hooks da página do ensaio usam
   `invalidateQueries` em vez do write-through padrão.
2. **`verify_208` contra manto_local toca o Google Calendar REAL** (o token vive no banco
   copiado): o ensaio de teste é criado e excluído de verdade. Transitório, mas visível
   por segundos na agenda.
3. **Excluir um show cascateia para os ensaios filhos** — a limpeza de teste precisa
   limpar as tabelas satélite de TODOS os eventos antes de deletar qualquer um.
4. O gate do dashboard é ENSAIO/superadmin (como a home antiga); o gate de ESCRITA é
   `_CAN_ENSAIO` (inclui CASTING). São padrões diferentes de propósito — casting agenda
   ensaio pelo evento, mas não carrega o painel de pendências.

### 206b — Hotfix: superfícies públicas por link voltaram a abrir sem login
`main` · **2026-08-05** · sem migration

**Motivação.** Incidente pós-virada: links públicos já distribuídos (formulário de
pré-contrato `/f/*`, cadastro de talentos `/cadastro/*`, avaliação da cliente `/avaliar/*`)
caíam no fallback do ERP interno e pediam login. A lista de proxy da 206 cobria API, mídia e
impressão — mas **superfície pública por link é uma categoria própria** que ninguém enumerou.

**O que mudou.** `frontend/server.js` ganhou `/cadastro`, `/avaliar` e `/static` (o CSS das
páginas Jinja) em `BACKEND_PREFIXES`. Os formulários tiveram tratamento próprio no segundo
ajuste do dia: **`/f/<slug>` é o endereço canônico** (impresso em bio e conectado a outros
softwares) e responde **302 → `/catalogo/f/<slug>`** preservando a query — o link antigo
abre o formulário REACT da vitrine, e o Jinja de `formularios_bp` fica aposentado como
superfície. O painel de Formulários copia o link curto. E os dois geradores de link de
avaliação (`api_feedback_link` e `feedback.gerar_link`) trocaram `request.url_root` por
`PUBLIC_BASE_URL`: atrás do proxy com `changeOrigin`, o Host que chega ao Flask é o do
serviço backend — link novo sairia com o domínio interno da Railway.

**Pegadinha para o futuro.** Ao apontar um domínio para o serviço frontend, o checklist do
proxy tem QUATRO categorias: API (`/api`), mídia (`/uploads`, `/catalogo/midia`,
`/portal/photo`), páginas internas legadas (`/figurinos/*/print`, `/google`) e **links
públicos em circulação** (`/f`, `/cadastro`, `/avaliar` + `/static`). Os links do painel
React de Formulários apontam para `/catalogo/f/<slug>` (SPA pública) e nunca quebraram — o
que quebra é sempre o link antigo impresso em bio/WhatsApp.

### 207 — Pacote de melhorias operacionais (5 frentes)
`main` · **2026-08-04** · migration `d9f2b3a41c07` (*google_review_url em site_settings*)

**Motivação.** Cinco atritos do dia a dia relatados pelo dono após a virada do React: impressão
de fichas com páginas em branco (e sem botão na SPA), agenda sem busca, catálogo exigindo HTML
na mão e sem caminho da galeria para o personagem, avaliação 5 estrelas sem conversão para o
Google, e o log do evento visível a qualquer papel.

**O que mudou.**

*Impressão de fichas* — `print_event_figurinos` agora filtra `role_type == "extra"` e deduplica
personagem (ficha quando existe, nome normalizado quando não) — cada extra/duplicata virava uma
folha. CSS de impressão: `.sheet-page` vira `display: block` no print (flex fragmenta mal no
Chromium e gerava folhas em branco), `break-inside: avoid` nos blocos, e modo `sheet-compact`
(>14 peças encolhe linhas/foto e corta linhas vazias para caber em UMA folha). Botão
"Imprimir fichas" voltou na `FigurinoSection` da SPA; proxies dev (vite) e produção
(`server.js`) ganharam `^/figurinos/print-event/\d+$`.

*Busca da agenda* — `event_ops.search_events` (núcleo puro): título e nome de cliente sem
acento (`unaccent_lower_sql`), telefone por só-dígitos `LIKE %digits%`, cobrindo `event_clients`
E `client_id` legado via EXISTS. `GET /api/agenda/search?q=` (rota separada — contrato do
`/api/agenda` intocado); nome/telefone da cliente só saem para COMERCIAL/FINANCEIRO/SUPERADMIN
(demais acham o evento, campos vêm `null`). UI: campo único na toolbar, debounce 300ms para o
param `q` da URL, resultados agrupados em Próximos/Anteriores/Sem data reusando `AgendaListItem`.

*Catálogo* — `storage.copy_file` (local resolve `/catalogo/midia/*` de volta a `catalog_photos/`;
S3 usa `copy_object`) + `adopt_gallery_photo` + `POST /api/admin/catalogo/personagens/<id>/adotar-foto`:
arrastar foto da galeria até um personagem a adota como foto dele (HTML5 dnd, payload
`application/x-manto-catalog-photo`; confirmação ao sobrescrever). A foto é SEMPRE copiada —
URL compartilhada quebraria nos 5 pontos que chamam `delete_file`. Descrição: `RichTextEditor`
(contentEditable + execCommand, B/I/limpar, cola só texto puro — zero dependência nova) no lugar
do textarea de HTML cru; sanitização server-side nova com **nh3** (`_sanitize_description`,
tags `b/strong/i/em/p/br/span/div`, zero atributos) nos dois pontos de gravação — antes NÃO
havia sanitização e o valor é renderizado com `dangerouslySetInnerHTML`/`|safe`.

*Avaliações* — coluna `site_settings.google_review_url` (NULL = `DEFAULT_GOOGLE_REVIEW_URL` em
`feedback_write.py`), editável em Admin→Configurações; `GET /api/avaliar/<token>` devolve
`google_review_url` e a tela de agradecimento (React E Jinja legada) mostra o CTA "Avaliar no
Google" quando a nota é 5. `DELETE /api/clientes/avaliacoes/<id>` (SUPERADMIN-only, auditado,
`client_ops.delete_feedback`); botão com confirmação inline nas duas telas
(`ClientFeedbackPage` via flag `can_delete` do payload, `FeedbackSection` via
`flags.is_superadmin`); o hook invalida `["clientes-avaliacoes"]` e o prefixo `["event"]`.

*Logs do evento* — `serialize_event_detail` só inclui `"logs"` quando `flags["is_superadmin"]`
(some também em impersonação — convenção de `auth.py`/`dashboard_service.py`); antes o payload
vazava para todo papel e só a UI escondia. Tipo `logs?:` opcional; `LogsSection` checa presença
da chave. Inserido ANTES do early-return de ENSAIO.

**Riscos e pegadinhas.**

1. **O dedup do print escolhe o PRIMEIRO cargo (menor id) de cada personagem** — o talento
   impresso na ficha é o desse cargo; os demais talentos do mesmo personagem não aparecem.
   Aceitável (a ficha é do figurino, não da escala), mas é uma escolha.
2. **`copy_file` devolve `None` em falha e a op converte em 400 controlado** — origem sumida do
   disco/bucket não derruba o request. Testado com arquivo inexistente.
3. **A sanitização nh3 só roda na GRAVAÇÃO** — descrição legada do WooCommerce continua como
   está até a primeira edição (na qual perde atributos de `<span>`, comportamento desejado).
4. **`queryCommandState`/`execCommand` são deprecados** — funcionam em todos os browsers atuais
   para bold/italic; se um dia quebrarem, o caminho é TipTap (decisão registrada: evitamos a
   dependência enquanto o escopo é negrito/itálico/parágrafo).
5. **A busca não usa índice** (translate/lower sobre title/name) — aceitável no volume do ERP,
   com `LIMIT 30` e mínimo de 2 caracteres obrigatórios.
6. **`verify_145` ganhou 3 checks de logs; `verify_207_pacote_melhorias.py` cobre o pacote**
   (23/23 contra manto_local).

### 206 — React como interface primária e proxy reverso em produção
`205-loja-interacoes-virtuais` · **2026-08-04** · sem migration

**Motivação.** A plataforma vivia em dois endereços: o serviço Node com os três bundles React e o
Flask com a API mais um resto de Jinja. Isso obrigava o build a carregar `VITE_API_BASE_URL`
apontando para o outro domínio, transformava todo `fetch` em cross-origin e deixava a raiz do
Flask servindo um dashboard paralelo ao do React. A 206 fecha isso: `app.mantoproducoes.com.br`
passa a ser a **única** porta de entrada, e o Flask vira serviço de backend puro.

**O que mudou.**

*Frontend* — `frontend/server.js` deixou de ser só `serve-handler`: agora usa `http-proxy`
(dependência nova, `^1.18.1`) e repassa ao Flask, **antes** de qualquer fallback de SPA, cinco
filtros que espelham os `server.proxy` dos três `vite.config.ts`: `/api/*`, `/uploads/*`,
`/catalogo/midia/*`, `/portal/photo/*` e `/figurinos/<id>/print` (regex). Alvo em `BACKEND_URL`,
com `changeOrigin: true` e `xfwd: true`; erro de conexão responde 502 sem derrubar os SPAs.

*Backend* — `app/config.py` ganhou a constante `PLATFORM_BASE_URL`
(`https://app.mantoproducoes.com.br`) e `PUBLIC_BASE_URL` passou a cair nela por padrão (antes:
string vazia). `GET /` não renderiza mais `home.html` — devolve **301** para `PLATFORM_BASE_URL`,
e as ~260 linhas do dashboard Jinja saíram de `create_app()`. `must_redirect_to_classic` saiu do
payload de `POST /api/portal/auth/login`, junto com `portal_ops.needs_classic_portal_flow` (já era
código morto desde a 191).

*Verificação* — `scripts/db/verify_206_react_primario.py` (20 checagens) e
`frontend/scripts/verify-proxy.mjs` (22 checagens: sobe um backend falso mais o `server.js` real e
confere para onde cada URL vai, inclusive com o backend fora do ar). Os quatro scripts que
afirmavam o comportamento antigo foram reapontados: `verify_136` passou a ler os reembolsos
pendentes pelo JSON do detalhe do evento, `verify_144` afirma o 301, `verify_176` e `verify_191`
afirmam a ausência de `must_redirect_to_classic`.

**Riscos e pegadinhas.**

1. **O proxy só entra em ação com `VITE_API_BASE_URL` vazia no build.** Com ela preenchida,
   `API_BASE` e `assetUrl()` geram URL absoluta do Flask e o browser fura o proxy inteiro —
   inclusive `/uploads` e a ficha de impressão. Limpar a variável no serviço frontend do Railway
   é parte do deploy, não detalhe.
2. **Ordem dos filtros é o bug óbvio que não aconteceu.** `/catalogo/midia` e `/portal/photo` são
   sub-caminhos de prefixos montados (`/catalogo`, `/portal`). Se o proxy rodasse depois dos
   mounts, cada imagem viraria o `index.html` do bundle — o mesmo gap de mídia já corrigido duas
   vezes no Vite. Por isso o bloco de proxy é a primeira coisa no handler.
3. **`changeOrigin: true` não é cosmético.** Preservar o `Host` original com `BACKEND_URL` num
   domínio público do Railway faz o roteador de borda devolver a requisição para o próprio serviço
   frontend, em laço.
4. **A regra do proxy é `/figurinos/<id>/print`, nunca `/figurinos`.** A SPA interna tem uma rota
   React Router em `/figurinos` (Banco de Figurinos); um prefixo amplo roubaria deep link e
   refresh para o Jinja. Note que `/figurinos/print-event/<id>` **não** casa o regex — de
   propósito: ela só é linkada de dentro de páginas Jinja.
5. **A home Jinja tinha blocos de tarefa que o `/api/dashboard` não expõe.** Reembolsos pendentes,
   ensaios pendentes/agendados/órfãos, presença pendente, notas fiscais a emitir, eventos sem
   valor, eventos sem cliente e pré-contratos sem cliente / que precisam de revisão sumiram com
   ela. `app/templates/home.html` ficou órfão. Reconstruir isso no React é trabalho em aberto.
6. **O 301 da raiz também vale em desenvolvimento.** `localhost:5000/` joga para produção. O ponto
   de entrada local é o Vite (`localhost:5173`), não a raiz do Flask.
7. **`BACKEND_URL` sem esquema derrubava o processo — e o sintoma apontava para o lugar errado.**
   Foi o que causou o incidente no dia da virada. O painel do Railway exibe o domínio privado como
   `mantoplatform.railway.internal`, e foi assim que a variável entrou. O `http-proxy` repassa o
   valor ao `requires-port`, que faz `protocol.split(':')` com `protocol` nulo e estoura
   `TypeError` **de forma síncrona, dentro de `proxy.web`** — antes de qualquer callback de erro.
   A exceção subia como *uncaught* e matava o Node: a página abria (o SPA era servido antes do
   crash) e cada chamada de API derrubava o servidor de novo. A borda do Railway devolvia
   `502 Application failed to respond`, que parece backend fora do ar, não falha de proxy — e
   custou uma suspeita errada sobre o Flask antes de a causa aparecer.
   Corrigido em duas camadas: `resolveBackendUrl` normaliza/valida o valor (deduz o esquema pelo
   host) e `proxy.web` roda em `try/catch`, porque nesse caminho o throw é síncrono. Valor
   inválido agora responde 502 com os três SPAs de pé.
8. **A rede privada do Railway não serve como `BACKEND_URL` hoje.** Ela é IPv6-only e o gunicorn
   sobe com `--bind 0.0.0.0` (IPv4). Usar `mantoplatform.railway.internal` só passa a ser possível
   trocando o bind para `[::]:$PORT`.
9. **`/google/*` teve de entrar nos filtros.** O callback do OAuth do Google Calendar é rota Jinja
   com `redirect_uri` fixo registrado no Google Console; apontando para este domínio, o
   consentimento voltava no fallback de SPA e a reconexão da agenda quebrava em silêncio.
10. **`portal.mantoproducoes.com.br` sumiu junto com a virada.** Antes ele apontava para o Flask,
    que o tratava em `portal_domain_routing`. Ao sair do Railway, a borda passou a apresentar o
    certificado curinga `*.up.railway.app` e o browser bloqueou — com HSTS, sem opção de exceção.
    Diagnóstico rápido para o futuro: leia o **SAN** do certificado. `*.up.railway.app` = o Railway
    não reconhece o hostname (cadastro ausente ou CNAME velho), **não** é Let's Encrypt emitindo.
    Cada domínio customizado tem um alvo de CNAME próprio; ao recadastrar, o CNAME muda.
11. **Recadastrar o domínio sozinho não resolveria.** Sem regra de host, `portal.*` entregaria
    `apps/internal/dist` — o talento cairia no login do staff, porque o bundle do portal exige o
    prefixo `/portal` (Vite `base` + `basename` do React Router). Daí o `PORTAL_HOSTS` em
    `server.js`, com redirect (não reescrita) preservando caminho e query.
12. **`fetch`/undici descarta o header `Host` silenciosamente.** A primeira versão do teste de
    roteamento por host passava `headers: { host: ... }` e media outra coisa — os casos falhavam
    por motivo errado. Teste de roteamento por host precisa de `node:http` cru.

### 205f — Loja de Interações Virtuais (resiliência a falha de serviço externo)
`205-loja-interacoes-virtuais` · **2026-08-04** · migration `c17b3ea94f52`

> Fase de **Convergence** (T129–T133), apurada pelo `/speckit.converge` sobre a 205e.

**Motivação.** Os quatro gaps que a convergência encontrou estavam todos no mesmo ponto cego: o que
acontece quando um serviço externo cai e **ninguém está olhando**. A venda se efetivava, o pedido
ficava sem sala, o e-mail não saía — e a única pista disso era uma coluna no banco que nenhuma tela
lia. Uma família chegava no horário sem link, e a equipe descobria pelo telefone.

**O que mudou.**

*Banco* — `virtual_orders.meet_attempts`/`meet_last_attempt_at`,
`virtual_order_notifications.attempts`/`last_attempt_at` e
`virtual_media_deliveries.deadline_alert_at`.

*Backend* — `virtuais_ops` ganhou `ciclo_de_varredura()`, `retentar_salas()`,
`alertar_prazos_video()`, `_entregar_aviso()`, `reenviar_aviso()`, `_enviadores_de_aviso()` e
`serialize_avisos_falhos()`. `_criar_evento_google` passou a usar `executar_com_retry`;
`regerar_sala` passou a cobrir também o caso do evento que nunca chegou a existir no Google.
`_start_virtual_sweep` roda as três rotinas do FR-057. Novo endpoint
`POST /api/virtuais/pedidos/<id>/avisos/<kind>/reenviar`.

*Frontend* — `components/AvisosFalhosBanner.tsx`, usado na Fila de Produção e no painel do evento,
com os hooks `useReenviarAviso` e `useRegerarSala`.

**Riscos e pegadinhas.**

1. **`email_service._send` engole a exceção do SMTP e devolve `False`.** Foi a pegadinha central:
   embrulhar o envio em `executar_com_retry` não retentava nada, porque a falha mais comum
   (servidor fora) chegava como retorno falso, sem exceção. `_entregar_aviso` converte o `False`
   em exceção para a política valer no caso real. O contrato de `_send` não foi tocado — ele é
   usado pelo sistema inteiro.
2. **`regerar_sala` só sabia reconsultar.** Havia dois jeitos de ficar sem sala e ela tratava um:
   o evento existir no Google e a sala não ter materializado. O outro — o evento **nunca** ter sido
   criado (id local `virtual-local-`) — ficava preso para sempre, consultando um id inexistente.
   Agora ela cria o evento e reconcilia o id.
3. **O progresso do retry é coluna, não memória.** Num caminho assíncrono o contador precisa
   sobreviver a restart de worker; se vivesse no processo, a "3ª tentativa" nunca chegaria e a
   ordem retentaria para sempre.
4. **Rollback desfaz o contador.** Quando `regerar_sala` estoura dentro de `retentar_salas`, o
   rollback apaga o incremento feito antes da falha — por isso ele é regravado no `except`. Sem
   isso a tentativa não conta e o pedido nunca esgota.
5. **Reenvio manual nunca cria linha de aviso.** Só reentrega o que já falhou. Um endpoint que
   criasse a linha seria caminho paralelo ao fluxo automático, e o `UNIQUE(order_id, kind)`
   deixaria de significar "a família recebe este aviso uma vez". Reenviar aviso já entregue dá 400.
6. **`deadline_alert_at` é idempotência, não status.** Sem ele o alerta de prazo sairia a cada
   ciclo de 60s, e alerta de minuto em minuto é alerta que se aprende a ignorar.
7. **As três rotinas são isoladas entre si** dentro de `ciclo_de_varredura` (FR-057b): uma exceção
   na expiração não pode impedir o alerta de prazo de rodar.

**Dois bugs que a própria fase revelou** (2ª passagem da convergência):

8. **O e-mail de "vídeo pronto" nunca era enviado.** `send_virtual_video_ready_email` existia em
   `email_service.py` e **não** estava no mapa de enviadores. `_enviar_aviso` gravava a linha (a
   trava de idempotência), não achava a função e voltava calado: a família não recebia nada e o
   sistema constava como tendo avisado. O teste antigo passava porque contava a linha — que é
   gravada **antes** do disparo. Só apareceu quando o painel passou a mostrar avisos falhados.
   V5.11b e V5.11c travam a classe inteira do bug.
9. **`expired_unverified` era gravado e nenhuma tela lia.** Quando o horário é liberado sem o
   sistema conseguir confirmar o pagamento, a família pode ter pago em dia e perdido o horário
   assim mesmo — e a devolução resultante era indistinguível de uma reserva que simplesmente
   venceu. Agora `_abrir_devolucao` grava `conflito_sem_confirmacao` e a tela de Devoluções
   destaca o caso (FR-018b). Registrar onde ninguém lê é o mesmo que não registrar.

**Verificação.** `verify_205.py` — **136/136 PASS**, re-rodável. O **V10** derruba os serviços com
as exceções reais (`googleapiclient.errors.HttpError` 503 e `smtplib.SMTPResponseException` 500),
e prova: a venda se efetiva mesmo assim, a varredura respeita o intervalo de 1 minuto, conta as
tentativas, desiste na 3ª, a falha aparece nos **dois** painéis, e o retorno dos serviços fecha o
fluxo de ponta a ponta sem duplicar aviso. `tsc --noEmit` limpo nos dois apps; banner conferido na
Browser pane com pedido semeado (os dois estados e a mensagem de erro do reenvio).

### 205e — Loja de Interações Virtuais (registro financeiro segregado e fechamento)
`205-loja-interacoes-virtuais` · **2026-08-04** · sem migration nova

> **Fecha a feature 205.** Cobre a fase de Financeiro segregado (T114–T119) e o Polish
> (T120–T128). Com esta entrada, as 5 user stories e os 68 requisitos funcionais estão entregues.

**Motivação.** A loja fatura em microvendas de 10 minutos, sem vendedor e sem contrato. Jogar isso
no mesmo balde dos shows quebraria três coisas ao mesmo tempo: o ticket médio (a régua que a
operação usa para precificar show), a meta do time comercial (venda que ninguém fechou) e o caixa
(comissão provisionada para um beneficiário que não existe). Ao mesmo tempo, é receita real — tem
que somar no DRE, senão o Fator R e o break-even passam a mentir.

**O que mudou.**

*Backend* — `app/financeiro/vendas_ops.py` ganhou `is_loja_virtual()`, `split_por_canal()` e
`resumo_loja_virtual()`: **fonte única** do recorte de canal. `_sync_commission_payment` e
`_event_commission` (em `app/financeiro/routes.py`) retornam cedo para venda virtual.
`app/financeiro/comissoes_ops.py` ganhou `_sem_loja_virtual()`, aplicado nas duas queries-base.
`GET /api/financeiro/dashboard` separou `todas_com_venda` (alimenta a cascata da DRE) de
`eventos_com_venda` (alimenta ticket médio e "a receber"), e passou a devolver
`paineis.loja_virtual`. `GET /api/vendas/pipeline` filtra o funil por canal e devolve
`loja_virtual` só para gestor. Ambos aceitam `?incluir_loja_virtual=1` (FR-055).

*Frontend* — `FinanceiroDashboardPage` e `VendasPipelinePage` ganharam o card consolidado do canal
e o botão de opt-in; os hooks aceitam `incluirLojaVirtual`.

**Riscos e pegadinhas.**

1. **A receita da loja NÃO sai da cascata da DRE.** Só sai dos indicadores *de evento*. Foi a
   decisão mais fácil de errar: filtrar a venda logo na query dos eventos teria "resolvido" o
   ticket médio e, de quebra, tirado dinheiro real do Fator R e do break-even — que decidem
   enquadramento tributário. Por isso existem duas listas (`todas_com_venda` e
   `eventos_com_venda`), e V9.8/V9.18 travam as duas pontas.
2. **A comissão é cortada na origem, não no relatório.** `_sync_commission_payment` retorna antes
   de criar a linha. Se a linha nunca nasce, nenhum relatório futuro precisa lembrar de escondê-la.
   `_sem_loja_virtual()` em `comissoes_ops` é a segunda trava, para linhas anteriores à feature —
   e usa `NOT EXISTS`, não `JOIN`, para não derrubar estornos (que têm `event_id IS NULL`).
3. **"Loja Virtual" vira barra própria em `receita_por_tipo`, mas `VIRTUAL` não.** A visão por
   canal é exatamente onde a loja *deve* aparecer; omiti-la ali esconderia receita do gestor. O que
   não pode é o tipo cru `VIRTUAL` aparecer diluído entre SHOW/OFICINA (V9.13).
4. **Vendedor comum nunca recebe o bloco `loja_virtual`,** nem com `?incluir_loja_virtual=1`: o
   opt-in é ignorado quando `can_filter_seller` é falso. Escopo é decisão do servidor.
5. **O teste precisa de um evento presencial de controle.** Sem ele, "o indicador não mudou" seria
   `0 == 0` e passaria com todos os filtros quebrados. V9 cria um SHOW de R$ 1.000 no dia da
   medição justamente para haver o que distorcer.

**Verificação.** `verify_205.py` — **110/110 PASS** contra `manto_local`, re-rodável e sem resíduo.
V9 mede volume, ticket médio e base de comissão antes e depois de 10 vendas virtuais (os três
ficam idênticos; o DRE sobe exatamente R$ 1.500). `tsc --noEmit` limpo em `apps/internal` e
`apps/public`. Mobile conferido no Browser pane a **320px e 430px** nas duas telas públicas: zero
scroll horizontal, zero alvo abaixo de 44px, zero texto abaixo de 12px.

### 205d — Loja de Interações Virtuais (presente 3D, fila de produção e entrega do vídeo)
`205-loja-interacoes-virtuais` · **2026-07-31** · sem migration nova

> **Entrega parcial.** Cobre US4 e US5 (T090–T113). Falta apenas a segregação financeira
> (T114–T119) e o fechamento (T120–T128).

**Motivação.** Fechar o produto ponta a ponta: o upsell de presente 3D no checkout, a fila que a
produção usa para saber o que gravar, e a entrega do vídeo com os dados da criança protegidos.

**O que mudou.**

*Backend* — `virtuais_ops` ganhou `verificar_telefone()`, `salvar_video_entrega()`,
`caminho_video()`, `atualizar_status_entrega()`, `listar_fila_producao()`, `serialize_delivery()`,
`serialize_order_full()` e `_whatsapp_url()`. Endpoints públicos de verificação, pedido completo e
vídeo; endpoints internos da fila. `Config.VIRTUAL_VIDEO_FOLDER` novo.

*Frontend* — `FilaProducaoMidiaPage`, validação por telefone + player na `PedidoVirtualPage`, e o
seletor de presente no checkout.

**Riscos e pegadinhas.**

1. **O vídeo mora fora de `UPLOAD_FOLDER`, e isso não é detalhe.** `/uploads/<path>` é uma rota
   servida e, com `USE_S3=true`, o `save_file` devolveria uma URL de bucket **público**. Por isso
   `salvar_video_entrega` grava direto em `VIRTUAL_VIDEO_FOLDER` (irmão de `uploads`) e o arquivo
   só sai por `GET /api/virtuais/pedidos/<token>/video`, que valida a sessão a cada requisição
   (FR-038e). `video_path` **nunca** aparece em payload — V6.3 e V6.6 travam isso.
2. **`send_file(conditional=True)` é o que faz o player funcionar.** Sem `206`/`Range`, arrastar a
   barra do vídeo baixaria o arquivo inteiro de novo. O teste checa a resposta parcial real, não o
   cabeçalho `Accept-Ranges` (que o test client não expõe).
3. **Vídeo gravado não ganha sala do Meet.** Era um bug: a família que comprava um vídeo via
   "Entrar na chamada" num produto sem chamada. `_criar_evento_google` só pede `conferenceData`
   quando a modalidade é `ao_vivo`, e `meet_pending` também passou a ser condicionado — senão a
   fila mostraria "sala pendente" para algo que nunca terá sala. V5.10b trava a regressão.
4. **A sessão de acesso vive no cookie do Flask** e expira por **inatividade** (30 min), renovando
   a cada acesso. Cinco erros de telefone bloqueiam por 15 min (FR-044b) — sem isso, o telefone
   seria adivinhável por quem tropeçasse no link.
5. **Presente 3D acima de 10 peças usa `Combobox`; abaixo, grade visual.** O Princípio XII.1 exige
   o combobox pesquisável a partir de 10 itens; com poucas peças, ver o presente é melhor que ler
   uma lista no celular.
6. **A fila mostra `pendente`/`gravando`/`finalizado` e nada mais** (FR-048a). Enviar o vídeo é a
   ação que permite chegar a `finalizado`; finalizar sem vídeo é recusado no servidor (V5.6).

**Verificação.** `verify_205.py` — **90/90 PASS**. V4 (upsell e injeção na Fila 3D), V5 (fila,
fluxo de status, envio e falha de envio) e V6 (validação dupla, bloqueio por tentativas e varredura
de vazamento). Mobile conferido em 375px.

### 205c — Loja de Interações Virtuais (efetivação automática da venda)
`205-loja-interacoes-virtuais` · **2026-07-31** · sem migration nova

> **Entrega parcial.** Cobre a US3 (T059–T089). A venda agora vira operação sozinha. Faltam o
> upsell 3D no checkout (US4), a fila de produção com entrega de vídeo (US5) e a segregação
> financeira.

**Motivação.** Fechar a promessa de "atrito zero": pagamento confirmado devia virar evento na
Agenda, escala de talento, sala de chamada e aviso à família — sem ninguém digitar nada.

**O que mudou.**

*Backend* — `virtuais_ops` ganhou `processar_notificacao_pagamento()`, `efetivar_pedido()`,
`_abrir_devolucao()`, `_enviar_aviso()`, `extrair_meet_url()` e `regerar_sala()`.
`calendar/service.insert_event()` passou a aceitar `conference_request_id` (sala do Meet via
`conferenceData` + `conferenceDataVersion=1`). `calendar/routes` ganhou `_is_virtual_event()` e
`_sinalizar_divergencia_virtual()`. Três e-mails novos em `email_service`. Webhook, endpoints de
sala e de devoluções.

*Frontend* — `PedidoVirtualSection` no detalhe do evento (ficha + sala), acesso à chamada na
página do pedido e a tela `/virtuais/devolucoes`.

**Riscos e pegadinhas.**

1. **A sincronização não encosta em evento virtual.** `sync_events` e `_cleanup_stale_events`
   pulam `event_type='VIRTUAL'` (FR-029a/029b). Sem isso, editar o evento no Google reescreveria
   uma venda paga, e apagá-lo lá **deletaria em cascata** o evento, a escala e o presente 3D de um
   pedido pago. Divergência vira log `virtual_divergente`, nunca propagação.
2. **`parse_event_type` deriva o tipo do prefixo `(TIPO)` do título.** Eventos virtuais não têm
   esse prefixo, então o payload da agenda dizia `event_type: ""` e a seção nunca renderizaria.
   `_event_type_serializado()` faz o fallback **só** para `VIRTUAL`, para não mudar o que a agenda
   devolve nos demais tipos.
3. **Idempotência tem duas travas, e as duas são do banco.** `UNIQUE(transaction_nsu)` barra a
   reentrega do webhook; `UNIQUE(order_id, kind)` barra o segundo e-mail. Ambas gravadas **antes**
   da ação, para a violação decidir — não a confiança no fluxo.
4. **Sem id do Google, a venda ainda acontece.** Se a criação do evento externo falhar, o
   `CalendarEvent` nasce com `google_event_id = "virtual-local-<nsu>"` e `meet_pending=True`. A
   coluna é NOT NULL e única; a venda não pode cair porque o Google estava fora.
5. **A sala fica fora da validação dupla, de propósito.** Ela aparece na página do pedido assim
   que o pagamento confirma — pedir mais uma etapa antes de uma chamada de 10 minutos custaria a
   experiência inteira. Nome, idade, dicas, endereço e vídeo seguem protegidos (FR-044a).
6. **`virtual_payment_notifications` sobrevive ao pedido** (a FK é anulada, não cascateada) — é
   auditoria. Consequência prática: um script de teste que reusa `transaction_nsu` bate em
   "duplicado" na segunda execução; por isso `verify_205.py` prefixa os ids com um `RUN_ID`.

**Verificação.** `verify_205.py` — **60/60 PASS**, incluindo reentrega quíntupla sem duplicar
nada, segredo inválido, não pago, valor divergente, operadora indisponível, aviso órfão, conflito
com devolução e a sincronização completa sem tocar nos eventos virtuais.

### 205b — Loja de Interações Virtuais (checkout público e soft lock)
`205-loja-interacoes-virtuais` · **2026-07-31** · migration **`a5c81e0cd247`** (*client_token do
pedido e lock da varredura virtual*)

> **Entrega parcial.** Cobre a US2 (T035–T058). O canal vende até "aguardando pagamento": o
> webhook ainda não processa nada, então a venda não vira operação sozinha (US3).

**Motivação.** Dar à família o caminho completo de compra sem falar com ninguém — landing,
checkout, reserva de horário com soft lock e link de pagamento — e um lugar para onde voltar
depois de pagar.

**O que mudou.**

*Banco* — `virtual_orders.client_token` (idempotência de duplo clique) e
`site_settings.virtual_sweep_at` (lock de execução única da varredura).

*Backend* — `virtuais_ops` ganhou `reservar()` com `with_for_update()`, os dois limites
anti-abuso, `expirar_reservas()` com reconsulta antes de liberar, `claim_sweep()` e a política de
retry. Endpoints públicos de landing, horários, reserva, pedido e autocomplete de endereço.
Thread `_start_virtual_sweep` em `create_app()`. `Config.PUBLIC_BASE_URL` e
`Config.VIRTUAL_SWEEP_INTERVAL`.

*Frontend* — `CampanhaVirtualPage` e `PedidoVirtualPage` no app público, rotas `/v/:slug` e
`/v/pedido/:token`. `GoogleAddressInput` **promovido** para `@manto/ui` e o hook de autocomplete
para `@manto/api-client` (parametrizado pelo endpoint); cada app ficou com um binding de ~10
linhas. `apps/internal/src/lib/maps.ts` foi removido. Proxy `/uploads` acrescentado ao
`vite.config.ts` do app público.

**Riscos e pegadinhas.**

1. **Um relógio só, e ele é São Paulo.** A feature usa `constants.now_sp()` em tudo — horário de
   slot, soft lock, janela do anti-abuso e os `created_at` das tabelas `virtual_*`. Foi um bug
   real encontrado na tela: com `datetime.utcnow()` o contador do soft lock mostrava **191
   minutos** em vez de 12, e horários das próximas 3h sumiam da lista. O resto do sistema segue
   com `utcnow` nos carimbos de auditoria; **não misture dentro desta feature**.
2. **FK circular entre `virtual_orders` e `virtual_campaign_slots`.** O slot aponta para o pedido
   e o pedido aponta para o slot. Para apagar uma campanha é preciso anular `slot.order_id`,
   apagar os pedidos e só então a campanha — ver `limpar_campanha()` em `verify_205.py`.
3. **A página do pedido consulta com a aba em segundo plano** (`refetchIntervalInBackground`) e
   revalida ao voltar o foco. É o caso normal: a família vai pagar em outra aba. Com os padrões
   globais do app (`staleTime: 30s`, `refetchOnWindowFocus: false`) ela voltaria para uma tela
   congelada em "aguardando".
4. **A operadora fica fora da transação do soft lock.** Uma chamada HTTP lenta não pode segurar o
   lock do slot no banco; se ela falha, a reserva é desfeita e o horário volta ao estoque.
   Verificado na tela: erro amigável, tudo que a família digitou preservado, slot livre de novo.
5. **`client_token` ≠ `origin_hash`.** Duas famílias atrás do mesmo NAT compartilham origem; usar
   a origem como chave de idempotência entregaria o pedido de uma para a outra.

**Verificação.** `verify_205.py` — **35/35 PASS**, incluindo a disputa simultânea com duas
conexões reais (V2.7/V2.8). Mobile conferido em 375px e 320px: sem rolagem horizontal, nenhum alvo
abaixo de 44px, nenhum texto abaixo de 12px.

### 205 — Loja de Interações Virtuais (fundação + gestão de campanhas)
`205-loja-interacoes-virtuais` · **2026-07-31** · migration **`f3a9c72e5d18`** (*loja de
interacoes virtuais*)

> **Entrega parcial.** Este registro cobre Setup + Foundational + US1 (T001–T034 de
> `specs/205-loja-interacoes-virtuais/tasks.md`). O checkout público, o webhook de pagamento, a
> fila de produção e a segregação financeira (US2–US5 + fase Financeiro) ainda não foram
> implementados — o schema já os contempla, mas o código deles não existe.

**Motivação.** Criar um canal B2C self-service que venda chamadas de vídeo de 10 minutos e vídeos
gravados com Personagens do catálogo, com atrito comercial zero: a família compra sozinha e a
entrega operacional (evento na agenda, escala de talento, presente 3D) nasce automática.

**O que mudou.**

*Banco* — sete tabelas novas (`virtual_campaigns`, `virtual_campaign_slots`, `virtual_orders`,
`virtual_payment_notifications`, `virtual_media_deliveries`, `virtual_refund_requests`,
`virtual_order_notifications`) mais a associação `virtual_campaign_acervo`. Dois campos novos em
`site_settings`: `infinitepay_handle` e `infinitepay_webhook_token`. Migration 100% aditiva.

*Backend* — `app/marketing/virtuais_ops.py` (núcleo: CRUD de campanha, geração de horários, acervo
liberado, serializers); `app/integracoes/infinitepay_client.py` (cliente da operadora);
`app/api/virtuais_{public,read,write,webhook}.py`. Constantes da feature em `app/constants.py`.

*Frontend* — `frontend/apps/internal/src/lib/virtuais.ts` (tipos + hooks TanStack Query),
`VirtuaisCampanhasPage.tsx` (listagem) e `VirtuaisCampanhaFormPage.tsx` (edição, geração de
horários, seleção de acervo via `Combobox` + `AvatarThumb`). Item de menu em `navigation.tsx`.

**Impacto em RBAC.** Novo gate `require_virtuais_access()` — `COMERCIAL` ou `SUPERADMIN`
(`VIRTUAIS_ADMIN_ROLES` em `constants.py`). Nenhum papel novo foi criado.

**Rotas e endpoints novos.**

| Método | Rota | Acesso |
|---|---|---|
| GET | `/api/virtuais/campanhas` | COMERCIAL/SUPERADMIN |
| POST | `/api/virtuais/campanhas` | COMERCIAL/SUPERADMIN |
| GET | `/api/virtuais/campanhas/<id>/admin` | COMERCIAL/SUPERADMIN |
| PATCH | `/api/virtuais/campanhas/<id>` | COMERCIAL/SUPERADMIN |
| POST | `/api/virtuais/campanhas/<id>/publicar` | COMERCIAL/SUPERADMIN |
| PUT | `/api/virtuais/campanhas/<id>/acervo` | COMERCIAL/SUPERADMIN |
| POST | `/api/virtuais/campanhas/<id>/horarios` | COMERCIAL/SUPERADMIN |
| DELETE | `/api/virtuais/horarios/<id>` | COMERCIAL/SUPERADMIN |
| GET | `/api/virtuais/campanhas/<slug>` | **público** |
| GET | `/api/virtuais/campanhas/<slug>/horarios` | **público** |
| POST | `/api/webhooks/infinitepay/<token>` | **público, com segredo no path** |

Frontend: `/virtuais/campanhas` e `/virtuais/campanhas/:id`.

**Riscos e pegadinhas.**

1. **Dinheiro nunca em centavos fora do cliente da operadora.** A InfinitePay exige centavos
   inteiros; o resto do sistema é `Numeric(12,2)`/`Decimal` (Princípio IX). A conversão vive
   exclusivamente em `infinitepay_client.py`, que recusa `float` com `TypeError` de propósito.
   Nenhuma coluna ou campo de API termina em `_cents`.
2. **O webhook não decide nada.** A InfinitePay **não assina** seus webhooks e **não publica API
   de estorno** (levantado na pesquisa da feature). A confiança vem do `payment_check`, não do
   aviso. O endpoint só valida o segredo do path e responde `404` quando ele falha — `403`
   confirmaria que o endereço existe.
3. **Responder `400` no webhook faz a operadora reenviar em loop.** Por isso duplicata, pedido
   inexistente e conflito respondem `200`; o que precisa de atenção vira registro, não status HTTP.
4. **Campanha pausada responde `410`, rascunho responde `404`.** A diferença importa para a
   família saber se errou o endereço ou se a campanha saiu do ar.
5. **`uq_virtual_slot_campaign_start`** é o que torna a geração de horários idempotente;
   **`uq_virtual_order_notification_kind`** e o `UNIQUE(transaction_nsu)` são as travas que impedem
   evento/escala/presente/aviso duplicados quando o webhook é reentregue.
6. **Eventos virtuais nascerão com `event_type='VIRTUAL'` e `source='platform'`** e a sincronização
   com o Google Calendar precisa ignorá-los em **todos** os caminhos (importação, atualização,
   remoção) — ainda **não implementado**, entra na US3. Sem isso, a sincronização corromperia um
   evento já pago.
7. **`VirtualOrder.meet_url` ≠ `CalendarEvent.google_html_link`.** O segundo abre o Google Calendar
   e exige login; o que a família recebe é o link da sala do Meet.

**Verificação.** `specs/205-loja-interacoes-virtuais/verify_205.py` — 18/18 PASS contra
`manto_local` (V0: fundação monetária; V1: campanha, idempotência de horários, RBAC, 404/410).

### 204b — Múltiplos Temas por postagem de marketing
`204b-marketing-multiplos-temas` · **2026-07-29** · migration **`b7d4f81a6e0c`** (*marketing
posts com multiplos temas do catalogo*)

**Motivação.** A feature 204 vinculava cada `MarketingPost` a **um** Tema do catálogo
(`catalog_item_id`), mas a equipe frequentemente junta vários Temas no mesmo vídeo/post (ex.: um
Reels que mistura "15 Anos" e "Debutante"). Pedido do usuário para permitir múltiplos Temas por
postagem.

**O que mudou.**

- **Banco.** `marketing_posts.catalog_item_id` (FK única) virou N:N via a tabela nova
  `marketing_post_temas` (`post_id`, `catalog_item_id`, FKs `ON DELETE CASCADE` dos dois lados).
  A migration migra os dados existentes (cada `catalog_item_id` preenchido vira uma linha na
  tabela nova) antes de remover a coluna antiga — nenhum vínculo se perde. `downgrade()` restaura
  a coluna, mas com perda: só o Tema de menor id volta quando um post tinha mais de um.
  `marketing_frequency_goals.catalog_item_id` não muda — a meta continua mirando em **um** Tema.
- **Backend.** `MarketingPost.temas` (relationship N:N, `lazy="joined"`) substitui
  `MarketingPost.catalog_item`. `marketing_ops.py`: `_resolve_catalog_items()` (lista, dedup,
  valida cada id) substitui `_resolve_catalog_item()` para posts; `create_post`/`update_post`
  recebem `catalog_item_ids` (lista) em vez de `catalog_item_id`; `serialize_post()` devolve
  `catalog_item_ids`/`catalog_items` (plural). O casamento de `last_published_post()` com a meta
  de frequência mudou de "post.catalog_item_id == goal.catalog_item_id" para "qualquer um dos
  Temas do post bate com o da meta" (`MarketingPost.temas.any(...)`) — um post multi-Tema conta
  para a meta de cada um dos seus Temas.
- **Frontend.** `MarketingPost.catalog_item_ids`/`catalog_items` (arrays) substituem os campos
  singulares em `lib/marketing.ts`. `MarketingPostDialog.tsx` ganhou `TemasMultiSelect` — compõe
  o `Combobox` existente (que continua single-select) como "adicionar" mais uma lista de chips
  removíveis abaixo, sem precisar de um componente multi-select novo no design system. Kanban e
  tabela do painel mostram os nomes dos Temas concatenados (`join(", ")`) e a capa do primeiro.

**RBAC.** Sem mudança — mesmo gate (`MARKETING`/`SUPERADMIN`) de antes.

**Pegadinhas.**
1. **Bug real encontrado e corrigido durante a verificação**: a primeira versão de
   `TemasMultiSelect` calculava o próximo array de ids a partir do `selectedIds` fechado no
   closure do `onChange` do `Combobox` (`onChange([...selectedIds, next])`). Em dev, o `Combobox`
   dispara `onChange` mais de uma vez por seleção (efeito colateral observável do `StrictMode`) —
   as chamadas duplicadas usavam o mesmo `selectedIds` desatualizado e a seleção anterior era
   perdida na 2ª escolha. Corrigido trocando para um *updater* funcional
   (`onChange: (updater: (prev) => prev) => void`, igual ao setter do `useState`) — imune a
   fechos desatualizados porque sempre aplica sobre o estado mais recente do React, nunca sobre um
   valor capturado.
2. O `Combobox` recebe `key={selectedIds.join(",")}` em `TemasMultiSelect`: sem isso, a lista de
   opções (`options`) já filtrada corretamente não refletia visualmente a exclusão do item recém
   selecionado — o `useMemo` interno do `Combobox` não invalidava a lista renderizada mesmo com a
   prop `options` trocando de referência a cada seleção. Forçar o remount por `key` é mais robusto
   que depender desse `useMemo`.
3. Verificado por teste funcional (test client Flask contra `manto_local`) e manualmente no
   Browser pane: criação com 2 Temas, PATCH removendo um, PATCH limpando todos, tema inexistente
   devolvendo 400 em `catalog_item_ids`, e o fluxo completo criar → aparecer no Kanban com os dois
   nomes de Tema.

---

### 204 — Módulo de Gestão de Marketing e Frequência
`204-modulo-marketing-frequencia` · **2026-07-29** · migration **`a3c7e1d59f42`** (*modulo de
gestao de marketing e frequencia*)

> **Sobre o número.** O pedido pediu para registrar como "202", mas 202 (Fila de Impressão dirigida
> pelo evento) e 203 (Melhorias na Comunicação e Alertas de E-mail) já estavam no histórico. Usei
> **204** para manter o append-only sem sobrescrever entrada existente — mesma decisão registrada
> na pegadinha nº 2 da entrada 203.

**Motivação.** O planejamento de conteúdo do marketing vivia fora do ERP (planilha + pastas do
Drive + mensagens), enquanto as duas informações de que ele mais depende já moravam aqui: o
**Tema do catálogo** (o que o post divulga) e o **espaço de Revisão de Mídia** (onde o material é
aprovado, feature 088). Faltava também um jeito de cobrar a **frequência** combinada em reunião
("postar sobre 15 Anos a cada 15 dias") — sem isso, "faz tempo que não postamos disso" era
memória, não dado.

**O que mudou.**

- **Banco.** Duas tabelas novas, 100% aditivas.
  - `marketing_posts` (`MarketingPost`) — o card do Kanban: `title`, `status`
    (`ideia`→`producao`→`revisao`→`agendado`→`publicado`), `deadline_date`, `publish_date`,
    `platform`, `drive_folder_url` (texto — o acervo bruto continua no Drive), `notes`,
    `created_at`/`updated_at`. FKs `assignee_id`→`users`, `catalog_item_id`→`catalog_items` e
    `review_space_id`→`review_spaces`, **todas `ON DELETE SET NULL`** (apagar usuário/Tema/espaço
    não pode apagar o planejamento) e `review_space_id` **UNIQUE** (o vínculo é 1:1). Índices em
    `status`, `catalog_item_id` e `publish_date`.
  - `marketing_frequency_goals` (`MarketingFrequencyGoal`) — `name`, `target_interval_days`,
    `catalog_item_id` opcional (`SET NULL`). **Sem coluna de estado de cumprimento**, de propósito.
  - Constantes novas em `app/constants.py`: `MARKETING_STATUSES`, `MARKETING_PLATFORMS` (7 itens) e
    `MARKETING_MAX_INTERVAL_DAYS` (1825).
- **Backend.**
  - Novo núcleo `app/marketing/marketing_ops.py` (funções puras, fonte única): CRUD de posts e
    metas com `MarketingValidationError(field, message)`; `goal_health()` e `last_published_post()`
    (o motor de frequência); serializadores dos payloads; e `attach_review_space()`, que **reusa
    `review_ops.create_space`** em vez de montar um `ReviewSpace` à mão (Princípio I).
  - `app/api/marketing_read.py` — `GET /api/marketing/posts` (com `?status=`/`?responsavel=`),
    `GET /api/marketing/posts/<id>`, `GET /api/marketing/goals` e `GET /api/marketing/opcoes`.
  - `app/api/marketing_write.py` — `POST /api/marketing/posts`,
    `PATCH|DELETE /api/marketing/posts/<id>`, `POST /api/marketing/posts/<id>/create-review` e o
    CRUD de `/api/marketing/goals[/<id>]`.
  - Gate `require_marketing_access()` (`MARKETING` ou `SUPERADMIN`), função chamada no início de
    cada view — não decorator, como no resto da camada de API.
  - **Duas regras de negócio que não estavam no pedido e foram necessárias**: (1) marcar um post
    como `publicado` sem data **preenche `publish_date` com hoje** — sem data o post não contaria
    para nenhuma meta e a frequência ficaria eternamente "atrasada"; (2) `drive_folder_url` só
    aceita `http(s)`, porque o valor vai para um `href` com `target="_blank"`.
- **Frontend.**
  - `lib/marketing.ts` — tipos + hooks TanStack (fonte única do contrato). `useMoveMarketingPost`
    faz **atualização otimista** (com rollback em `onError`): o card precisa começar a andar no
    clique, senão a animação de `layoutId` não comunica causa e efeito.
  - `components/MarketingKanban.tsx` — 5 colunas, cards com `layoutId` dentro de um `LayoutGroup` e
    `<AnimatePresence>`; animações desligadas sob `useReducedMotion()`. **Mover tem dois caminhos**:
    **arrastar e soltar** (`drag` do Framer com `whileDrag`, `dragSnapToOrigin`, `dragConstraints`
    no quadro, realce da coluna alvo e "Solte aqui" na coluna vazia) e as **setas ◀ ▶**, que
    continuam sendo o caminho de teclado e de tela estreita. O alvo do drop sai de
    `elementsFromPoint` em coordenadas de viewport; soltar fora de uma coluna (ou na mesma) não
    dispara requisição.
  - `components/MarketingPostDialog.tsx` — formulário único (criação e edição) com `Combobox` +
    `AvatarThumb` para Tema (quadrada) e responsável (circular), botão dourado "Abrir Acervo de
    Mídia no Drive" e a ponte "Criar Espaço de Revisão" ⇄ "Ir para Revisão →".
  - `components/MarketingGoalDialog.tsx` e `pages/MarketingMetasPage.tsx` — o *Health Dashboard*:
    faixa de resumo, cards ordenados por urgência com selo + ícone + barra de consumo do intervalo.
  - `pages/MarketingPainelPage.tsx` — alternador Tabela ⇄ Kanban persistido em `localStorage`
    (`manto_marketing_painel_view`, mesmo padrão de `/admin/catalogo`), com o "trilho" do item ativo
    animado por `layoutId` e a troca de visão em `AnimatePresence mode="wait"`.
  - `App.tsx` (rotas `/marketing/painel` e `/marketing/metas`) e `lib/navigation.tsx` (seção
    "Marketing" entre "Impressão 3D" e "Comercial", visível para `MARKETING`/`SUPERADMIN`).

**Impacto em RBAC e regras de negócio.** Nenhum papel novo — `MARKETING` (que existia desde a 088
só para criar espaços de revisão) ganhou um módulo próprio, e `SUPERADMIN` acompanha. `MARKETING`
passa a **ler** os Temas ativos do catálogo por `GET /api/marketing/opcoes`, sem ganhar acesso ao
gerenciador de catálogo (que segue exclusivo de `SUPERADMIN`). Regras novas: post publicado sem
data recebe a data de hoje; a saúde da meta é sempre derivada dos posts publicados (nunca
armazenada); postagem e espaço de revisão são 1:1; excluir a postagem **não** apaga o espaço.

**Riscos e pegadinhas descobertos.**
1. **`AnimatePresence mode="popLayout"` quebra com componente de função.** O wrapper `PopChild` do
   Framer injeta uma `ref` no filho direto; como o filho é `<KanbanCard>` (função, sem
   `forwardRef`), o console enchia de *"Function components cannot be given refs"*. Resolvido
   ficando no `mode` padrão (`sync`) — a alternativa seria envolver o card em `forwardRef` só para
   satisfazer o wrapper.
2. **Dialog não pode receber uma cópia do registro em `useState`.** A primeira versão guardava o
   `post` selecionado em estado; depois de `create-review` o servidor mudava o post, o cache era
   invalidado, mas o Dialog seguia mostrando "Criar Espaço de Revisão" (cópia velha). Corrigido
   guardando **só o id** e lendo o registro do cache do TanStack Query — vale para qualquer Dialog
   que sofra efeito colateral de API sobre o item aberto.
3. **`ILIKE` com o nome da meta precisa escapar curingas.** Uma meta chamada `%` casaria com todo
   post publicado; `_escape_like` neutraliza `\`, `%` e `_` e o filtro passa `escape="\\"`.
4. **A verificação visual no Browser pane engana com animações.** Sem o painel visível a página não
   compõe frames: transições de saída do Framer **não terminam**, então o card "fantasma" fica na
   coluna antiga e a troca Tabela⇄Kanban (`mode="wait"`) parece travada. Confirmação real veio
   recarregando a rota com a visão já persistida (tabela renderizou com as 8 colunas e 4 linhas) —
   é artefato da ferramenta, não da tela.
5. **Drag do Framer dentro de container com `overflow-x-auto` precisa de `dragConstraints`.** Como
   um eixo `auto` promove o outro a `auto`, o quadro recorta o card nos dois sentidos durante o
   gesto (e ganha barra de rolagem). Limitar o arraste ao próprio quadro resolve sem tirar a
   rolagem horizontal das colunas. E o **`click` chega depois do `pointerup`**: sem a guarda de
   `ref` ("houve arraste?"), todo drop terminava abrindo o Dialog de edição.
6. **Hit-test do drop: use `elementsFromPoint`, não `getBoundingClientRect` das colunas.** A pilha
   de elementos alcança a coluna mesmo com o card levantado por cima dela, e evita remedir 5 colunas
   a cada quadro. Duas pegadinhas: o ponto tem de estar em coordenadas de **viewport**
   (`event.clientX/clientY`; `info.point` do Framer é coordenada de **página** e erra o alvo com a
   janela rolada), e no toque o dedo que soltou está em `changedTouches`, não em `touches`.
7. **`ruff format` não é neutro nos arquivos vizinhos.** `impressoes3d_ops.py`/`impressoes3d_*.py`
   não passam `ruff format --check` (o estilo compacto de `audit(...)` em uma linha). Os arquivos
   novos desta feature foram formatados (regra do `CLAUDE.md` para arquivo novo) e o `ruff check`
   está limpo; a divergência de estilo com os vizinhos é conhecida e não foi propagada para eles.

**Verificação.** `scripts/db/verify_204_marketing.py` — **62/62 checks** contra `manto_local`
(Postgres): RBAC (401/403/200), validação campo a campo dos 6 campos rejeitáveis, payload com
Tema/responsável/espaço aninhados, filtro por status, `publish_date` automática e preservada,
`PATCH` parcial não zerando o que não foi enviado, `create-review` (título, criador, 1:1 e o 400 do
segundo), motor de metas (casamento por Tema e por nome, `days_late`, `next_due_date`,
`never_posted`, `delayed_count`, recálculo no `PATCH`) e as exclusões com o espaço de revisão
sobrevivendo. Migration aplicada com **round-trip `downgrade`/`upgrade`** no `manto_local`.
Frontend: `npm run typecheck` (os 3 apps) e `npm run build` do app internal limpos; telas
conferidas no app real com dados temporários (Kanban movendo card com `PATCH 200`, Dialog com
Combobox preenchido, ponte de revisão criando `/revisao/33`, tabela persistida, metas passando de
`ATRASADO 15D` para `EM DIA` ao trocar o intervalo, sem rolagem horizontal em 375px).
**Drag-and-drop** exercitado com sequência real de `pointerdown`/`pointermove`/`pointerup`: card
saiu de "Ideia" e chegou em "Agendado" com `PATCH 200`, coluna alvo realçada durante o gesto, drop
fora de coluna não moveu nada nem gerou requisição, e o arraste não abriu o Dialog (o clique simples
continua abrindo).

---

### 203 — Melhorias na Comunicação e Alertas de E-mail
`203-melhorias-comunicacao-email` · **2026-07-29** · sem migration

**Motivação.** A auditoria de e-mails (feature 191) veio o mapeamento dos 8 gatilhos existentes.
A partir dele, três lacunas de cobertura foram fechadas: o alerta de "evento alterado" não avisava
o talento quando o evento passava a exigir ensaio (só a equipe interna era avisada); o alerta
interno de ENSAIO era o único e-mail do sistema em texto plano, destoando da identidade visual dos
demais; e não havia alerta nenhum para o Financeiro quando um gasto extra era lançado — a
aprovação dependia de alguém abrir a tela por conta própria.

**O que mudou.**

- **Backend.**
  - `app/calendar/event_ops.py::save_logistics` — a transição `needs_rehearsal`
    desligado→ligado agora entra na lista de mudanças de `notify_accepted_roles`
    (`send_event_changed_email`, ao talento) **além** de continuar disparando
    `notify_ensaio_team` (`send_ensaio_alert_email`, à equipe interna). Antes, só a equipe
    de ENSAIO era avisada; o talento com cargo aceito não sabia que o evento passou a exigir
    ensaio.
  - `app/email_service.py::send_ensaio_alert_email` — trocado de texto plano para HTML,
    reusando os mesmos helpers de template (`_html_wrap`/`_greeting`/`_info_box`/`_alert_box`)
    dos outros 7 e-mails do sistema — mesma identidade visual (cabeçalho "Manto Produções",
    cores, tipografia). Não foi criado um arquivo `.html` de template à parte: o projeto não tem
    esse mecanismo para e-mails (todos os 8 já eram — e continuam sendo — montados por funções
    Python no próprio `email_service.py`); seguir esse padrão evita duas formas paralelas de
    gerar o mesmo tipo de conteúdo.
  - **Novo 9º gatilho** — `app/email_service.py::send_new_expense_alert_email(expense, users)`:
    alerta HTML curto e direto ("novo gasto extra cadastrado... verifique no sistema para
    aprovação"), com descrição/categoria/valor/evento (quando vinculado) em destaque. Protegido
    pela mesma `_emails_enabled()`/`SiteSetting.email_notifications_enabled` dos demais 8.
  - `app/gastos/gastos_ops.py::create_expense` — ao final da criação de um `SpecialExpense`,
    busca (`_financeiro_and_superadmin_users`) todos os usuários **ativos** com papel FINANCEIRO
    ou SUPERADMIN e dispara o alerta acima via `send_async` (best-effort, não bloqueia a
    requisição). Fonte única: dispara para as duas rotas que chamam `create_expense`
    (`app/api/gastos_write.py` e o Jinja legado de `app/gastos/routes.py`), sem duplicar lógica.

**Impacto em RBAC e regras de negócio.** Nenhuma mudança de RBAC. Regra nova: todo `SpecialExpense`
criado gera um alerta best-effort para FINANCEIRO/SUPERADMIN ativos (usuários inativos ou de
outros papéis, incluindo quem criou o gasto, não recebem). O total de gatilhos de e-mail do
sistema passa de 8 para 9, todos atrás da mesma chave geral.

**Riscos e pegadinhas descobertos.**
1. **A pergunta "o alerta já verifica data/hora/local do evento?" tem resposta não-óbvia: NÃO.**
   `send_event_changed_email` hoje só dispara por mudanças de logística (horário/local de
   saída/maquiagem, em `save_logistics`) e por mudança de cachê (`casting_ops.py`) — a edição em
   bloco do evento (`event_ops.py::update_core`, título/data/horário/local/descrição, usada pelo
   `PATCH /api/events/<id>`) **não** chama `notify_accepted_roles`. Ou seja, hoje um talento com
   cargo aceito **não é avisado** se o horário ou local do próprio evento mudar por essa tela —
   só se a logística (saída/maquiagem) ou o cachê mudarem. Isso não foi alterado nesta feature
   (não fazia parte do pedido) — fica registrado como lacuna candidata a uma próxima feature, a
   confirmar com o usuário antes de mexer (mudaria o comportamento de uma rota já em produção).
2. **O número desta entrada não é o "201" pedido originalmente** — a numeração já havia avançado
   para 201 (Acervo 3D multi-arquivos) e 202 (Fila de Impressão 3D) antes desta tarefa; usei 203
   para manter o append-only sem sobrescrever histórico.

**Verificação.** `scripts/db/verify_203_email_melhorias.py` — 14/14 checks contra `manto_local`
(Postgres): transição de ensaio disparando os dois alertas (interno + talento) com a mudança
correta na lista, ausência de disparo duplicado num 2º save sem mudança real, criação de gasto
via `POST /api/gastos` alertando FINANCEIRO+SUPERADMIN ativos e excluindo quem criou o gasto,
ENSAIO e FINANCEIRO inativo. Geração de HTML das 3 funções de e-mail tocadas (`send_ensaio_alert_email`,
`send_new_expense_alert_email` com e sem evento vinculado) exercitada à parte, sem exceções.

---

### 202 — Fila de Impressão dirigida pelo evento
`202-fila-3d-por-evento` · **2026-07-29** · migration **`e4f7b2c9a350`** (*pendencia 3d por evento
show*)

**Motivação.** Com a 200 no ar, o usuário abriu `/3d/fila` em produção e viu **vazio**, apesar de
haver 23 shows futuros na agenda. Não era bug: a fila listava apenas presentes **já vinculados**,
e nenhum tinha sido cadastrado. Mas o diagnóstico do usuário estava certo — *"talvez a lógica
esteja errada: se um evento SHOW existe, ele gera uma tarefa de vincular algum presente a ele"*.
Uma fila que só mostra trabalho depois que alguém lembrou de cadastrá-lo não é uma fila de
trabalho; o Artista 3D não tinha como saber o que estava faltando.

**O que mudou.**

- **Banco.** Nova `event_3d_dismissals` (`event_id` **UNIQUE**, `ON DELETE CASCADE`,
  `dismissed_at`, `dismissed_by`) — a dispensa "este show não leva presente". Mesmo padrão de
  `FigurinoMissingDismissal` (183) e `EventRole.dismissed_at` (108): quando a tarefa nasce de uma
  **ausência**, é preciso um jeito de dizer "esta ausência é intencional".
- **Backend.**
  - `list_pending_events()`: SHOWs com `start_at >= hoje`, **zero** `Event3DGift` e sem dispensa.
    O recorte por data é deliberado — incluir o histórico traria centenas de linhas mortas.
  - `dismiss_event()` / `undismiss_event()`, ambos idempotentes.
  - `add_event_gift()` passou a **apagar a dispensa** do evento: se o show leva presente, a
    decisão anterior deixou de valer.
  - `GET /api/3d/fila` virou dois blocos (`items` + `sem_presente`) e aceita `?dispensados=1`;
    novos `POST|DELETE /api/events/<id>/3d-dismissal`.
- **Frontend.**
  - O formulário de vínculo saiu de dentro de `Presente3DSection` e virou
    `components/AddPresente3DForm.tsx` — **fonte única** (Princípio I), usada pela seção do evento
    e pelo novo Dialog "Vincular presente" da Fila, que pré-preenche o prazo com a data do show.
  - `Fila3DPage` ganhou o bloco "Shows sem presente vinculado" com contador, personagens
    contratados, selo de urgência, "Vincular presente", "Não leva presente" e o toggle "Mostrar
    dispensados" → "Reativar".

**Impacto em RBAC e regras de negócio.** RBAC inalterado (dispensa exige `ARTISTA_3D`/
`SUPERADMIN`). Regra nova: **todo SHOW futuro sem presente é uma tarefa aberta**, e sai da lista
de três formas — vinculando um presente, dispensando, ou o show virando passado.

**Riscos e pegadinhas descobertos.**
1. **O "vazio" que motivou a feature não era bug.** Antes de mudar qualquer coisa, conferi na
   cópia de produção: 0 peças, 0 presentes, e **23 SHOWs futuros com `event_type` batendo 100%
   com o prefixo do título** (nenhum divergente). O filtro estava correto — o modelo mental é que
   estava.
2. **Dispensa sem "desfazer" seria um beco sem saída.** Se um show fosse dispensado por engano,
   não haveria como reverter pela tela. Daí o `DELETE` e o toggle "Mostrar dispensados".
3. **Erros de `<AcervoForm>` no console durante a verificação eram do HMR**, não do código: ao
   trocar `file_path` por `files[]` (feature 201) com o app aberto, o cache do TanStack Query
   ainda tinha o formato antigo. Confirmado abrindo o app em aba nova — console limpo. Ao validar
   no browser depois de mudar o **formato de um payload**, recarregue de verdade antes de acusar
   um bug.

**Verificação.** `scripts/db/verify_200_impressoes_3d.py` ampliado — **65/65 checks**, com um
bloco US4.1 dedicado (SHOW futuro com/sem presente, não-SHOW, SHOW passado, dispensa idempotente,
`?dispensados=1`, reativar, vincular descartando a dispensa e remover o presente devolvendo a
pendência). Conferido no app real contra a cópia de produção: **23 pendências** listadas por data,
vínculo pelo Dialog derrubando o contador para 22, dispensa para 21 e "Reativar" de volta para 22.

---

### 201 — Acervo 3D: uma peça, vários arquivos
`201-acervo-3d-multi-arquivos` · **2026-07-29** · migration **`d9e3a5b7c124`** (*acervo 3d com
multiplos arquivos*)

**Motivação.** A feature 200 modelou a peça do Acervo com **um** arquivo 3D (`file_path`). Na
prática um mesmo presente quase nunca é um arquivo só: o modelo vem **fatiado em partes** (corpo,
argola, base), e o `.zip` estava sendo usado como gambiarra para empacotar tudo — o que obriga o
Artista 3D a baixar, descompactar e adivinhar o que é cada coisa.

**O que mudou.**

- **Banco.** Nova tabela `acervo_3d_files` (1:N com `acervo_3d_items`, `ON DELETE CASCADE`) com
  `file_path`, `original_name`, `position` e `created_at`. A coluna `acervo_3d_items.file_path`
  **saiu**. A migration **migra os dados antes de dropar**: um `INSERT ... SELECT` transforma
  cada peça já cadastrada numa linha de `acervo_3d_files` na posição 0, e só então a coluna é
  removida.
  - `original_name` existe porque o caminho salvo é um UUID — sem ele o Artista 3D veria três
    links indistinguíveis em vez de `corpo.stl` / `argola.3mf` / `base.stl`.
- **Backend.**
  - `Acervo3DFile` em `models.py`; `Acervo3DItem.files` com `cascade="all, delete-orphan"` e
    `order_by=position`.
  - `impressoes3d_ops.py`: `create_acervo_item` passou a receber `model_files: list` e exigir
    **pelo menos um**; `update_acervo_item` ganhou `model_files` (acrescenta) + `remove_file_ids`
    (remove) via `_apply_file_changes`, que **recusa deixar a peça com zero arquivos**;
    `delete_acervo_item` remove todos os arquivos do storage; novo `serialize_model_files`.
  - `impressoes3d_write.py`: `_model_files()` lê `request.files.getlist("files")` **e** o `file`
    singular da 200 (nenhum cliente antigo quebra), `_remove_file_ids()` lê `remove_file_ids[]`.
  - O payload da **Fila** passou a incluir os arquivos dentro de `item` — o Artista 3D baixa
    direto da fila, sem abrir o Acervo.
- **Frontend.**
  - `Acervo3DItem.file_path: string` virou `files: Acervo3DFile[]`; `SaveAcervoItemInput` ganhou
    `files: File[]` e `removeFileIds: number[]`.
  - `Acervo3DPage`: o `FileUpload` único do arquivo 3D virou um input `multiple` com lista dos
    arquivos já salvos (link de download + ✕/Desfazer para marcar remoção) e prévia dos que serão
    enviados. O card mostra badge com o nº de arquivos e um link por arquivo.
  - `Fila3DPage`: o dialog "Ver Detalhes para Impressão" lista os downloads de cada parte.

**Impacto em RBAC e regras de negócio.** RBAC inalterado. Regra nova: **peça do Acervo sempre tem
≥1 arquivo** — vale no cadastro e na edição.

**Rotas e endpoints.** Nenhuma rota nova. `POST /api/3d/acervo` passou a aceitar `files`
(múltiplos) em vez de `file`; `PATCH /api/3d/acervo/<id>` ganhou `files` e `remove_file_ids[]`. O
JSON da peça troca `file_path` por `files[]` — **breaking** para qualquer consumidor externo, mas
o único consumidor é o próprio frontend, atualizado no mesmo commit.

**Riscos e pegadinhas descobertos.**
1. **Ordem da migration é o ponto crítico.** O `INSERT ... SELECT` precisa rodar **antes** do
   `DROP COLUMN` — invertido, os arquivos das peças existentes sumiriam sem erro nenhum.
   Testado explicitamente: downgrade para `c8d2f4a6b013`, inserção de uma peça no schema antigo,
   upgrade → o arquivo apareceu em `acervo_3d_files` na posição 0.
2. **O downgrade perde dados por natureza** (volta a caber um arquivo só, fica o primeiro). Ele
   **não apaga peças** para satisfazer o NOT NULL: se sobrar alguma sem arquivo, a coluna fica
   nullable e o log avisa — perder uma peça inteira num rollback seria pior que a divergência.
3. **`FileUpload` guarda o nome do arquivo em estado interno.** Zerar o estado do formulário no
   `onSuccess` não limpava o campo: continuava exibindo "preview.png" como se ainda estivesse
   selecionado. Corrigido remontando o formulário por `key` — a limpeza agora é do chamador, não
   do próprio formulário. Vale para qualquer tela futura que reutilize o `FileUpload` em
   formulário de criação repetida.
4. **`.zip` continua aceito** (decisão do usuário): quem preferir mandar um pacote único segue
   podendo, e nada já cadastrado quebra.

**Verificação.** `scripts/db/verify_200_impressoes_3d.py` ampliado — **47/47 checks** (inclui
ordem/posição dos arquivos, PATCH acrescentando sem substituir, remoção individual e o 400 ao
tentar remover todos). Round-trip da migration testado com dado real. `tsc --noEmit` limpo,
build do internal OK, e conferido no app real: upload de 3 arquivos de uma vez, card com os 3
downloads nomeados, dialog de edição com ✕/Desfazer e formulário limpo após o sucesso.

---

### 200 — Módulo Core de Impressões 3D
`200-impressoes-3d` · **2026-07-29** · migration **`c8d2f4a6b013`** (*modulo core de impressoes 3d*)

**Motivação.** A entrega física dos Presentes 3D dos eventos `SHOW` era controlada fora do
sistema. O Artista 3D não tinha como saber, sem perguntar, **quantas peças imprimir e de que
idade** — informação que a cliente já preenche no formulário de pré-contrato — nem qual era o
prazo real de cada evento. O módulo nasce fechando esse ciclo: catálogo de peças com foto,
vínculo peça↔evento com prazo e status, e um painel operacional que **cruza elenco contratado +
respostas do formulário** numa tela só.

**O que mudou.**

- **Banco.** Duas tabelas novas, migração 100% aditiva:
  - `acervo_3d_items` (`Acervo3DItem`): `name`, `photo_url` e `file_path` (`.stl`/`.3mf`/`.zip`)
    — **os dois arquivos NOT NULL**: sem foto a peça não é selecionável visualmente (Princípio
    X.2) e sem arquivo ela não é imprimível, então uma entrada incompleta só sujaria o Acervo.
    Na edição, não enviar um arquivo significa manter o atual — nunca limpar. Mais `is_active`,
    `created_at`.
  - `event_3d_gifts` (`Event3DGift`): `event_id` (**ON DELETE CASCADE**), `item_id`, `status`,
    `deadline_date`, `quantity`, `notes`, `created_at`/`updated_at`; índices em `event_id`,
    `item_id` e `status`. Backref `CalendarEvent.presentes_3d` com
    `cascade="all, delete-orphan"`.
  - Nada de tabela existente foi alterado — eventos antigos seguem funcionando sem presente
    vinculado.
- **Backend.**
  - `app/constants.py`: papel `RoleName.ARTISTA_3D`, `EVENT_TYPE_SHOW` e `GIFT_3D_STATUSES`
    (`pendente` → `imprimindo` → `finalizado` → `entregue`) como fonte única do ciclo de vida.
  - `app/impressoes3d/impressoes3d_ops.py` (**novo núcleo de negócio**, funções puras): CRUD do
    Acervo com validação de extensão e troca de arquivo (upload novo apaga o antigo do storage),
    vínculo/edição/remoção de presentes, `list_print_queue()` e os serializadores
    (`serialize_acervo_item`, `serialize_gift`, `serialize_form_response`). Erros de validação
    viram `Impressao3DValidationError(field, message)` → `json_error(..., fields={campo: msg})`.
  - `app/api/impressoes3d_read.py` / `impressoes3d_write.py`: `/api/3d/acervo` (CRUD multipart),
    `/api/3d/fila` e `/api/events/<id>/3d-gifts[/<gift_id>]` (POST/PATCH/DELETE). RBAC como
    **função** (`require_3d_access()`) chamada no início de cada view, nunca decorator.
  - `app/api/agenda_read.py`: flag `can_manage_3d` em `_role_flags` e serialização de
    `presentes_3d` no detalhe do evento **só quando `event_type == 'SHOW'`** — reusando
    `serialize_gift` do módulo 3D, sem segunda montagem do payload (Princípio I).
  - `seed.py`: `get_or_create_role("ARTISTA_3D")`.
- **Frontend.**
  - `lib/impressoes3d.ts`: contrato JSON tipado + hooks TanStack Query + os helpers
    `formatDeadline`/`daysUntilDeadline`.
  - `pages/Acervo3DPage.tsx` (`/3d/acervo`): formulário de upload duplo e grade de cards com a
    contagem de usos, download do arquivo, edição em `Dialog`, inativar/reativar e exclusão
    confirmada.
  - `pages/Fila3DPage.tsx` (`/3d/fila`): tabela densa por prazo, selo de urgência, seletor rápido
    de status e o `Dialog` "Ver Detalhes para Impressão".
  - `components/EventDetail/Presente3DSection.tsx`: injetado na **coluna esquerda** de
    `/events/:id`, entre Logística e Observações; adição via `Combobox` de `@manto/ui` com
    `AvatarThumb` **quadrado** da peça (Princípio X.1/X.2).
  - `lib/navigation.tsx`: seção nova **"Impressão 3D"** (Fila + Acervo), visível para
    `ARTISTA_3D` e `SUPERADMIN`. `App.tsx`: rotas `/3d/fila` e `/3d/acervo`.

**Impacto em RBAC e regras de negócio.**
- Papel novo `ARTISTA_3D`: gestão total do módulo 3D + **leitura** dos eventos (herda o
  `api_login_required` de `GET /api/events/<id>`, que não é gated por papel) — é o que dá acesso
  ao elenco e ao formulário de pré-contrato.
- `can_manage_3d` = `ARTISTA_3D` ou `SUPERADMIN`. **Quem abre o evento lê a lista de presentes;
  só o Artista 3D edita.** Decisão consciente de não estender a escrita ao `COMERCIAL` — se a
  operação pedir, é um `has()` a mais em `_role_flags` e em `require_3d_access`.
- Presente 3D é **exclusivo de evento `SHOW`** (400 nos demais tipos).
- Peça com evento vinculado **não pode ser excluída** (400 orientando a inativar) — protege a
  contagem histórica de usos.

**Rotas e endpoints novos.** `GET|POST /api/3d/acervo` · `PATCH|DELETE /api/3d/acervo/<id>` ·
`GET /api/3d/fila` · `POST /api/events/<id>/3d-gifts` ·
`PATCH|DELETE /api/events/<id>/3d-gifts/<gift_id>` · telas `/3d/acervo` e `/3d/fila`.
**Alterado (aditivo)**: `GET /api/events/<id>` ganhou `presentes_3d` (só SHOW) e
`flags.can_manage_3d` (sempre).

**Riscos e pegadinhas descobertos.**
1. **Nome dos módulos Python.** A spec pedia `app/api/3d_read.py` e `app/3d_impressions/3d_ops.py`
   — impossível: identificador Python não pode começar com dígito, `from app.api import 3d_read`
   é erro de sintaxe. Ficaram `app/api/impressoes3d_{read,write}.py` e
   `app/impressoes3d/impressoes3d_ops.py`. **As URLs mantêm o `3d` exatamente como pedido.**
2. **`event_type` tem duas origens.** A coluna `CalendarEvent.event_type` (preenchida na
   sincronização a partir do prefixo do título) é o que o backend filtra; o JSON do detalhe expõe
   `parse_event_type(event.title)`. Hoje concordam porque a sincronização usa a mesma função —
   mas se algum dia divergirem, a seção some da tela enquanto o backend ainda aceita o vínculo.
3. **Data pura vs. `new Date()` no JS.** `new Date("2026-08-02")` é interpretado como **UTC**, o
   que em São Paulo (UTC−3) exibiria 01/08. `deadline_date` é data pura, então o módulo usa
   `formatDeadline` (split da string), e não `formatShortDate` de `@manto/ui` — este continua
   correto para os ISO **com hora** (`start_at`).
4. **Duas formas históricas de `FormResponse.data`.** Campos podem vir como
   `[chave, rótulo, valor]` (feature 123) ou `[rótulo, valor]` (anteriores).
   `serialize_form_response` normaliza as duas e **descarta campos vazios** — sem isso o extrato
   do formulário vira uma parede de rótulos em branco.
5. **`useAcervo3D` precisa de `enabled`.** O endpoint responde 403 para quem não é Artista 3D; a
   seção do evento só dispara a busca quando `can_manage_3d` é verdadeiro, senão todo `CASTING`
   que abrisse um SHOW geraria um 403 no console.

**Verificação.** `scripts/db/verify_200_impressoes_3d.py` contra `manto_local` — **40/40 checks**
(RBAC 401/403, upload duplo obrigatório com validação de extensão, vínculo recusado em não-SHOW,
status fora do ciclo de vida, presente de outro evento → 404, exclusão bloqueada de peça em uso,
elenco + formulário aninhados na fila, `entregue` sumindo da fila, `presentes_3d`/`can_manage_3d`
no detalhe do evento). `npx tsc --noEmit` limpo nos três apps e `npm run build` do internal OK.
Conferido no app real (Flask + Vite locais) com um evento SHOW de verdade: fila, dialog de
detalhes (leu "Rafael e Gabriel · 2 e 3 anos" direto do formulário), seção no evento, combobox
com miniatura e ausência da seção em evento `R&I`.

---

### 199 — Liberação do status 'No banco' para Comissões e Recorrentes
`199-no-banco-comissoes-recorrentes` · **2026-07-29** · **sem migration**

**Motivação.** A feature 189 restringiu de propósito "No banco" para itens `commission` e
`recurring` na Planilha de Pagamentos (`/financeiro/pagamentos`): em lote o backend devolvia o
item em `skipped` e a UI nem oferecia a opção no seletor. A operação do setor financeiro mudou —
hoje esses dois tipos também passam pelo mesmo fluxo bancário dos demais (cachê, salário, gasto,
BV) — então a trava intencional virou bloqueio indevido. Passou a ser exigido que os 3 status
(`nao_pago`/`no_banco`/`pago`) valham para **todos** os tipos de pagamento, sem exceção.

**O que mudou.**

- **Backend.**
  - `app/models.py`: docstrings de `CommissionPayment.status` e `RecurringExpenseEntry` (+
    `STATUSES`) passaram a documentar `no_banco` — o campo já era `db.String` livre, sem
    migration necessária.
  - **A causa raiz real não estava no endpoint de escrita, e sim na leitura**:
    `_build_commission_items`/`_build_recurring_items` (`app/financeiro/routes.py`) filtravam a
    query em `.in_(["a_pagar", "pago"])` — um item marcado `no_banco` **desaparecia da
    planilha** em vez de só não oferecer a opção. Ambos os filtros agora incluem `no_banco`, e o
    status do item agregado de comissão passou de binário (`pago`/`nao_pago`) para as 3 faixas
    (`pago` se todas as linhas do vendedor/período estão pagas, `no_banco` se todas estão no
    banco, `nao_pago` no resto/misto).
  - `set_payment_status`/`api_set_payment_status` (`app/financeiro/routes.py` e
    `app/api/financeiro_write.py`, mantidos em paridade manual — este módulo não usa `*_ops.py`
    compartilhado): o ramo `commission` calculava `target = "pago" if status == "pago" else
    "a_pagar"`, colapsando qualquer pedido de `no_banco` em `"a_pagar"` sem persistir nada; agora
    `target` aceita `pago`/`no_banco`/cai em `a_pagar` só para `nao_pago`. O ramo `recurring`
    tinha o mesmo colapso binário — ganhou o `elif status == "no_banco"`. Os filtros de status
    "aceito para reconsulta" (`CommissionPayment.status.in_(...)` /
    `entry.status not in (...)`) também passaram a incluir `no_banco`, senão um item já marcado
    não seria reencontrado para sair desse estado.
  - `_bulk_set_commission_period`/`bulk_payment_action`/`api_bulk_payment_action`: removida a
    trava explícita que devolvia `commission_ids` em `skipped` com a mensagem "não têm estado
    'no banco'" quando `action == "no_banco"`; o helper de bulk ganhou a mesma correção de
    mapeamento/filtro do endpoint individual.
- **Banco.** Nada — status seguem como string livre nas duas tabelas.
- **Frontend.** `frontend/apps/internal/src/pages/PagamentosPage.tsx`:
  `STATUS_OPTIONS_BY_TYPE` para `commission` e `recurring` passou de `["nao_pago", "pago"]` para
  `["nao_pago", "no_banco", "pago"]`, igual aos demais tipos; comentário que documentava a
  restrição intencional foi atualizado. `SELECTABLE_TYPES` **não** ganhou `recurring` — contas
  recorrentes nunca foram selecionáveis para ação em lote (limitação preexistente e
  independente do bug de `no_banco`; o backend de bulk-action não recebe `recurring_ids`), e
  estender isso é fora do escopo desta mudança.
- **Impacto em RBAC**: nenhum — mesmo gate `FINANCEIRO`/`SUPERADMIN` de sempre.
- **Verificação.** `scripts/db/verify_199_no_banco_comissao_recorrente.py` contra `manto_local`
  (test client, fora de `app_context`): set-status individual `commission`/`recurring`
  percorrendo os 3 status e voltando; `GET /api/financeiro/pagamentos` confirmando que um item
  em `no_banco` continua listado (e soma em `totals.no_banco`) em vez de sumir; bulk-action com
  `action=no_banco` para `commission_ids` deixando de cair em `skipped`. 16/16 checks.
- **Pegadinha para quem mexer aqui de novo**: este módulo **duplica** a lógica de
  `set_payment_status`/`bulk_payment_action` entre a view Jinja legada
  (`app/financeiro/routes.py`) e a API (`app/api/financeiro_write.py`) — não há um `*_ops.py`
  compartilhado como nos blueprints mais novos. Qualquer correção de regra de negócio aqui
  precisa ser replicada nos dois lugares manualmente (como foi feito nesta feature), ou vai
  divergir de novo.

### 197 — Refatoração do Dashboard de Avaliações de Clientes
`197-dashboard-avaliacoes-clientes` · **2026-07-28** · **sem migration**

**Motivação.** `/clientes/avaliacoes` estava quebrada e pobre: **a lista de avaliações nunca era
renderizada** (a página montava KPIs, distribuição e o bloco "Atenção", mas simplesmente não
usava `data.feedbacks`), o **comentário escrito pela cliente não era serializado pelo endpoint**
— ou seja, o texto que dá sentido à nota nunca chegava à tela — e o **filtro por tag não casava
nenhuma linha**. Como é a tela onde medimos a qualidade do serviço, virou um dashboard de
satisfação de verdade.

**O que mudou.**

- **Backend.** `app/clientes/client_ops.py`:
  - `summarize_feedback` ganhou `joinedload(ClientFeedback.event).joinedload(CalendarEvent.client)`
    — a serialização lê `f.event.title` e `f.event.client.name` por linha e o `lazy=True` fazia
    2 SELECTs por avaliação (N+1);
  - novo campo `pct_five` em `FeedbackSummary` (índice de excelência do recorte filtrado);
  - **correção do filtro por tag**: novo `_tag_match_conditions` + `_like_literal`. As duas rotas
    de escrita gravam com `json.dumps(...)` sem `ensure_ascii=False`, então o banco guarda a tag
    **escapada** (`["⏰ Pontualidade"]`); o filtro antigo procurava o emoji literal e ainda
    caía na barra invertida, que o PostgreSQL consome como escape do `LIKE`. Agora procura as duas
    formas com `ESCAPE '!'`. **A view Jinja legada de `app/clientes/routes.py` herda a correção.**
- **Banco.** Nada. Zero migration — `ClientFeedback.comment` e `client_name` já existiam
  (features 130/132); só não estavam sendo serializados.
- **Frontend.**
  - `@manto/ui` ganhou dois membros compartilhados (Princípio I): **`StarRating`**
    (`components/star-rating.tsx`) — estrelas somente-leitura, aceita nota fracionária,
    substitui os `StarsInt`/`StarsAvg` que viviam em cópia local dentro de
    `AvaliacaoCastingPage.tsx` — e **`formatShortDate`/`formatRelativeDay`** (`lib/date.ts`),
    promovidos de `apps/portal/src/lib/format.ts`, que agora só reexporta.
  - `lib/clientes.ts`: tipos novos `ClientFeedbackEvent`, `ClientFeedbackClient`,
    `ClientFeedbackKpis`; `ClientFeedbackItem` passou a ter `comment` e os relacionamentos
    aninhados no lugar dos antigos `event_title`/`client_name` planos.
  - `pages/ClientFeedbackPage.tsx` reescrita: 3 cards de KPI (nota média com estrelas, total,
    índice de excelência), distribuição por nota (mantida), barra de filtros funcional e grade de
    cards ricos (estrelas, cliente em destaque, evento com link para `/events/:id` + data,
    comentário em `blockquote`, tags) e empty state com ícone.
- **Verificação.** Script de test client contra `manto_local` (semeia, exercita e limpa):
  payload/aninhamento, fallback de nome, KPIs, cada filtro, formato do bloco "Atenção" e RBAC
  (COMERCIAL 200 · sem papel de vendas 403 · anônimo negado). Filtros, ordenação, empty state e
  layout mobile conferidos no navegador.

**Rotas e endpoints.**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/clientes/avaliacoes` | **contrato alterado (breaking)** — cada item de `feedbacks[]`/`attention[]` passou de `{id, score, tags, submitted_at, event_title, client_name}` para `{id, score, comment, tags, submitted_at, event: {id, title, event_date} \| null, client: {id, full_name} \| null}`; bloco novo `kpis: {media_geral, total_avaliacoes, percentual_5_estrelas}`. As demais chaves de topo (`total`, `avg_overall`, `clients_rated`, `dist`, `dist_max`, `clients_with_feedback`, `all_tags`, `filters`) seguem iguais. |

**Impacto em RBAC e regras de negócio.**

- RBAC **inalterado**: segue `_require_vendas()` (`COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`).
- `client.full_name` cai para `ClientFeedback.client_name` (o nome digitado no formulário público,
  feature 132) quando o evento não tem cliente cadastrada vinculada — nesse caso `client.id` vem
  `null`. Sem isso a maioria dos cards apareceria sem nome, porque `CalendarEvent.client_id` é
  opcional e fica vazio na maior parte da base.
- Nota e ordenação **não** vão ao servidor: a faixa "3 ou menos" não cabe no parâmetro `score`
  (que só aceita nota exata), então busca textual, faixa de nota e ordenação são aplicadas no
  cliente sobre a lista já carregada. Período e tag continuam sendo filtros de servidor.
- O seletor de cliente saiu da tela — a busca textual cobre nome da cliente **e** título do
  evento. O parâmetro `client_id` do endpoint continua existindo e funcionando.

**Riscos e pegadinhas.**

- **`LIKE` sobre JSON com emoji**: a barra invertida do `\uXXXX` é o caractere de escape padrão do
  `LIKE` no PostgreSQL. Sem `ESCAPE '!'` explícito o padrão nunca casa. Vale para qualquer filtro
  futuro sobre `ClientFeedback.tags`.
- **`grid` sem `grid-cols-1`**: `grid gap-3 md:grid-cols-2` não define coluna no mobile, e a
  trilha implícita `auto` é dimensionada por `max-content` — o comentário longo esticava o card
  para ~880px dentro de um viewport de 375px, estourando a rolagem horizontal. Corrigido com
  `grid-cols-1` explícito (`minmax(0,1fr)`) nas duas grades.
- **`truncate` dentro de flex** precisa de `min-w-0` no item; sem isso o item não encolhe abaixo
  do texto e o corte não acontece (título do evento no card).
- **Sem animação de saída por card.** A transição é do bloco inteiro, com `key` no recorte atual.
  Animar a saída item a item mantém o card removido no DOM até a animação terminar — a lista
  exibida discorda do contador enquanto isso.
- `manto_local` tem **zero** `client_feedbacks` e nenhum `CalendarEvent.client_id` preenchido: para
  conferir a tela é preciso semear dados (e limpar depois).

### 196 — Pivot do Pipeline de Vendas para Dashboard Comercial
`196-dashboard-comercial` · **2026-07-28** · **sem migration**

**Motivação.** A tela `/vendas` ("Pipeline de Vendas", feature 156) tinha virado uma cópia
empobrecida da tabela do Painel Financeiro: mesma lista de eventos com venda/custo/lucro/comissão,
sem período, sem KPI e sem nada que o Painel Financeiro já não mostrasse melhor. Para o gestor era
redundante; para o vendedor era quase inútil — e é justamente o `COMERCIAL` quem **não tem acesso
ao Painel Financeiro**, ou seja, `/vendas` é a única superfície onde ele acompanha o próprio
resultado. A tela virou um **Dashboard Comercial**: metas, performance e acompanhamento das vendas
fechadas do período.

**O que mudou.**

- **Backend.** Novo `app/financeiro/vendas_ops.py` — núcleo puro do dashboard: `list_closed_sales`
  (recorte do funil), `build_kpis`, `serialize_sales`, `closing_date`, `contratante_name`,
  `contract_status_map`, `received_map` e `event_payment_status`. `api_vendas_pipeline` em
  `app/api/financeiro_read.py` foi reescrita sobre esse núcleo e ganhou `_resolve_vendas_scope()`
  (RBAC de servidor) e `_comercial_sellers()`. **Refatoração de reuso**: `api_financeiro_dashboard`
  passou a chamar `vendas_ops.event_payment_status` no lugar da cadeia `if/elif` inline — o status
  de cobrança agora tem fonte única e as duas telas mostram o mesmo rótulo.
- **Banco.** Nada. Zero migration, zero coluna nova — `sale_value_gross`, `sale_date`, `seller_id`,
  `EventContract.is_signed`, `EventPayment` e `EventClient` já existiam.
- **Frontend.** `lib/vendas.ts` reescrito (`useDashboardComercial`, tipos `VendaFechada`,
  `VendasKpis`, `ContractStatus`, `SalePaymentStatus`); `pages/VendasPipelinePage.tsx` reconstruído
  como layout gerencial em grid: filtros de período, filtro de vendedor (só gestor), 4 cards de KPI
  e tabela densa com `Table`/`TableRow`/`TableCell` + `Badge` de `@manto/ui`. Nome do arquivo e do
  componente mantidos (`VendasPipelinePage`) para não mexer na rota em `App.tsx`.
- **Verificação.** `scripts/db/verify_196_dashboard_comercial.py` — 55 checks contra `manto_local`.

**Rotas e endpoints.**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/vendas/pipeline?period=&seller_id=` | **reescrito (breaking)** — `{items[], is_financeiro}` deu lugar a `{period, start, end, kpis, eventos[], can_filter_seller, scope_label, sellers?}` |
| GET | `/api/financeiro/dashboard` | **inalterado no contrato** — só passou a derivar `eventos[].status` de `vendas_ops` |

**Impacto em RBAC e regras de negócio.**

- O gate de acesso continua `_can_view_vendas()`. O que mudou é o **escopo de dados**, decidido no
  servidor por `_resolve_vendas_scope()`: `FINANCEIRO`/`SUPERADMIN` veem a empresa toda e podem
  filtrar por `seller_id`; `COMERCIAL` sem papel de gestão recebe **só as próprias vendas** e o
  `seller_id` da querystring é ignorado; responsável EducaManto sem papel comercial segue restrito
  aos eventos `(EDU…`. Mesmo padrão da feature 187.
- **Custo e lucro saíram do payload**, não só da tela — informação do setor financeiro.
- `comissao_prevista` usa `_commission_beneficiary`, não `seller_id`: em evento EducaManto a
  comissão é do responsável, então ela cai no dashboard **dele**, não no do vendedor do evento.

**Riscos e pegadinhas descobertos.**

1. **`sale_value_gross` não é a receita.** O prompt original pedia somar `sale_value_gross` no
   "total vendido". Nesta base ele é o **preço de tabela antes do desconto** e fica `NULL` na
   maioria dos eventos — somar isso daria um total menor que o real e divergente da Receita Bruta
   do Painel Financeiro, que usa `sale_value`. O KPI usa `sale_value`; `sale_value_gross` virou o
   preço riscado na linha e o KPI derivado `desconto_concedido`.
2. **O eixo do período é a data de fechamento, não a data do evento.** Nesta operação a venda é
   fechada meses antes do evento (evento de julho vendido em janeiro). O Painel Financeiro recorta
   por `start_at` — correto para DRE; para o comercial o que importa é "o que eu fechei neste mês",
   que é `sale_date`. **As duas telas não batem por período de propósito**, e não é bug.
3. **`sale_date` `NULL` existe e vale dinheiro.** Em `manto_local`, 7 vendas com valor estão sem
   `sale_date` — filtrar só por `sale_date` sumiria com R$ 13.000 reais só em junho/2026. Daí o
   fallback para `start_at` em `closing_date()`.
4. **Mas o fallback sozinho polui o funil.** Na primeira versão ele arrastava para a tela todo
   evento de agenda **sem venda nenhuma** (15 linhas de `R$ 0,00` num mês). O recorte final exige
   `sale_value > 0` **ou** `is_cortesia_permuta` — evento sem valor não é venda, e quem cobra esse
   preenchimento é a auditoria do Painel Financeiro.
5. **Satélite de grupo comercial fica fora por SQL**, não em Python: o principal carrega o valor do
   grupo (FR-010/FR-011); incluir o satélite contaria a mesma venda duas vezes.
6. **`_resolve_period()` lê `request.args`** — por isso o período é resolvido na rota e passado
   pronto para `vendas_ops`, que precisa continuar puro (regra de arquitetura do projeto).

### 195 — Autocomplete de Endereços com Google Places e Comboboxes com Busca Visual
`195-autocomplete-enderecos-comboboxes` · **2026-07-28** · **sem migration**

**Motivação.** Duas regressões de usabilidade em relação ao sistema clássico, ambas com custo
operacional real. (1) O formulário de evento em React usava `<select>` nativos para figurino,
pré-escala de talento e coordenador — listas de centenas de itens onde o comercial rolava e
escolhia o nome errado, sem nenhuma foto para conferir. (2) Todo endereço do sistema era texto
livre: o operador digitava "Av Paulista 1000" e a Distance Matrix devolvia `NOT_FOUND`, quebrando
o cálculo de transporte no orçamento e no EducaManto. Endereço normalizado pelo Google é o que faz
o KM sair certo.

**O que mudou.**

- **Backend.** `app/maps.py` ganhou `address_autocomplete()` ao lado do `distance_km_ida()` já
  existente (feature 076) — fonte única da integração com o Maps — e o helper privado `_api_key()`,
  agora compartilhado pelas duas funções. Novo módulo `app/api/maps_read.py` com
  `GET /api/maps/address-autocomplete`, registrado em `app/api/__init__.py`.
  `_build_event_create_options()` em `app/calendar/routes.py` passou a incluir `photo_face_path`
  em cada item de `assignable_talents` (mudança aditiva — o Jinja legado ignora a chave).
- **Banco.** Nada. Zero migration, zero coluna nova — a `SiteSetting.google_maps_api_key` e o
  `Talent.photo_face_path` já existiam.
- **Frontend.** Dois componentes novos no design system (`@manto/ui`): `AvatarThumb` e `Combobox`.
  No app internal: `lib/maps.ts` (hook `useAddressAutocomplete`, debounced) e
  `components/GoogleAddressInput.tsx`. Telas tocadas: `EventFormBlocks/ElencoBlock.tsx`,
  `EventFormBlocks/DadosEventoBlock.tsx`, `pages/OrcamentoCalculadoraPage.tsx`,
  `pages/EducaMantoCalculadoraPage.tsx`. Tipos `FigurinoSheetOption`/`AssignableTalent` extraídos
  em `lib/eventCreate.ts`.
- **Constituição.** Novo **Princípio X** (v2.1.0) — dados complexos, comboboxes e autocomplete.

**Rotas e endpoints.**

| Método | Rota | Observação |
|---|---|---|
| GET | `/api/maps/address-autocomplete?q=&session_token=` | **novo** — proxy do Google Places |
| GET | `/api/events/new/options` | **alterado (aditivo)** — `assignable_talents[].photo_face_path` |

**Detalhe do que ficou de pé.**

1. **Proxy do Places, chave no servidor.** O React nunca vê a `google_maps_api_key`: fala só com
   `/api/maps/address-autocomplete`, que lê a chave de `SiteSetting` (com fallback para a env
   `GOOGLE_MAPS_API_KEY`) e devolve `{"items": [{description, place_id}]}`, no máximo 5, restrito
   ao Brasil e em pt-BR. Chave ausente → **503** com "Configure a API Key em Admin →
   Configurações"; falha do Google → **502** amigável, com o erro real em `logger.warning`.
2. **Economia de quota em dois níveis.** Termo com menos de 3 caracteres devolve lista vazia com
   200 **sem chamar o Google** (constante `AUTOCOMPLETE_MIN_CHARS`, espelhada no frontend como
   `ADDRESS_MIN_CHARS`); o `useAddressAutocomplete` ainda aplica debounce de 350ms e cache de 5min
   do TanStack Query. O `GoogleAddressInput` inicia com a busca vazia mesmo quando o campo já tem
   endereço salvo — abrir a edição de um evento **não** consulta o Google.
3. **`Combobox` é o novo padrão para lista grande.** Filtro local que ignora acentos ("José" casa
   com "jose"), navegação por setas/Enter/Esc, `aria-activedescendant`, botão de limpar, spinner de
   loading e dropdown com Framer Motion respeitando `useReducedMotion()`. Tem modo `freeSolo`, em
   que o valor é o texto digitado e as opções são só sugestões — é o que permite reusar o mesmo
   componente para endereço (nem todo local existe no Google).
4. **Miniaturas com forma semântica.** `AvatarThumb` é **circular** para pessoas (talento,
   coordenador — `photo_face_path`) e **quadrada** para figurino/personagem (`photo_url`). Sem foto
   salva, renderiza as iniciais do nome ou o ícone passado (🎭 para figurinos, 📍 nas sugestões de
   endereço). `@manto/ui` continua **sem** depender de `@manto/api-client`: quem chama resolve a
   URL com `assetUrl()` antes de passar.
5. **O botão de distância do orçamento passou a existir.** `useDistancia()` estava definido em
   `lib/orcamento.ts` desde a migração e **nunca era chamado** — o KM em `/orcamento` era 100%
   digitado à mão, enquanto o EducaManto já calculava. Agora há um "Calcular km (Maps)" ao lado de
   *Km (ida)*, e escolher uma sugestão do Google com "Fora de SP" ligado já dispara o cálculo.

**Impacto em RBAC e regras de negócio.** Nenhum. O endpoint novo é `api_login_required` puro (não
expõe dado do sistema, só o retorno público do Google) e as telas que o consomem mantêm o RBAC que
já tinham. Nenhuma regra de cálculo de orçamento, transporte ou elenco foi alterada — o que mudou
é *como o dado entra*.

**Riscos e pegadinhas.**

- **`onSelectSuggestion` recebe o texto explicitamente.** Ao escolher uma sugestão, o `onChange` do
  React ainda não refletiu o novo valor no mesmo tick; por isso `handleCalcularDistancia(override)`
  aceita o endereço por parâmetro. Sem isso, a primeira consulta iria com o endereço anterior.
- **`onClick={handleCalcularDistancia}` é armadilha.** Como a função passou a ter um parâmetro
  opcional `string`, ligar o handler direto no `onClick` passaria o `MouseEvent` como endereço.
  Sempre `onClick={() => handleCalcularDistancia()}`.
- **O `activeIndex` do `Combobox` não depende da identidade de `options`.** Um chamador que recria
  o array a cada render zeraria o item destacado a cada tecla; o reset ficou dividido em "volta ao
  topo quando a busca muda" + "reancora quando a lista encolhe".
- **A cópia local `manto_local` tem `manto_address = 'Rua V168 Teste, 123'`** (lixo deixado pelo
  `verify_168`), o que faz **qualquer** cálculo de distância local retornar 400 "Endereço não
  encontrado pelo Google Maps" — inclusive com endereço normalizado. Não é bug do código: com uma
  origem válida a Distance Matrix responde `OK`. Em produção o endereço-base é o real.
- **Verificação**: `scripts/db/verify_195_maps_autocomplete.py` (20/20) — monkeypatcha
  `googlemaps.Client` para cobrir sucesso e falha sem gastar quota nem depender de rede.

### 194 — Planilha de Pagamentos: cards-filtro, colorização por faixa e soma da seleção
`194-pagamentos-ux-cores-filtro` · **2026-07-28** · **sem migration**

**Motivação.** A planilha de `/financeiro/pagamentos` já tinha todos os dados certos, mas o
financeiro precisava ler linha a linha para saber o que estava pago, no banco, vencido ou por
vencer — os 5 cards de KPI no topo eram números mortos, sem interação, e as linhas só tinham cor
para "pago"/"no banco" (pendente e futuro ficavam ambos brancos). Faltava também o número que o
operador confere antes de disparar um lote no internet banking: **quanto soma o que está
marcado**.

**O que mudou.**

- **Backend / Banco.** Nada. Zero endpoint, zero migration, zero mudança de contrato JSON — toda
  a evolução é de apresentação e roda sobre o payload que `GET /api/financeiro/pagamentos` já
  devolvia desde a feature 159.
- **Frontend.** `frontend/apps/internal/src/pages/PagamentosPage.tsx` reescrita (typecheck e
  `npm run build` limpos) e um acréscimo ao design system em
  `frontend/packages/ui/tailwind-preset.ts`.

**Detalhe do frontend.**

1. **Cards de KPI viraram filtro da tabela.** Os 5 cards do topo agora são `<button>`
   (`Card asChild`, com `aria-pressed`) que filtram as linhas no cliente: **Pagos** →
   `status === "pago"`; **No banco** → `"no_banco"`; **Pendentes** → `"nao_pago"` já vencido;
   **Futuro** → `"nao_pago"` a vencer; **Total no período** (ou reclicar o card ativo) limpa o
   filtro. Cada card mostra também a contagem de itens da faixa e o rótulo "· filtro ativo".
   O card ativo ganha borda de 2px na cor do status + `ring` + fundo colorido e sombra; os
   demais ficam com `opacity-60 grayscale-[35%]` (volta ao normal no hover), então nunca há
   dúvida sobre qual filtro está ligado. Um `aria-live` anuncia "Filtro X ativo: N de M itens",
   e o cabeçalho da tabela vira "Itens do mês (N de M)" com um botão "Limpar filtro".
2. **A classificação das 4 faixas é a MESMA do backend.** `bucketOf()` deriva "pendente" e
   "futuro" do campo `is_future` que a API já manda (`_pagamentos` em
   `app/api/financeiro_read.py` soma `totals.pendente` como `nao_pago && !is_future` e
   `totals.futuro` como `nao_pago && is_future`) — **não** recomparando datas no cliente. Assim
   o filtro do card sempre bate com o valor exibido nele; se a regra de vencimento mudar no
   backend, a tela acompanha sozinha.
3. **Colorização da tabela por faixa.** Cada linha recebe uma nuance de fundo pela sua situação:
   `bg-green-50` (pago), `bg-blue-50` (no banco), `bg-rose-50` (pendente), `bg-gold-50` (futuro).
   O seletor de situação e o badge "⏳ Futuro" saem da mesma paleta (`BUCKET_TONE`), então a cor
   que o operador clica no card é exatamente a cor das linhas que aparecem. Descrição, favorecido
   e valor subiram para `font-bold text-ink` (#1a1a1a) — contraste ≥ 15:1 sobre os quatro fundos.
4. **Barra de ações em lote no topo da tabela, com a soma da seleção.** Nova
   `PagamentoBulkBar` (mesmo padrão de movimento do `CatalogBulkActionBar` da feature 186:
   `AnimatePresence` + `useReducedMotion`), renderizada dentro do `CardContent` acima da tabela.
   Texto à esquerda: **`"X selecionados • R$ Y.YYY,YY"`**, com a soma calculada por `reduce`
   sobre os itens marcados no estado do React e formatada por `formatBRL` de `@manto/money`
   (Princípio VII — fonte única).
5. **Spinner individual por ação em lote (Princípio V).** Antes, `bulkAction.isPending` fazia os
   4 botões girarem juntos. Agora a ação em voo é lida de `bulkAction.variables?.action`
   (TanStack Query v5) — só o botão clicado mostra spinner; os outros ficam `disabled` enquanto
   o lote roda, o que também impede disparar dois lotes concorrentes.
6. **Seleção.** "Selecionar tudo" passou a operar sobre as linhas **visíveis**: com um filtro
   ligado, marcar tudo marca só aquela faixa e não mexe no que já estava selecionado fora dela.
   A linha marcada ganha uma barra lateral roxa (`border-l-4 border-l-accent` no primeiro `td`,
   com `border-l-transparent` quando não marcada, para a linha não "pular" 4px). Trocar o mês
   limpa seleção e filtro.

**Design system.** `gold` ganhou os degraus **50 / 100 / 500 / 600** em
`frontend/packages/ui/tailwind-preset.ts` (`DEFAULT` e `soft` intactos — mudança puramente
aditiva). Motivo: `green`/`blue`/`red`/`rose` herdam a escala numérica padrão do Tailwind, mas
`gold` só tinha `DEFAULT`/`soft`, então `bg-gold-50` e `border-gold-500` não existiam. `gold`
continua sendo a cor de atenção/futuro do sistema — **não usar `amber`**, que não combina com o
dourado da marca.

**Impacto em RBAC e regras de negócio.** Nenhum. Acesso segue `FINANCEIRO`/`SUPERADMIN` pelo
endpoint; o filtro é 100% visual e não altera o que a ação em lote envia (ela continua mandando
os IDs selecionados, estejam visíveis ou não).

**Riscos e pegadinhas descobertas.**

- **`Card asChild` não desempata classe Tailwind.** O `Slot` do Radix apenas **concatena** o
  `className` do filho ao do pai — não passa por `twMerge`. Com as classes do card no `<button>`
  filho, `border` (do `Card`) e `border-2` (do card ativo) sobrevivem os dois e quem vence é a
  ordem no CSS gerado, não a ordem no atributo. Correção: passar **todas** as classes no
  `className` do próprio `<Card>` (que roda `cn`/`twMerge`) e deixar o `<button>` filho sem
  `className`.
- **`shadow-[inset_3px_0_0_theme(colors.accent.DEFAULT)]` é silenciosamente descartado.** O
  Tailwind 3.4 não gerou nenhuma regra para esse valor arbitrário com `theme()` dentro — e não
  emite erro: nem `tsc` nem `vite build` reclamam, a classe simplesmente não existe no CSS
  final. Só se pega conferindo o `dist/assets/*.css`. Trocado por `border-l-4 border-l-accent`.
  **Ao usar valor arbitrário do Tailwind, confirme no CSS buildado que a regra saiu.**
- **`vite build` falha com `EPERM ... dist/assets` se algum shell estiver com o `cwd` dentro de
  `dist/assets`** (o Windows trava a pasta e o `emptyDir` do Vite não consegue apagá-la). Sair da
  pasta antes de rebuildar.

### 193 — Importação Histórica do WhatsForm (One-time Migration)
`193-import-whatsform-history` · **2026-07-28** · **sem migration**

**Motivação.** O formulário de pré-contrato do Manto (features 118/119/123) substituiu o
WhatsForm em produção, mas os **1.445 preenchimentos de 2023-09 a 2026-07** continuavam presos
nos CSVs exportados da ferramenta antiga. A vendedora não tinha como buscar no Manto uma cliente
que já havia preenchido o formulário lá atrás, e a base de leads (até então só Kommo) ignorava
todo esse histórico de intenção de compra — o dado comercial mais quente que a empresa tinha.

**O que mudou.**

- **Backend.** Nenhum endpoint, rota ou tela nova — é uma **carga única por CLI**, por decisão
  explícita: um botão no sistema para algo que roda uma vez seria superfície morta. Todo o
  trabalho está em `scripts/db/import_whatsform_history.py` (novo, ~600 linhas, `ruff
  check`/`ruff format` limpos), que lê `instance/import_whatsform/*.csv` e grava via
  `db.session`. Reusa, sem duplicar (Princípio I): `normalize_phone` de
  `app/clientes/importer.py` e as chaves-sistema `SYSTEM_KEY_CPF`/`SYSTEM_KEY_CNPJ`/
  `SYSTEM_KEY_ADDRESS_*` de `app/formularios/formularios_ops.py`.
- **Banco (sem DDL).** Em **produção**: `form_responses` 28 → **1.473** linhas (+1.445);
  `clients` 5.533 → **6.198** (+665 criados, 767 reutilizados, 415 completados em colunas que
  estavam nulas). Antes disso a mesma carga rodou em `manto_local` (+693 criados, 739
  reutilizados) — a produção tinha mais clientes cadastrados que a cópia local, então 28 linhas
  a mais casaram em vez de duplicar. Valor novo em `clients.source`: **`whatsform_import`** (ao
  lado de `kommo_import` e `manual`) — coluna é texto livre, não há enum/constraint para alterar.
- **Frontend.** Zero mudança de código. As respostas importadas aparecem nas telas que já
  existiam (`/formularios`, buscador de resposta em `/events/new`, ficha do cliente) porque o
  script grava `form_type` em `comum`/`corporativo` e monta `FormResponse.data` no formato da
  feature 123 — `[{"secao", "campos": [[chave, rótulo, valor], …]}]`, com campos de 3 posições,
  que é o que `FormulariosAdminPage.tsx` destrutura.

**Regras de negócio implementadas.**

- **Deduplicação em 2 níveis**: telefone normalizado (dígitos, DDI `55` acrescentado em números
  de 10–11 dígitos) e, se não achar, CPF/CNPJ limpo. Cliente encontrado é **reaproveitado** e
  só tem preenchidas as colunas nulas (`email`, `cpf`, `cnpj`, `company`, `address`,
  `phone_display`) — `name` nunca é sobrescrito.
- **Lógica B2B premium** (3 planilhas corporativas): `name` = `"Nome do Responsável (Empresa)"`
  e telefone = **WhatsApp de quem preencheu**, não o fixo da empresa — em venda corporativa quem
  responde no WhatsApp é a pessoa. A razão social completa vai para `clients.company`.
- **CPF vs CNPJ**: o WhatsForm tinha campo único "CNPJ ou CPF"; o roteamento é por comprimento
  (14 dígitos → `clients.cnpj`, demais → `clients.cpf`), aproveitando as duas colunas que o
  model já tem.
- **`iNFORMACOES PARA PRE CONTRATO CORPORATIVO.csv`** não tem coluna de responsável: o nome sai
  da parte local do e-mail + tema, no padrão `"Contato (Tema: Halloween)"`.
- **`created_at` histórico** em respostas e nos clientes criados pela carga — a base reflete a
  linha do tempo real de captação, não a data do import.

**Impacto em RBAC.** Nenhum. Não há rota nova; quem já via `/formularios` (COMERCIAL,
FINANCEIRO, SUPERADMIN) passa a ver mais linhas.

**Rotas e endpoints novos/alterados.** Nenhum.

**Riscos e pegadinhas descobertas.**

- **`clients.phone` é `NOT NULL UNIQUE`** — linha sem telefone normalizável não pode virar
  cliente. Em vez de descartar a resposta, o script grava a `FormResponse` com `client_id`
  nulo (13 casos) para o comercial associar à mão depois. Não invente telefone-placeholder aqui:
  a unicidade do telefone é a identidade da base inteira.
- **`form_type` só aceita `comum`/`corporativo` na prática** — não é enum no banco, mas
  `frontend/apps/internal/src/lib/formulariosAdmin.ts` tipa assim e `FormulariosAdminPage`
  filtra por igualdade. Um valor como `"pre-contrato"` gravaria sem erro e **sumiria dos
  filtros** da tela. Mesma armadilha vale para qualquer carga futura.
- **Documento não confiável não deduplica.** Valores como `"2222222222"` (10 dígitos) aparecem
  nas planilhas; se entrassem na busca por CPF fundiriam clientes diferentes. Só documentos com
  11 ou 14 dígitos participam da deduplicação — os demais são gravados, mas ignorados na busca.
- **Console do Windows é cp1252**: `print` com glifos como `▶`/`═`/`✔` derruba o script com
  `UnicodeEncodeError` antes de qualquer linha ser gravada. A saída usa só ASCII (`>>`, `[OK]`,
  `[ERRO]`) — acentos pt-BR passam normalmente, os símbolos é que não.
- **`strptime` com `%a`/`%b` depende do locale da máquina.** O carimbo do WhatsForm
  (`"Wed, Jul 8, 2026 12:06 PM"`) é parseado por regex + tabela de meses própria, para a carga
  não mudar de comportamento conforme o computador que a roda.
- **Rodar duas vezes duplicaria tudo** — não há chave natural de resposta no banco para
  `upsert`. O script detecta respostas já importadas (mesmo `contact_name` + `created_at`) e
  **aborta o arquivo** com rollback, a menos que se passe `--force`. Verificado: a segunda
  execução não gravou nada.
- **Transação por arquivo**: erro em qualquer linha faz `rollback()` do CSV inteiro e loga
  arquivo + linha + contato. `--dry-run` processa tudo numa transação única e desfaz no fim —
  o resumo simulado bate número a número com o da carga real (foi assim que a carga foi
  validada antes de gravar).

**Como rodar (uma vez por ambiente).**

```powershell
# 1. Backup fresco ANTES de qualquer escrita
.\scripts\db\backup-railway.ps1

# 2. Cópia local (manto_local)
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path

# 2'. OU produção (Railway) — trocar o driver para psycopg3, ver pegadinha abaixo
$env:DATABASE_URL = (Get-Content .railway-db-url -Raw).Trim() -replace '^postgresql://', 'postgresql+psycopg://'
$env:PYTHONPATH = (Get-Location).Path

# 3. Ensaio e carga
.venv\Scripts\python.exe scripts\db\import_whatsform_history.py --dry-run   # ensaio
.venv\Scripts\python.exe scripts\db\import_whatsform_history.py             # carga
```

> **Status: concluído nos dois ambientes em 2026-07-28** — `manto_local` primeiro, produção
> (Railway) em seguida, ambas precedidas de ensaio limpo. Backup da produção imediatamente antes
> da carga: `backups/manto_2026-07-28_1119.dump`.

**Pegadinhas descobertas ao apontar para a produção** (valem para qualquer script CLI futuro):

- **`create_app()` sobe três workers de background** — `talent-sync`, `calendar-sync` e
  `review-cleanup`. Apontados para a produção, o `calendar-sync` pode reivindicar o slot de
  sincronização automática e disparar um sync real com o Google Calendar, e o `review-cleanup`
  apaga arquivos de revisão vencidos do armazenamento — efeito colateral que nada tem a ver com
  importar CSV. O script chama `build_app_without_background_workers()`, que ativa a guarda de
  dev já existente (`FLASK_ENV=development` sem `WERKZEUG_RUN_MAIN`) antes do `create_app()`.
  Isso **não** muda o banco: a `SQLALCHEMY_DATABASE_URI` vem sempre de `DATABASE_URL`, e nem
  `DevelopmentConfig` nem `ProductionConfig` a sobrescrevem.
- **Driver diferente entre a máquina de dev e a produção.** O `requirements.txt` traz
  `psycopg2-binary` (usado no deploy), mas o venv local tem só o **psycopg3** — por isso
  `.local-db-url` usa `postgresql+psycopg://`. A URL do Railway vem como `postgresql://`, que o
  SQLAlchemy resolve para psycopg2 e quebra com `ModuleNotFoundError` na máquina de dev. Reescrever
  o scheme para `postgresql+psycopg://` resolve — mesmo banco, cliente diferente.
- **Latência domina a carga remota.** A deduplicação consulta o banco linha a linha: imperceptível
  no Postgres local, ~100 ms por ida-e-volta contra o Railway → ~20 min para as 1.445 linhas
  (ensaio + carga = ~40 min). Foi aceito de propósito, para rodar exatamente o código validado em
  vez de otimizar o caminho crítico em cima de produção. Se algum dia precisar ser rápido, o
  caminho é carregar o índice de clientes em memória de uma vez, não paralelizar.

---

### 191 — Migração do Portal do Artista (React) e Auditoria de Segurança
`191-portal-artista-react-auditoria` · **2026-07-28** · **sem migration**

> Numeração fora de ordem em relação à 192 logo abaixo: a 192 foi um ajuste direto em `main`,
> feito enquanto esta fatia estava planejada. A ordem do documento continua sendo por data.

**Motivação.** A fatia **176** entregou 5 telas React do Portal do Artista (login, agenda,
convites, ficha de figurino, fotos/documentos) e deixou explicitamente de fora todo o resto —
primeiro acesso, troca de senha obrigatória, aceite de termos, "esqueci minha senha", edição de
perfil e avaliação de eventos continuaram só no Jinja (`app/talent_portal`). Na prática o
talento era jogado para a versão clássica no meio do login (`must_redirect_to_classic`), e o
histórico de cachês não existia em React. Além disso, **o bundle do portal nunca era publicado**:
`frontend/server.js` só montava `apps/internal` e `apps/public`, e o `build` agregado do
monorepo não incluía `apps/portal` — o app existia no repositório e nunca chegava a produção.

**Backend.** Nenhum endpoint antigo mudou de contrato. Três módulos de núcleo de negócio, todos
puros e reusáveis pelo Jinja legado (Princípio I):
- `app/talent_portal/portal_account_ops.py` (**novo**): `validate_password_strength`,
  `start_first_access`, `request_password_reset`, `find_talent_by_reset_token`,
  `reset_password_with_token`, `change_password`, `accept_terms`, `pending_account_steps`.
  O disparo de e-mail entra por callback injetado pela rota — o módulo não importa `request`.
- `app/talent_portal/portal_rating_ops.py` (**novo**): extraído de `routes.py` sem mudar a
  semântica em produção — janela de 7 dias para avaliar e 30 para editar (contadas do mais
  recente entre o fim do evento e `assigned_at`, feature 085), nota &lt;4 exige comentário,
  versionamento da avaliação anterior (feature 181) e as categorias de sub-nota.
- `app/talent_portal/portal_ops.py`: ganhou `get_profile`/`update_profile` (PATCH parcial com
  validação de altura e data), `add_portfolio_photo`/`add_portfolio_link`/
  `delete_portfolio_item` e `get_historico` (lista + somatórios pago/pendente).

**Endpoints novos** (12; total de `/api/portal/*` foi de 14 para 26):
`POST /api/portal/auth/first-access`, `POST /api/portal/auth/forgot-password`,
`GET /api/portal/auth/reset-password/<token>`, `POST /api/portal/auth/reset-password`,
`POST /api/portal/auth/change-password`, `POST /api/portal/auth/accept-terms`,
`GET|PATCH /api/portal/profile`, `POST /api/portal/profile/media/photo`,
`POST /api/portal/profile/media/link`, `DELETE /api/portal/profile/media/<id>`,
`GET /api/portal/historico`, `GET /api/portal/ratings/pending`,
`GET|POST /api/portal/events/<id>/rate`, `POST /api/portal/events/<id>/rate/detail`.
`GET /api/portal/auth/me` e o login agora devolvem `must_change_password`, `terms_accepted` e
`pending_steps`; `must_redirect_to_classic` virou sempre `false` (mantido por compatibilidade).

**Banco.** Sem migration — tudo já existia em `Talent` (`must_change_password`,
`password_reset_token/expires`, `terms_accepted_at`, medidas), `TalentMedia`, `EventRating`,
`EventSubRating` e `EventRatingVersion`.

**Frontend.** 8 telas novas em `frontend/apps/portal`: `PortalFirstAccessPage`,
`PortalForgotPasswordPage`, `PortalResetPasswordPage`, `PortalChangePasswordPage`,
`PortalTermsPage`, `PortalProfilePage`, `PortalHistoricoPage` e `PortalRatePage`. Componentes
compartilhados novos: `AuthCard`, `FormField`/`FormError`/`FormSuccess`, `PasswordChecklist`,
`StarRating` (radiogroup real, acessível) e `OnboardingGate`. `lib/format.ts` centraliza
data/hora amigável (Princípio VII) — `formatDateTime`, `formatWeekday`, `formatRelativeDay`,
`formatLongDate`, `formatShortDate`; valor monetário continua em `@manto/money`.
O texto do termo virou `lib/termsContent.ts`, transcrição fiel de `templates/portal/terms.html`
(o aceite gravado precisa se referir ao mesmo documento antes e depois).

**Deploy (a parte que faltava para o portal existir em produção).**
- `frontend/server.js`: passou de 2 para 3 SPAs, com uma lista de apps montados por prefixo —
  `/catalogo/*` → `apps/public/dist` e `/portal/*` → `apps/portal/dist`, raiz → `apps/internal`.
  Deep link e refresh funcionam nos três (cada um com seu próprio fallback de `index.html`).
- `frontend/apps/portal/vite.config.ts`: `base: "/portal/"` em produção (mesmo padrão da 186 no
  `apps/public`), e o React Router recebe `basename={import.meta.env.BASE_URL}`.
- `frontend/package.json`: `build` e `typecheck` agregados passam a incluir o portal, mais
  `dev:portal`/`build:portal`/`typecheck:portal`.
- `app/api/portal_auth.py::_reset_url` monta o link de redefinição a partir de `PORTAL_URL`
  (mesma base já usada pelos outros e-mails do portal), caindo na rota Jinja se a env não estiver
  configurada — o link não quebra em ambiente onde o front novo ainda não subiu.

**RBAC e regras de negócio.** Sem mudança de política. O RBAC do portal continua sendo "é o dono
do recurso": toda consulta parte do `talent_id` da sessão e nenhum endpoint aceita um id de
talento vindo do cliente (o PATCH de perfil ignora um `id` no corpo, verificado na auditoria).
A trava de onboarding é servida **no lugar** do app pelo `OnboardingGate`, não por redirect —
não existe URL de onboarding para pular, e um deep link para `/agenda` com senha pendente cai na
mesma trava. A API deliberadamente **não** bloqueia por termos pendentes: o gate é de produto,
não de segurança, e endurecer isso mudaria o comportamento do Jinja legado que ainda usa a mesma
sessão.

**Auditoria de segurança** (`scripts/security/overnight_security_audit.py`, **novo** — 76
verificações, saída com código 1 em qualquer falha, relatório em
`scripts/security/relatorio_seguranca.md`):
- **Cookies**: `HttpOnly` + `SameSite=Lax` confirmados nas sessões de Staff e de Talento, e
  `SESSION_COOKIE_SECURE=True` em `ProductionConfig` (em dev fica ausente de propósito, HTTP).
- **Isolamento de sessão**: as duas sessões são hermeticamente fechadas nos dois sentidos —
  cookie de talento dá 401 na API de staff e vice-versa, e cada login faz `session.clear()`,
  encerrando a sessão do outro tipo no mesmo cookie.
- **RBAC**: talento bloqueado em 13 endpoints internos; anônimo bloqueado; vendedor (COMERCIAL)
  bloqueado em usuários/RH/pagamentos/configurações/logs/desempenho (403); IDOR no portal
  (escalação, mídia e figurino de terceiros) devolve 404/403.
- **E-mails**: os 8 disparadores mapeados; todo caminho de `mail.send()` está sob `try/except`
  **e** atrás de `SiteSetting.email_notifications_enabled`; com a flag desligada o envio vira log
  silencioso e a request segue 200; com SMTP fora do ar a resposta continua 200 com mensagem
  amigável, sem 500; o reset de senha não permite enumeração de conta (mesmo status e mesmo corpo
  para CPF existente e inexistente).

**Riscos e pegadinhas descobertas.**
1. **`app/api/__init__.py` importa por efeito colateral em ordem de registro** — o módulo novo
   `portal_ratings` precisa entrar nessa lista, senão as rotas simplesmente não existem. O
   `ruff` acusa `I001` no arquivo (pré-existente): a ordem é deliberada, não ordene os imports.
2. **`query.delete()` em massa não passa pelo ORM** e deixa órfãs as linhas de associação —
   estourou FK em `user_roles` (auditoria) e em `event_sub_ratings` (verificação). Nos scripts,
   apagar objeto a objeto com `db.session.delete()` para a cascata do ORM valer.
3. **`send_quote_email` não usa `_send`** (precisa anexar PDF) e reimplementa o guarda. A
   auditoria verifica a *propriedade* (todo `mail.send(` sob try/except + gate) em vez de exigir
   uma função única — contar chamadas dava falso positivo.
4. **Reset de senha de staff não existe por e-mail**: um SUPERADMIN define a senha temporária à
   mão em `user_ops.reset_password`. Só o Portal do Artista tem fluxo self-service. Registrado
   como observação na auditoria, não como falha.
5. **`FileUpload` do design system tinha alvo de toque de 36px** (`size="sm"`, único controle do
   componente). Corrigido na origem com `min-h-[44px]` — o portal é mobile-only (Princípio VIII)
   e no desktop o botão só cresce 8px.
6. **O baseline de versionamento da avaliação vai e volta pelo cliente** na API (a tela Jinja
   guarda na sessão, mas o slot único já estourou o tamanho do cookie uma vez). É só um detector
   de mudança: adulterá-lo no máximo registra — ou deixa de registrar — uma versão no histórico,
   nunca altera a nota gravada.
7. **Proxy Vite de `/portal` foi estreitado para `/portal/photo`** — o prefixo largo funcionava
   quando o app React vivia só na raiz em dev, mas sombrearia as rotas próprias do portal. Mesma
   pegadinha da feature 183 com `/figurinos`.

**Legado.** As rotas Jinja de `app/talent_portal` **continuam de pé e sem regressão** (paridade
verificada: login, first-access, forgot-password, `/portal/`, `/portal/historico`,
`/portal/profile`). Decomissioná-las é limpeza futura, fora do escopo desta entrega — conforme a
regra de `CLAUDE.md`, não apagar view antiga sem confirmação.

**Verificação.** `scripts/db/verify_191_portal_react.py` — 72/72 contra `manto_local`
(fluxos de conta, perfil/portfólio, avaliações com janelas e versionamento, histórico com
somatórios, paridade Jinja). Auditoria: 76/76. `npx tsc --noEmit` e `npm run build` limpos nos
três apps. Telas conferidas em viewport de 320px e 430px: sem rolagem horizontal, nenhum alvo de
toque &lt;44px, nenhum texto informativo &lt;12px.

---

### 192 — Detalhe do Evento: layout de duas colunas com paridade total da tela clássica
`main` (ajuste direto, sem branch de feature dedicada) · **2026-07-27** · **sem migration**

**Motivação.** A `/events/:id` em React era uma coluna única de ~1370 linhas num arquivo só,
com uma fração do que a tela clássica Jinja (`app/templates/event_detail.html`, 3.201 linhas,
ainda em produção em paralelo) entrega. Faltavam na versão React: menu "⋯ Ferramentas", bloco de
cópia rápida para WhatsApp, indicador de conflito de agenda do talento, medidas de figurino,
vínculo de ficha de figurino ao personagem, status de pagamento do cachê, equipe de apoio
separada dos personagens, materiais de ensaio, gastos extras vinculados, acréscimos/BV,
avaliações dos artistas, feedback da cliente e o log de atividades. Boa parte disso já existia
como cálculo inline na view Jinja — nunca tinha sido exposta pela API.

**Backend.** Nenhum endpoint antigo mudou de contrato; o JSON de leitura **ganhou campos**.
- `app/calendar/event_ops.py` (+~290 linhas): núcleo novo — `talent_availability` (extraído do
  loop inline de `event_detail`), `set_payment_status`, `link_figurino_sheet`,
  `clear_figurino_done`, `ensure_feedback_token`, `suggested_departure_time`,
  `add_ensaio_file`/`add_ensaio_link`/`delete_ensaio_material`.
- `app/api/agenda_read.py`: `serialize_event_detail` passou a incluir `event.description`,
  `event.google_html_link`, `event.travel` (cache do Maps + saída sugerida + `maps_url`),
  `materiais`, `ratings`, `client_feedbacks`; e, sob os gates já existentes, `acrescimos`,
  `gastos`, `mensagens`, `reembolsos_pendentes_total`, `feedback_link_pendente`. Cada cargo
  do `elenco` ganhou `talent` completo (medidas, WhatsApp com DDI, primeiro nome), `role_type`,
  `assigned_at`, `payment_status`, `availability`, `figurino_sheet_name`, `figurino_done_at`,
  `travel_cache` e `cache_cap`.
- `app/api/agenda_write.py`: 7 endpoints novos — `POST /api/roles/<id>/payment-status`,
  `POST /api/roles/<id>/figurino-sheet`, `DELETE /api/roles/<id>/figurino-done`,
  `POST /api/events/<id>/travel-estimate`, `POST /api/events/<id>/materials`,
  `DELETE /api/materials/<id>`, `POST /api/events/<id>/feedback-link`.

**Banco.** Sem migration — nenhuma coluna nova. Tudo já existia em `EventRole`
(`payment_status`, `figurino_sheet_id`, `assigned_at`), `CalendarEvent` (`description`,
`google_html_link`, `travel_*`, `feedback_token`), `EnsaioMaterial`, `EventRating`,
`ClientFeedback`, `SpecialExpense` e `EventAcrescimo`.

**Frontend.** `EventDetailPage.tsx` reescrita (1.367 → ~120 linhas) como composição de
`components/EventDetail/`: `parts.tsx` (Panel/DataRow/Stars/formatadores), `EventHeader.tsx`
(cabeçalho + menu Ferramentas + modal de exportar elenco + diálogo de exclusão),
`CastingSection.tsx`, `FigurinoSection.tsx`, `LogisticaSection.tsx`, `ComercialSection.tsx`,
`FinanceiroSection.tsx`, `FeedbackSection.tsx`, `ObservacoesSection.tsx` (+ `WhatsAppSummary` e
`LogsSection`). Hooks novos em `lib/eventDetail.ts` (todos gravam o evento devolvido no cache do
TanStack Query, como `casting.ts`) e os construtores das mensagens de WhatsApp. `KebabMenu`
ganhou `triggerLabel` e itens `disabled`/`title` em vez de um segundo componente de dropdown.
A busca de fichas de figurino reusa `useFigurinoSheets()` (`GET /api/figurino`), sem endpoint
novo.

**RBAC e regras de negócio.** Sem mudança de política — os gates novos reusam os existentes:
`_CAN_EDIT_EVENT` (status de pagamento, ficha de figurino, desmarcar figurino, estimar trajeto),
`_CAN_ENSAIO_MATERIAL` (materiais de ensaio) e Comercial/Superadmin (link de feedback, mesmo
gate de `feedback.gerar_link`). **Novo requisito de segurança**: a seção "Log de atividades" só
é renderizada para `SUPERADMIN` — para os demais papéis ela **não existe no DOM**, não é
escondida por CSS.

**Riscos e pegadinhas descobertas.**
1. `CalendarEvent.roles` **não tem `order_by`** — o Postgres devolvia os cargos em ordem
   arbitrária, e a ordem *mudava depois de um UPDATE*. Com os cards densos isso fazia a lista
   inteira pular de posição a cada mutação. `serialize_event_detail` agora ordena por `id`.
2. `api_set_payment_status` colidiu com o endpoint de mesmo nome em `financeiro_write.py`
   (Flask recusa o registro do blueprint com `AssertionError`) — renomeado para
   `api_set_role_payment_status`.
3. A descrição do evento vem do Google/Kommo **em HTML** (`<br>`, âncoras de e-mail). Colada
   crua no WhatsApp vira um paragrafão com tags à mostra; `descriptionToText()` converte para
   texto puro por regex (sem `innerHTML`/`querySelector`, proibidos pela constituição).
4. `/api/events/<id>` não é alcançável por `REVENDEDOR_EDUCAMANTO` puro — o guard global de
   `app/__init__.py` só libera o prefixo `/events/`, não `/api/...`. Comportamento pré-existente,
   descoberto ao escolher papéis para o script de verificação.
5. Materiais de ensaio novos vão por `app.storage.save_file` (local/S3) em vez do `file.save()`
   direto do fluxo Jinja; o serializador normaliza os dois formatos de `file_path`.

**Verificação.** `scripts/db/verify_190_event_detail.py` — 53/53 contra `manto_local`
(serialização dos blocos novos, RBAC de leitura por papel, e 200/400/403/404/401 dos 7
endpoints). Frontend: `npm run build` limpo e conferência no app real (evento 286): 16 seções,
duas colunas em 1280px, sem rolagem horizontal, log ausente do DOM ao impersonar `CASTING`,
mutações de figurino/pagamento/materiais devolvendo 200 com a lista estável.

---

### 191 — Calculadora de Orçamento: paridade de layout clássico + cálculo reativo
`main` (ajuste direto, sem branch de feature dedicada) · **2026-07-27** · **sem migration**

**Motivação.** A versão React de `/orcamento` (feature 190) portou a calculadora para duas
colunas de largura igual com um botão manual "Calcular orçamento" — isso dispersou os campos em
relação à tela clássica Jinja (`app/templates/orcamento/index.html`, ainda em produção em
paralelo) e tornou o fluxo do comercial mais lento (clicar em "Calcular" a cada ajuste). Dois
recursos da tela clássica nunca foram portados: o alerta de segurança "já agendado neste dia"
(evita vender o mesmo personagem duas vezes no mesmo dia) e o painel "Personalizar valores"
(definir o total final manualmente, por valor ou por multiplicador) — a infraestrutura de API
para ambos já existia (`usePersonagensNoDia`, campos `personalizado*` em
`CalcularOrcamentoInput`), só nunca tinha sido usada na tela.

**Backend.** Nenhuma mudança — nenhum endpoint, RBAC ou model tocado. Todo o trabalho reusou
`GET /api/orcamento/personagens-no-dia`, `GET /api/orcamento/historico` e
`POST /api/orcamento/calcular`, já existentes desde a feature 177/190.

**Banco.** Sem migration.

**Frontend.** Reescrita completa de `OrcamentoCalculadoraPage.tsx` (mesmo arquivo,
`PerformerTableRow` reaproveitado sem mudanças):
- Layout `lg:grid-cols-3`: coluna esquerda (1/3) = Dados do Evento + transporte condicional
  (Fora de SP) + alerta de agenda + link "Histórico de Orçamentos" com contador dinâmico
  (`useOrcamentoHistorico({}).data.entries.length`); coluna direita (2/3) = Equipe, Acréscimos,
  card "Ajustes Finos" (Nota Fiscal, duração extra, formato do orçamento, durações incluídas,
  "Personalizar valores") e o card de Resultado.
- **Cálculo reativo**: removido o botão "Calcular orçamento"; um `useEffect` observa um
  `payload` memoizado com todo o estado do formulário e dispara `calcular.mutate` com debounce
  de ~400ms a cada alteração — sem exigir clique. Os cards de resultado ficam com opacidade
  reduzida (`opacity-50`) enquanto uma requisição está em voo, em vez de somem, preservando o
  último valor visível (Princípio V — feedback visual obrigatório).
- **Alerta "Já na agenda neste dia"**: novo componente `AgendaNoDiaAlert`, usa
  `usePersonagensNoDia(eventDate)` (existia no hook, nunca usado em nenhuma página); valida a
  data com regex antes de habilitar a query, para não disparar a API com data parcial/inválida;
  renderiza abaixo do campo Data.
- **Painel "Personalizar valores"** (novo na UI — só o tipo já existia): checkbox que abre um
  toggle "Definir valor final" / "Mudar multiplicador" e 4 campos (1h–4h), `MoneyInput` no modo
  valor final, `Input` numérico no modo multiplicador.
- Substituído o `<select>` de "Formato do orçamento" por um toggle de dois `Button`
  (`variant="default"`/`"outline"` conforme seleção), mesmo padrão visual dos botões +/- do
  Coordenador — sem componente novo no design system.

**Impacto em RBAC e regras de negócio.** Nenhum — mesma tela, mesmo RBAC (`COMERCIAL`,
`SUPERADMIN`), nenhuma regra de cálculo mudou no backend.

**Riscos e pegadinhas.**
- O alerta de agenda e o contador do histórico dependem de dados existentes em `manto_local` —
  verificado manualmente logado como SUPERADMIN contra um evento real do dia (BLUEY + BINGO,
  27/07/2026): o alerta apareceu corretamente com os dois personagens.
- O modo "Personalizar valores" retorna erro de campo do backend quando os 4 valores ficam em
  zero ("Informe valores válidos para o orçamento personalizado.") — comportamento esperado do
  endpoint, não um bug novo; confirmado que o erro aparece e some corretamente ao preencher um
  valor.
- Sem verificação funcional automatizada de backend nesta entrada (nenhum endpoint mudou) — só
  `npx tsc --noEmit` (limpo) e verificação manual na UI real via preview.

---

### 190 — Paridade e Unificação do Módulo de Orçamentos e EducaManto (React)
`190-paridade-orcamento-educamanto` · **2026-07-27** · **sem migration**

**Motivação.** As 6 telas do módulo de Ferramentas (Calculadora de Orçamento, Config. de Preços,
Histórico de Orçamentos, Calculadora EducaManto, Pacotes EducaManto, Histórico EducaManto) já
existiam e funcionavam, mas haviam perdido densidade visual e paridade de recursos frente à
extinta versão Jinja: listas de `Card` soltos em vez de tabelas gerenciais, filtros avançados já
suportados pelo backend mas nunca expostos na UI (`date_from`/`date_to`/`min_val`/`max_val`/
`user_id`/`has_show` no histórico de Orçamento), e — a lacuna mais importante — **nenhum dos dois
históricos tinha ação "Recalcular"**, apesar do backend já guardar o estado bruto necessário
(`OrcamentoHistory.form_snapshot`, `EducaMantoQuote.snapshot`) sem nunca expô-lo em JSON. A meta
de negócio é unificar a experiência do EducaManto com a Calculadora de Orçamento normal como
ferramentas irmãs do mesmo ecossistema, incluindo paridade de "reabrir, editar e recalcular".

**Backend.** Dois endpoints de leitura, ambos aditivos/retrocompatíveis — nenhum endpoint
existente mudou de contrato, nenhuma lógica de negócio nova (reuso de `quote_ops` já existente).
- `app/api/orcamento_read.py`: `GET /orcamento/historico/<id>` passou a incluir também
  `form_snapshot` (estado bruto de entrada, já persistido, nunca antes exposto) ao lado do
  `quote` congelado que já existia.
- `app/api/educamanto_read.py`: **novo** `GET /educamanto/historico/<id>` — retorna
  `quote_ops.load_quote_snapshot(quote)` em JSON (mesmo dado já usado internamente para regerar o
  PDF), mesmo RBAC (`_require_use`) da listagem, sem restrição por dono (paridade com o endpoint
  de PDF por id, que também não restringe por dono).

**Banco.** Sem migration — nenhuma coluna nova, nenhum model alterado.

**Frontend.**
- Fundação em `@manto/ui`: `Table`/`TableRow`/`TableCell` (convenção densa extraída de
  `PagamentosPage`/`GastosRecorrentesPage`, feature 189), `Badge` (rótulo de tom único,
  complementar ao `MetricBadge` existente) e `CopyButton` (promovido de local em
  `PagamentosPage.tsx` para fonte única).
- `OrcamentoCalculadoraPage.tsx`: layout em duas colunas, "Limpar tudo", equipe em tabela
  (Coordenador com contador +/-, "+ Ator/Cantor"/"+ Especial"), nota informativa de BV, campo de
  duração extra (`duracao_custom`, já existia no tipo mas não estava exposto na UI), painel de
  resultados em cards 1h–4h, `Dialog` "Ver memória de cálculo"; lê `?recalcular_id=` e repopula
  todos os campos a partir de `form_snapshot` (mesmo padrão de pré-fill via query param de
  `EventCreatePage.tsx`).
- `OrcamentoConfigPrecosPage.tsx`: os 8 blocos de preço viraram tabelas (`PriceTable`) — Markup,
  Cachê Atores, Cachê Cantores, Técnico/Coordenador, Especiais (uma linha por variante); "Voltar
  à calculadora" no `PageHeader`.
- `OrcamentoHistoricoPage.tsx`: tabela gerencial com todos os filtros que o hook já suportava
  (texto, data, faixa de valor, vendedor, tipo com/sem show), badge de tipo, `Dialog` "Ver"
  (substitui a expansão inline anterior), **"Criar evento"** (`/events/new?orcamento_id=` — o
  pré-fill do lado do `EventCreatePage` já existia, só faltava o link) e **"Recalcular"**
  (`/orcamento?recalcular_id=`).
- `EducaMantoCalculadoraPage.tsx`: seletor de pacote virou dropdown (era pills), layout em duas
  colunas, cards "Sem Nota Fiscal"/"Com Nota Fiscal" recoloridos (verde/azul) com Custo Base e
  Comissão do Vendedor explícitos, detalhamento de custos dentro de um `AccordionRow`
  colapsável, atalhos no cabeçalho ("Editar pacote", "+ Novo pacote"); lê `?package_id=` (vindo
  de "Usar" na tela de Pacotes) e `?recalcular_id=` (repopula a partir do novo endpoint de
  detalhe — note que o texto do endereço não é persistido no snapshot, só o km calculado, então
  o campo de endereço fica vazio no recálculo mas o km/transporte já vêm preenchidos).
- `EducaMantoPackagesPage.tsx`: lista vertical virou grade de 2–3 colunas; cada card ganhou
  margens (1S/2S/1S-dias/2S-dias), desconto formatado ("5% após N dias") e uma mini matriz de
  custos; botão novo "Usar" (`/educamanto?package_id=`, disponível a todos que veem pacotes, não
  só a quem gerencia); "Duplicar" ganhou o rótulo "Criar cópia" pedido (mesma mutation).
- `EducaMantoHistoricoPage.tsx`: lista virou tabela; "Reabrir PDF" renomeado para "Baixar PDF";
  **"Ver"** novo (`Dialog` consumindo o endpoint de detalhe novo) e **"Recalcular"** novo
  (`/educamanto?recalcular_id=`).

**Rotas e endpoints.**
- **Novo:** `GET /api/educamanto/historico/<id>`.
- **Alterado (aditivo):** `GET /api/orcamento/historico/<id>` (campo `form_snapshot` a mais).
- Rotas de página inalteradas.

**RBAC e regras de negócio.** Sem mudança de permissões. "Recalcular" sempre roda o cálculo com
as configurações de preço **atuais** (não os valores congelados no histórico) — é a mesma
calculadora reaberta com os campos preenchidos, não uma reconstrução do valor histórico exato;
para ver o valor exatamente como foi cotado, a ação é "Ver" (mostra o snapshot congelado), não
"Recalcular".

**Riscos e pegadinhas.**
- O processo do backend local (`manto-backend-local`) não recarregou a nova rota
  `/api/educamanto/historico/<id>` automaticamente apesar do reloader do Werkzeug reportar
  "Restarting with stat" — só passou a responder (401 em vez de 404) após um restart manual do
  processo. Se uma rota nova parecer "não existir" mesmo com o código correto no disco
  (confirmado lendo `app.url_map` num processo novo), suspeite do processo de dev desatualizado
  antes de suspeitar do código.
- `EducaMantoQuote.snapshot` guarda `transporte.kmT`/`label`/`pessoas`/`total`, mas **não** o
  texto do endereço digitado — "Recalcular" no EducaManto restaura o km calculado, não o campo
  de endereço em si.
- `@manto/ui` não tem um componente `Table`/`Badge` genérico antes desta feature — telas com
  tabela usavam `<table>` nativo caso a caso; os novos `Table`/`TableRow`/`TableCell`/`Badge`
  ficam disponíveis para qualquer tela futura que precise de listagem densa.
- Verificação: `npx tsc --noEmit` limpo em `frontend/apps/internal`; `ruff check` limpo nos dois
  arquivos Python tocados; fluxo completo Calculadora → Salvar → Histórico → Recalcular → Criar
  evento exercitado no navegador contra `manto_local` para os dois módulos (Orçamento e
  EducaManto), incluindo o `Dialog` "Ver" em ambos os históricos.

### 189 — Módulo Financeiro de Alta Fidelidade e Consistência (React)
`189-financeiro-alta-fidelidade` · **2026-07-27** · **sem migration**

**Motivação.** As três telas financeiras em React (`/financeiro`, `/financeiro/pagamentos`,
`/gastos/recorrentes`) haviam perdido densidade de informação e fluxos operacionais frente à
versão Jinja congelada. Especificamente: o painel financeiro virou uma pilha vertical de cards
(sem grid 2/3 + 1/3, sem termômetro de break-even, sem barra do Fator R, com a DRE achatada e
sem hierarquia); a planilha de pagamentos perdeu a **cópia rápida de PIX/valor/descrição**, a
ordem de colunas clássica e — bug operacional principal — **não tinha ação em lote para "No
banco"**, embora o backend sempre tenha suportado; e `/gastos/recorrentes` era uma lista de
cards indiferenciados, sem as três seções por tipo, sem a coluna de status do mês de referência
e sem o botão `[Preencher]` proeminente que gera o `RecurringExpenseEntry`.

**Backend.** Nenhum endpoint novo de escrita; só enriquecimento de leitura (aditivo,
retrocompatível) e uma extração para não duplicar regra de negócio.
- `app/gastos/gastos_ops.py`: **duas funções novas** — `estimate_monthly_cost(conta)` (custo
  mensal estimado, normalizando frequência: semanal ×4, quinzenal ×2, anual ÷12; variável usa o
  teto da faixa) e `recurring_summary(contas)` (`somas` por tipo + `programado_pendente_total`).
  Ambas foram **extraídas de dentro da view Jinja** `app/gastos/routes.py::recorrentes` (onde
  viviam como `_estimate`/somas inline) — a view passou a chamá-las, fonte única com a API
  (Princípio I).
- `app/api/gastos_read.py`: `_recurring_dict` ganhou parâmetros opcionais `ref_year`/`ref_month`
  e passou a serializar os rótulos derivados do model (`expected_label`, `dia_label`,
  `vigencia_label`, `parcelas_summary`), além de `estimated_monthly`, `has_entries`,
  `occurrences` (0 = "fora do ciclo") e `entries` (só para `programado`). O payload da listagem
  ganhou `ref_year`, `ref_month`, `weekday_labels`, `somas` e `programado_pendente_total`.
- `app/api/financeiro_read.py`: `kpis` ganhou `margem_bruta`, `margem_ebitda`, `tax_rate`
  (alíquota do `SiteSetting`, para o rótulo "Impostos Provisionados (16% · eventos com nota)")
  e as faixas do Fator R (`fator_r_rate_low`/`fator_r_rate_high`); cada linha de `eventos[]`
  ganhou `receita` e `event_type` (a tabela React não tinha como exibir a coluna Receita).

**Banco.** Sem migration — nenhuma coluna nova. `RecurringExpense`/`RecurringExpenseEntry` e
`SpecialExpense` seguem inalterados; toda a informação nova é derivada.

**Frontend.**
- `FinanceiroDashboardPage.tsx` **reconstruída** no layout clássico em grid: coluna principal
  (2/3) com 4 KPIs (Ticket Médio, Custo Talento/Receita, Margem Bruta, EBITDA), **termômetro de
  break-even** e **alerta fiscal do Fator R** — ambos com barra de progresso Tailwind
  (`role="progressbar"` + `aria-valuenow`) e badge de proteção tributária —, a **DRE Gerencial
  com identação hierárquica** (linhas `(–)` recuadas, subtotais `=` em faixa destacada, EBITDA e
  Resultado Líquido com régua superior) e os 3 cards de A Receber/A Pagar/Pago. Coluna analítica
  (1/3) com Receita por Tipo (barras horizontais), Top Vendedores ranqueados, Auditoria de Input,
  Notas a Emitir, Tendência de 6 meses e Recebimentos Previstos. Tabela de Eventos no Período em
  largura total, agora com Receita e Tipo.
- `PagamentosPage.tsx`: ordem de colunas do Jinja restaurada (checkbox · vencimento · descrição
  detalhada com badge de tipo · favorecido em **bold** · valor · chave PIX com tipo · situação);
  **botão compacto de cópia** ao lado da descrição, do valor (formato cru `1234,56`) e da chave
  PIX, com feedback "✓" temporário e `aria-live`; **checkbox "selecionar tudo"**; ação em lote
  **"Marcar como no banco"** (o backend já aceitava `no_banco` em `bulk-action`); seletor de
  situação colorido por estado, com as opções que cada tipo realmente suporta.
- `GastosRecorrentesPage.tsx` **refeita** em três seções tabulares (Contas Variáveis, Débito
  Automático, Assinaturas/Cartão) + Pagamentos Programados, com resumo mensal no topo, seletor
  de mês de referência e formulário de criação completo (tipo, frequência, dia/dia-da-semana,
  vigência, faixa **ou** valor exato, cartão, PIX padrão, observações). Cada linha traz
  `[Preencher]` (Dialog de `@manto/ui` com `MoneyInput`), `[Pular mês]`, `[Pagar]`/`[Reabrir]`,
  `[Histórico]` (Dialog consumindo o endpoint novo), `[Editar]` (Dialog) e
  `[Desativar]`/`[Excluir]` com confirmação em Dialog.
- `lib/financeiro.ts` e `lib/gastos.ts`: tipos estendidos (zero `any`) + hook novo
  `useRecorrenteHistorico`.

**Rotas e endpoints.**
- **Novo:** `GET /api/gastos/recorrentes/<conta_id>/historico` — todos os lançamentos da conta,
  do mais recente para o mais antigo (equivale ao painel `?conta=<id>` da tela Jinja).
- **Alterados (aditivos):** `GET /api/financeiro/dashboard` e `GET /api/gastos/recorrentes`.
- Rotas de página inalteradas.

**RBAC e regras de negócio.** Sem mudança. O endpoint novo usa o mesmo gate
`gastos_ops.is_financeiro` (FINANCEIRO/SUPERADMIN) dos demais de recorrentes; a página Jinja
legada segue funcionando (`/gastos/recorrentes` e `/financeiro/` verificados em 200 após a
extração para `gastos_ops`).

**Riscos e pegadinhas.**
- **Os status de pagamento do backend são exatamente três**: `nao_pago` ("Não pago"), `pago` e
  `no_banco` (`_VALID_PAYMENT_STATUS` em `app/api/financeiro_write.py` e `_STATUS_LABELS` em
  `app/financeiro/routes.py`). Não existem `pendente` nem `agendado` — "pendente" é o rótulo de
  UI de `nao_pago`. `commission` e `recurring` **não têm** `no_banco`: em lote o backend
  devolve o item em `skipped`, e a UI já nem oferece a opção.
- **`text-amber`/`bg-amber-soft` não existem** no preset do design system
  (`@manto/ui/tailwind-preset` tem `green`, `red`, `blue`, `gold`, `accent` — não `amber`). A
  versão anterior de `GastosRecorrentesPage` usava essas classes no alerta do topo e elas nunca
  renderizaram cor nenhuma. Estados de atenção agora usam `gold`.
- `occurrences === 0` significa **"fora do ciclo"** (fora da vigência ou da frequência no mês),
  não "sem lançamento" — sem esse campo no payload a UI teria que reimplementar
  `RecurringExpense.occurrences_in_month`, que é regra de negócio real.
- O botão `[Excluir]` da conta só aparece com `has_entries === false`; com histórico o caminho é
  desativar (`delete_recurring` levanta `GastoStateError` → 409).
- Verificação funcional: `scripts/db/verify_189_financeiro_alta_fidelidade.py` (**51/51** contra
  `manto_local`) — novos campos do dashboard, `no_banco` individual **e** em lote com persistência
  conferida no banco, resumo/rótulos/`occurrences` das recorrentes, `preencher` gerando o
  `RecurringExpenseEntry` que aparece na planilha de pagamentos, e o histórico (200/404/403).
  Fluxo completo também exercitado no navegador contra `manto_local` (criar conta → `[Preencher]`
  com máscara BRL → linha vira "a pagar R$ 512,30" → item aparece na planilha de pagamentos).

### 188 — Refatoração e Paridade do Módulo de Formulários
`188-formularios-paridade-listagem` · **2026-07-27** · **sem migration**

**Motivação.** A migração para React deixou `/formularios` com menos informação que a tela Jinja
antiga: o painel superior com os **links públicos copiáveis** havia sumido, a listagem virou uma
pilha de cards sem **Data do evento**, o "Recebida em" perdeu a **hora**, e a "Situação" caiu para
texto cinza ("Sem cliente • Sem evento") em vez dos **badges coloridos**. Esta entrada restaura a
paridade e moderniza o editor de campos.

**Backend.**
- `app/api/formularios_admin_read.py`: **`client_name` promovido do detalhe para o
  `_response_summary`** — a coluna "Situação" da listagem precisa do nome para o badge
  "Cliente: `<nome>`". `_response_detail` deixa de duplicá-lo (herda do summary).
- `app/formularios/formularios_ops.py`: `list_responses` e `search_responses` passam a fazer
  `joinedload(FormResponse.client)`. Sem isso, ler `r.client.name` em até 200 linhas geraria
  N+1 queries.
- **Correção de bug Postgres-only** em `app/gastos/gastos_ops.py::search_events_by_date`:
  `func.date(CalendarEvent.start_at) == day.isoformat()` comparava um `date` com **string** e
  estourava `psycopg.errors.UndefinedFunction: operador não existe: date = character varying`
  → `GET /api/gastos/eventos?date=...` respondia **500 em produção**. Agora compara com o próprio
  `date`. O SQLite de dev aceitava a comparação (tipagem dinâmica), então o bug nunca aparecia
  localmente. Afetava o seletor "vincular evento" **desta** tela e o da tela de Gastos Extras
  (mesmo hook `useGastosEventos`).
- Nenhum endpoint novo, nenhuma mudança de RBAC.

**Banco.** Nenhuma alteração de schema.

**Frontend.**
- `FormulariosAdminPage.tsx` reescrita: **gerenciador de links públicos** (dois cards com URL
  somente-leitura, "Copiar link" com confirmação "✓ Copiado" + `aria-live`, "Abrir" em nova aba e
  atalho SUPERADMIN para o editor); **tabela densa** com as 6 colunas da tela antiga (Contratante,
  Formulário, Data do evento, Recebida em com `DD/MM/AAAA HH:mm`, Situação, Ver); badges de
  situação via `MetricBadge` (verde resolvido / âmbar pendente); busca + abas de tipo de
  formulário; detalhe e editor em `Dialog` de `@manto/ui` (antes eram painéis inline).
- **Novo** `components/FormFieldEditor.tsx`: editor de `FormFieldDefinition` com formulário real
  (rótulo, seção com `datalist`, tipo, opções, ajuda, placeholder, obrigatório) no lugar dos
  `window.prompt()`/`window.confirm()` anteriores.
- `lib/formulariosAdmin.ts`: `client_name` no `FormResponseSummary`; `FIELD_TYPES` e
  `optionsToText()` (converte o `options` JSON do backend em texto "uma opção por linha");
  `UpdateFieldInput` explícito.
- `EventCreatePage.tsx`: aceita **`?form_response_id=<id>`** e pré-preenche pré-contrato vinculado,
  data do evento e cliente associado — reusando `GET /api/formularios/respostas/<id>` (mesmo RBAC),
  sem endpoint novo.

**Princípio V (nenhum botão morto).** Todo disparador de mutation desta tela dá retorno visual:
`Button loading` em associar/desassociar/vincular/desvincular/salvar/excluir; nas linhas de
resultado da busca de cliente e nas setas ↑/↓ do editor, o estado usa `mutation.variables` para
que **só o item clicado** fique em spinner (e não a lista inteira); o `<select>` de evento — que é
o próprio gatilho da ação — trava e troca o rótulo para "Vinculando…" enquanto o vínculo está em
voo. "Copiar link" não é assíncrono: confirma inline com "✓ Copiado" + `aria-live`.

**RBAC e regras de negócio.** Inalterados. Respostas seguem em `_require_vendas()`
(COMERCIAL/FINANCEIRO/SUPERADMIN) e o editor em `_require_superadmin()`; a UI só espelha o
`can_edit_structure`/`is_superadmin` que o servidor já devolve.

**Rotas e endpoints.** Nenhum novo. `/formularios` mantém a rota; `/events/new` ganha o parâmetro
opcional `form_response_id` (o `orcamento_id` continua funcionando igual).

**Riscos e pegadinhas.**
- **`update_field` substitui, não faz merge**: omitir `help_text`/`placeholder`/`required` no PATCH
  **apaga** esses atributos. A versão anterior da tela mandava só `label` + `required` num
  `window.prompt()` e silenciosamente limpava ajuda/placeholder do campo. O editor novo sempre
  envia o payload completo.
- `field_type` e `section_name` são **imutáveis** após a criação (o backend nunca os altera) — o
  formulário de edição os desabilita e explica o porquê.
- Os links dos cards usam `window.location.origin` + `/catalogo/f/<slug>`, que só resolve no build
  de produção (onde `frontend/server.js` serve `apps/public` sob `/catalogo/*`). No dev server do
  `apps/internal` (:5173) o link abre um 404 da SPA — esperado, não é regressão.
- **`func.date(coluna) == <str>` é bomba-relógio neste repo**: passa no SQLite e explode no
  Postgres. Ao escrever qualquer filtro por dia, compare com o objeto `date` — e verifique contra
  `manto_local`, nunca contra o SQLite de `instance/` (regra do `CLAUDE.md`). Foi assim que o 500
  do `/api/gastos/eventos` apareceu: só ao exercitar o seletor de evento contra o Postgres local.
- Verificação funcional: `scripts/db/verify_formularios_listagem_paridade.py` (20/20 contra
  `manto_local`) — cobre `client_name` em listagem/busca/detalhe, `event_date`/`created_at`
  serializados e o RBAC dos três endpoints. O 500 do `/api/gastos/eventos` foi confirmado
  (e a correção validada) direto contra `manto_local`: 2026-08-22 → 3 eventos, 2026-08-15 → 1.

### 187 — Reestruturação do Módulo de Comissões
`187-comissoes-modulo-completo` · merge **2026-07-24** (`4c20e47`) · **sem migration**

**Motivação.** A tela `/financeiro/comissoes` misturava a visão do vendedor com a do financeiro,
dependia do cliente para restringir escopo e sofria de dessincronização ao marcar comissões como
pagas uma a uma.

**Backend.**
- Novo módulo de núcleo de negócio **`app/financeiro/comissoes_ops.py`** (385 linhas): dataclasses
  `CommissionEntry`, `CommissionKpis`, `CommissionMonthSummaryRow`, `PayoutResult`; funções
  `parse_month_strict`, `resolve_month`, `get_month_entries`, `get_month_summary_by_seller`,
  `get_month_kpis`, `pay_seller_month`. Exceções próprias `InvalidMonthError` e
  `SellerNotFoundError`.
- `GET /api/financeiro/comissoes` reescrito: devolve `month`, `can_manage`, `title`, `kpis`,
  `by_seller`, `entries` e (só para gestor) `sellers`. Continua chamando
  `_resync_pending_commissions()` de `app/financeiro/routes.py` para não duplicar a reconciliação.
- **Novo** `POST /api/financeiro/comissoes/pagar-mes` — liquidação em lote atômica por
  vendedor/mês, com `SELECT ... FOR UPDATE` (`with_for_update()`) sobre os registros elegíveis.
  Duas chamadas concorrentes (duplo clique / duas abas): a segunda espera a primeira commitar,
  relê o estado, encontra 0 elegíveis e reporta `changed_count = 0` — **idempotente, nunca paga
  duas vezes**. Registra `audit("payment", "commission_month", ...)`.
- Decisão explícita: `app/financeiro/routes.py` (Jinja legado) **não** foi tocado e **não**
  importa `comissoes_ops` — mantém sua própria cópia de `_bulk_set_commission_period`.

**Banco.** Nenhuma alteração de schema. `CommissionPayment` já tinha tudo que era necessário
(`status`, `paid_at`, `payable_from`, `original_id`, `amount` assinado).

**Frontend.**
- `ComissoesPage.tsx` reconstruída (~464 linhas alteradas): 3 cards de KPI, seletor de mês,
  **duas abas** (Resumo por Vendedor / Detalhamento de Vendas), accordion por vendedor, modal de
  confirmação com o valor somado no servidor, e **export CSV** do resumo.
- Três componentes novos em `@manto/ui`: **`AccordionRow`**, **`Dialog`** e **`Tabs`**.

**RBAC e regras de negócio.**
- **O servidor decide o escopo**: `seller_filter = requested_seller_id if can_manage else
  current_user.id`. Vendedor comum nunca recebe dados de outro, mesmo forçando `seller_id` na
  querystring.
- `can_manage` = `FINANCEIRO` ou `SUPERADMIN`. Título muda para **"Minhas Comissões"** quando
  falso, e nenhuma ação de pagamento é renderizada.
- O **responsável EducaManto** sem papel Financeiro continua sendo vendedor comum nesta tela.
- `pagar-mes` responde **403** para não-gestor, inclusive para o próprio `seller_id`.
- **Estornos** (`amount < 0`, `status='a_pagar'`) aparecem em **qualquer mês** até serem resolvidos
  (`_pending_reversals_query`, sem filtro de mês, deduplicado por `id`) e só são liquidados junto
  com as demais comissões do vendedor — nunca isoladamente.
- KPIs derivam do **mesmo** resumo que alimenta o botão "Pagar Mês", garantindo que batem centavo
  a centavo com o que pode ser efetivamente liquidado.

**Pegadinhas.** Mês inválido cai silenciosamente no mês corrente em `resolve_month` (leitura), mas
`pay_seller_month` usa `parse_month_strict` e **falha** — a escrita nunca adivinha o mês.

---

### 186 — Gerenciador de Catálogo: UX e fluxo Ficha ↔ Catálogo ↔ Venda
`186-gerenciador-catalogo-ux` · merge **2026-07-24** (`31310d3`) · **sem migration**

**Motivação.** A 185 entregou a estrutura Tema/Personagem funcional, mas "cega": a busca de elenco
mostrava só nome, o vínculo com a Ficha de Figurino só existia por um lado, e não havia forma de
tratar em lote o acervo antigo sem vínculo.

**Backend.**
- `GET /api/catalogo/elenco-busca` passou a servir também o lado da Ficha: gate ampliado para
  `COMERCIAL`, `FIGURINO` e `SUPERADMIN` (antes era só o fluxo comercial), incluindo `photo_url` e
  `figurino_sheet_id` de cada Personagem — dado interno, por isso fora da grade pública.
- **Novo** `POST /api/admin/catalogo/personagens/mover-em-massa` +
  `catalog_character_ops.move_characters(character_ids, target_item)`.
- `admin_catalogo_read` passou a expor o indicador de vínculo pendente por Personagem.

**Banco.** Nenhuma alteração. **Decisão de projeto**: o vínculo bidirecional reusa a coluna
existente **`catalog_characters.figurino_sheet_id`** — não há coluna espelho em `figurino_sheets`;
o "personagem vinculado" de uma ficha é derivado por busca inversa.

**Frontend.**
- **`CharacterAutocomplete`** — busca visual com miniatura, filtrada para **Personagens filhos
  ativos** (Temas pai nunca aparecem); placeholder quando não há foto; ao selecionar preenche nome
  e `figurino_sheet_id` na linha do elenco.
- **`CatalogTreeView`** (árvore hierárquica Tema → Personagens, com guia de recuo),
  **`CatalogCardGrid`**, **`KebabMenu`** e **`CatalogBulkActionBar`** (barra flutuante de ações em
  massa: Mover para… / Inativar / Excluir; "Mover" só existe para Personagens).
- `/admin/catalogo`: alternador **Cards ⇄ Árvore** persistido em `localStorage`
  (`manto_admin_catalogo_view`), seleção múltipla, e associação rápida "+ Vincular Ficha".
- `FigurinoFormPage`: campo **"Vincular a um Personagem do Catálogo"** com Desvincular.
- `FigurinoListPage`: indicador **"⚠ Sem personagem vinculado"** + modal de vínculo em 2 cliques.
- **US6 — deploy**: `frontend/server.js` novo (serve `apps/internal/dist` na raiz e
  `apps/public/dist` sob `/catalogo/*`, cada um com seu fallback de SPA), `base` condicional em
  `apps/public/vite.config.ts`, `basename` condicional em `apps/public/src/App.tsx`,
  `frontend/nixpacks.toml` passando a compilar os **dois** apps, e correção do link "/catalogo" no
  menu lateral.

**RBAC.** Gerenciador continua exclusivo de `SUPERADMIN`. A exceção é `elenco-busca`, aberta
também a `COMERCIAL` e `FIGURINO` — comercial escala evento e figurino vincula ficha sem ser
superadmin.

**Regras de negócio.** Um Personagem aponta para **no máximo uma** Ficha por vez: vincular pelo
lado da Ficha **substitui** o vínculo anterior, nunca duplica.

**Pegadinhas.** Um *Build/Start Command* customizado no painel do Railway tem precedência sobre o
`nixpacks.toml` — foi exatamente um build command com sintaxe de Turborepo/pnpm que causou o erro
"Missing script: build". Os dois campos precisam ficar vazios.

---

### 185 — Catálogo Vitrine Completo: Temas, Personagens e Vídeo
`185-catalogo-vitrine-completo` · merge **2026-07-24** (`17e6e11`, + fix `528e561`) ·
migration **`9f1c3a7b5e2d`**

**Motivação.** O catálogo só suportava fotos e tratava cada produto como uma unidade indivisível —
invisível para o cliente que um Tema é composto por atrações individuais também contratáveis.

**Banco (migration `9f1c3a7b5e2d` — head atual).**
- **Nova tabela `catalog_characters`**: `catalog_item_id` (FK → `catalog_items`, **ON DELETE
  CASCADE**), `name`, `slug` (unique, prefixado pelo slug do Tema), `photo_url`, `video_url`,
  **`figurino_sheet_id`** (FK → `figurino_sheets`, **ON DELETE SET NULL**), `position`,
  `is_active`, `created_at`; índice `ix_catalog_characters_catalog_item_id`.
- **Nova coluna `catalog_items.video_url`** (Drive/MP4/Vimeo).

**Backend.**
- Novo `app/admin/catalog_character_ops.py`: `unique_character_slug`, `create_character`,
  `update_character`, `delete_character`, `_validate_video_url`, `_validate_photo_extension`.
- Novo `app/catalogo/media.py` (normalização/detecção do tipo de vídeo).
- Endpoints novos: `POST /api/admin/catalogo/<item_id>/personagens`,
  `PATCH|DELETE /api/admin/catalogo/personagens/<character_id>`,
  `GET /api/admin/catalogo/tags`, `GET /api/catalogo/elenco-busca`.
  `GET /api/catalogo/<slug>` passou a devolver `video_url`, `video_kind` e o elenco de Personagens.

**Frontend.**
- **Público**: `VideoPlayer` (autoplay mudo em loop, botões próprios de som e tela cheia),
  `ProductGallery` com **transição animada de altura** entre foto horizontal e vídeo 9:16,
  `CharacterCard`/`CharacterGrid` para a seção **"Elenco Individual"**, `WishlistButton` por
  Personagem. Vídeo inválido é ignorado silenciosamente na vitrine.
- **Interno**: `ChipInput` (tags com Enter/vírgula, autocomplete das tags existentes),
  `AdminCatalogCharacterPanel` (CRUD de Personagens com foto, vídeo e dropdown de Ficha de
  Figurino), `ElencoBlock` do Novo Evento passando a auto-vincular a ficha do Personagem
  selecionado.
- Suíte E2E nova para catálogo público e admin; `verify_185.py` de verificação funcional.

**Regras de negócio.**
- URL de vídeo não reconhecida (não é Drive/MP4/Vimeo) é **recusada com erro no campo** no
  gerenciador.
- Excluir um Tema **apaga em cascata** seus Personagens; excluir uma Ficha **apenas desvincula**
  (`SET NULL`), sem apagar o Personagem.
- A lista de interesse do cliente aceita Tema completo **e** Personagem individual como itens
  distintos.

**Fix pós-merge (`528e561`).** Alvo de toque do botão "copiar link do Personagem" no mobile.

---

### 184 — Reconstrução do Formulário de Cadastro/Edição de Eventos
`184-eventos-formulario-completo` · merge **2026-07-24** (`1da7be6`) · **sem migration**

**Motivação.** `/events/new` no app React não tinha paridade de campos com a tela Jinja em
produção, forçando o vendedor a voltar para a tela antiga — risco real de dado divergente na tela
mais crítica do comercial. E a edição estava espalhada em várias ações soltas na tela de detalhe.

**Backend.**
- `app/calendar/event_ops.py` ampliado (+255 linhas): `update_event_core` e a reconciliação de
  elenco por `role_id`.
- `POST /api/events` e **`PATCH /api/events/<id>`** cobrindo os 7 blocos; `_build_create_event_data`
  / `_build_update_event_data` normalizam o corpo JSON. Validação central via `_validate_event_core`,
  devolvendo **`fields`** no envelope de erro para o formulário apontar o campo exato.
- `agenda_read.py` passou a serializar os campos que faltavam para pré-preencher a edição.
- Falha ao criar o evento no Google Calendar devolve **502** com mensagem amigável.

**Banco.** Nenhuma alteração — a feature foi de paridade e UX sobre o schema existente.

**Frontend.**
- `EventCreatePage.tsx` reescrita (982 linhas alteradas) e **`EventEditPage.tsx` nova** (489
  linhas), ambas montadas sobre **7 blocos** compartilhados em
  `src/components/EventFormBlocks/`: Cliente · Dados do Evento · Elenco · Valores · Pagamento ·
  Contrato · Observações.
- `eventFormSchema.ts` novo: validação `onBlur` imediata, banner de erro no topo **e** no rodapé,
  **auto-scroll suave até o primeiro campo inválido com foco**, e limpeza do destaque assim que o
  campo é corrigido.
- `ClientPicker` ganhou **cadastro rápido inline** (reaproveita cliente existente por telefone) e
  seletor de relação (Contratante/Assessora/Mãe-Pai/Familiar/Outros).
- `PendingAttachmentsPanel` novo: anexos escolhidos antes do evento existir sobem em **fase 2**,
  após a criação.
- Rota `/events/:id/edit` registrada no `App.tsx`; suíte E2E `event-form.spec.ts`.

**RBAC.** `_can_create_event()` / `_can_edit_event()` = `COMERCIAL` + `SUPERADMIN`, com paridade
verificada contra `_CAN_CREATE` / `_CAN_EDIT_EVENT` do Jinja. Acesso direto à URL de edição por
papel sem permissão (ex.: `ENSAIO`) é bloqueado no servidor.

**Regras de negócio confirmadas na tela.**
- Evento tipo **SHOW sempre gera ensaio**, independentemente do checkbox (o aviso é explícito).
- Percentual de desconto = `sale_value_gross − sale_value`, calculado em tempo real.
- *Faturado* exige vencimento; *Dividido no PIX* exige parcelas entre **2 e 12**.
- Fora de cortesia/permuta, os dois valores de venda são obrigatórios.
- Horário de fim não pode ser igual ao de início.
- Na edição, o elenco é **reconciliado** por `role_id` (não substituído), e agrupamento comercial
  / sincronização com o Google não são alterados pela feature.

---

### Contexto imediatamente anterior (para leitura do histórico)

| Feature | Entrega | Migration |
|---|---|---|
| **183** | Reestruturação do Banco de Figurinos — tags JSON na ficha, alerta "personagem sem ficha" com dispensa rastreável (`figurino_missing_dismissals`), impressão legada linkada da SPA | `7c2d9e4f1a3b`, `4e6f8a1c2d5b` |
| **182** | Revisão de mídia com Vimeo; correção do proxy Vite de `/uploads` | `aa1bb2cc3dd4` |
| **181** | Avaliações — fidelidade visual e RBAC | — |
| **180** | Módulo de Talentos completo (modo edição unificado em `/talents/:id?edit=1`) | — |
| **144** | Migração React SPA concluída (constituição v2.0.0) — fatias 145–177 | — |

**Correção pontual pós-187** — `6d6e234` (2026-07-25, branch `fix-figurino-nova-ficha-foto`):
completa o formulário de **Nova Ficha** de figurino (foto, textos de apoio, obrigatoriedade do
nome do personagem). Só frontend, sem impacto de schema, API ou RBAC.

---

## Convenções para as próximas entradas

1. **Append no topo** da seção "Registro", nunca no fim.
2. Sempre declarar **se houve migration** (e qual `revision`) — ou "sem migration", explicitamente.
3. Sempre declarar **impacto em RBAC**, mesmo quando for "nenhum".
4. Rotas novas ou alteradas precisam também ser refletidas em
   [`01_SISTEMA_E_BANCO.md`](01_SISTEMA_E_BANCO.md) §3 e, se tiverem tela,
   em [`02_MAPA_DE_PAGINAS_E_UX.md`](02_MAPA_DE_PAGINAS_E_UX.md).
5. Registrar **pegadinhas** descobertas na implementação — é a parte do documento que mais evita
   retrabalho.

# Orcamento EducaManto: verificar adicao de personagens Manto (agregacao com calculadora de orcamento) + i de informacao sem mensagem

## Resumo
A "adição de personagens Manto" NÃO foi perdida: a US4 da spec 235 (Contratação Manto embutida) está implementada de ponta a ponta — tela, motor, snapshot e PDF — e foi para produção no merge 30b24e7. O que existe é um problema de descoberta (o card é o ÚLTIMO da coluna esquerda, abaixo do textarea de observação) somado a 4 defeitos reais menores, sendo o pior o silêncio quando nenhuma duração está marcada. Já o "i" de informação nunca mostra mensagem porque a dica foi implementada só como atributo HTML nativo `title` num span de 12px — não existe componente de Tooltip no @manto/ui, então clique, toque e teclado não produzem nada.

## Causa raiz
Bug do "i": `frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx:570` — a dica foi implementada APENAS como o atributo HTML nativo `title` num `<span>` de `text-xs` (glifo de ~10x16px), sem nenhum componente de tooltip da aplicação (não existe Tooltip em `frontend/packages/ui/src/components/`, nem `@radix-ui/react-tooltip` em `frontend/packages/ui/package.json:12-16`). O `title` nativo só dispara com hover do MOUSE parado ~1s exatamente em cima do glifo; não responde a clique (não há `onClick`/`onFocus` no span), não existe em toque, não é alcançável por teclado (span puro, sem `tabIndex`) e some se o ponteiro se mover. Ou seja: para qualquer gesto que não seja "parar o mouse em cima do ⓘ por um segundo", o código produz literalmente nenhuma mensagem — exatamente o relato.

Falha secundária no mesmo ponto (`:554-575`): quando `useEducaMantoTextos` ainda está carregando ou falha, `info` é `undefined` → o ⓘ some por completo (`:567`) E os rótulos degradam para as chaves cruas "som"/"iluminacao"/"alimentacao" (`:565`), sem nenhum estado de loading/erro na tela — a query tem `staleTime: Infinity` (`frontend/apps/internal/src/lib/educamanto.ts:106`) e nenhum consumidor trata `isError`.

Defeito real na contratação Manto (silêncio, não "perda"): `frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx:134-148` — quando o vendedor ativa a contratação e desmarca TODAS as durações, `duracoes.length === 0` e o front envia `contratacao_manto: null`. A validação que deveria barrar isso está em `app/educamanto/quote_ops.py:82-88` e só roda se `contratacao_manto` for truthy — logo nunca dispara. Resultado: o orçamento é gerado e congelado SEM a parte Manto, sem nenhum aviso, contrariando o Edge Case da `specs/235-educamanto-responsabilidades/spec.md:162` ("Contratação Manto sem nenhuma duração selecionada: geração bloqueada com aviso").

## Comportamento atual (evidencia)
A) CONTRATAÇÃO MANTO (agregação com a calculadora de orçamento) — EXISTE E FUNCIONA.

Tela: `frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx:828-967` — card "Contratação Manto (apresentação tradicional)" com botão "+ Adicionar contratação Manto" (:843-854), horário (:867-883), durações 1h/2h/3h/4h + "Extra (h)" (:885-924), `PerformersEditor` (:928-940, é onde se adicionam os personagens/atores/especiais e o coordenador) e `AcrescimosEditor` (:943-949).
Fonte única de UI: `frontend/apps/internal/src/components/orcamento/PerformersEditor.tsx` (extraído na T019), consumido também por `frontend/apps/internal/src/pages/OrcamentoCalculadoraPage.tsx:467`.
Envio: `configParaInput` monta `contratacao_manto: {duracoes, payload}` em `EducaMantoCalculadoraPage.tsx:121-150`.
Backend: `app/educamanto/quote_ops.py:109-156` (`_totais_contratacao`) chama `app.orcamento.quote_ops.calculate_quote` forçando `nota_fiscal=False`/`fora_sp=False` (:122-123) e extrai `total_1h..total_4h`/`total_custom`; `:175-184` congela o snapshot da contratação.
Fechamento: `app/educamanto/pricing_ops.py:364-374` (`_combinado`) soma ao líquido e aplica ceil100 e ÷0,84 UMA vez sobre a soma (FR-016); `:437-440` gera `combinados`.
Resultado na tela: card dourado "Totais com contratação Manto (NF sobre a soma)" em `EducaMantoCalculadoraPage.tsx:1030-1049`.
PDF: `app/educamanto/pdf.py:208-228` — seção "COM CONTRATAÇÃO MANTO (apresentação tradicional)" com "Inclui: <team_lines>" e um total combinado por duração.
Status na esteira: `specs/235-educamanto-responsabilidades/tasks.md:74-83` — T019/T020/T021/T022 todas [x]. Documentado em `docs/02_MAPA_DE_PAGINAS_E_UX.md:1234` e `docs/03_HISTORICO_MUTACOES.md:435-438`.

Por que parece perdida: (1) o card é o ÚLTIMO da coluna esquerda, depois de Responsabilidades → Dias e ensemble → Transporte → Acréscimo do vendedor (que ainda contém nome do cliente e o textarea de 2.000 chars) — fica fora da primeira dobra; (2) só aparece para SUPERADMIN/COMERCIAL (`EducaMantoCalculadoraPage.tsx:230-233`), coerente com `app/api/orcamento_read.py:30-33/46-48` que exige COMERCIAL/SUPERADMIN em `/api/orcamento/opcoes`, mas a calculadora EducaManto também é usada por ENSAIO e REVENDEDOR_EDUCAMANTO (`app/api/educamanto_read.py:19-24`), que nunca veem o card; (3) nada na área de Responsabilidades nem na coluna de resultado indica que essa opção existe.

B) O "i" DE INFORMAÇÃO — NUNCA MOSTRA MENSAGEM.

`frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx:567-575`:
    {info?.tooltip && (
      <span className="cursor-help text-xs text-muted" title={info.tooltip} aria-label={`Dica: ${info.tooltip}`}>ⓘ</span>
    )}
O conteúdo existe e chega corretamente: `app/educamanto/pdf_textos.py:27-85` (chaves `tooltip` de som/iluminacao/alimentacao) → `app/api/educamanto_read.py:151-164` (`GET /api/educamanto/textos`) → `frontend/apps/internal/src/lib/educamanto.ts:98-108`. O texto NÃO é o problema.

C) Fatos verificados que sustentam o diagnóstico: é a ÚNICA ocorrência de `ⓘ` e a única de `cursor-help` em todo o monorepo (grep em `frontend/apps/*/src`); não existe componente Tooltip/Popover em `frontend/packages/ui/src/components/` (22 arquivos, nenhum tooltip) nem export "Tooltip" em `frontend/packages/ui/src/index.ts`; as dependências Radix em `frontend/packages/ui/package.json:13-15` são só dialog, slot e tabs — não há `@radix-ui/react-tooltip`. Nenhum CSS global interfere (`frontend/apps/internal/src/index.css` e `frontend/packages/ui/src/theme.css` não têm `pointer-events`/regras sobre `[title]`).

## Arquivos relevantes
- C:/Users/schim/Desktop/Manto_Platform/frontend/apps/internal/src/pages/EducaMantoCalculadoraPage.tsx (62-150, 230-233, 386-389, 554-608, 828-967, 1030-1049) — Tela da calculadora: causa raiz do 'i' (567-575), montagem/envio da contratacao (121-150), gate de papel (230-233), card da contratacao Manto (828-967), totais combinados (1030-1049), copia rasa de pagina (386-389)
- C:/Users/schim/Desktop/Manto_Platform/frontend/apps/internal/src/components/orcamento/PerformersEditor.tsx (16-100) — Editor de personagens (ator/cantor/especial + coordenador) compartilhado entre /orcamento e a contratacao Manto do EducaManto — e onde se 'adicionam personagens Manto'
- C:/Users/schim/Desktop/Manto_Platform/frontend/apps/internal/src/components/orcamento/AcrescimosEditor.tsx (1-76) — Editor de acrescimos/BV compartilhado, usado pela contratacao Manto
- C:/Users/schim/Desktop/Manto_Platform/frontend/apps/internal/src/lib/educamanto.ts (98-108, 150-197, 388-421) — Hook useEducaMantoTextos (fonte do tooltip, staleTime Infinity sem tratamento de erro) e tipos ContratacaoMantoInput/TotalCombinado/SnapshotV2Config
- C:/Users/schim/Desktop/Manto_Platform/app/educamanto/pdf_textos.py (27-89) — Fonte unica dos textos: label/tooltip/manto/contratante das 3 responsabilidades — o conteudo do 'i' existe e esta correto
- C:/Users/schim/Desktop/Manto_Platform/app/api/educamanto_read.py (19-35, 151-164, 201-223) — GET /api/educamanto/textos (serve os tooltips), POST /api/educamanto/calcular e RBAC _CAN_USE (inclui ENSAIO e REVENDEDOR_EDUCAMANTO)
- C:/Users/schim/Desktop/Manto_Platform/app/educamanto/quote_ops.py (80-92, 109-156, 159-198, 240-263) — Parse/validacao da contratacao (a validacao de duracao vazia em 82-88 nunca dispara), chamada a calculate_quote e congelamento do snapshot v2
- C:/Users/schim/Desktop/Manto_Platform/app/educamanto/pricing_ops.py (364-374, 428-440) — Soma da parte Manto ao liquido com NF unica sobre a soma (FR-016) e geracao de `combinados`
- C:/Users/schim/Desktop/Manto_Platform/app/orcamento/quote_ops.py (58-110, 345-357, 415-433, 470-493) — Motor unico da calculadora de orcamento reusado pela contratacao: totals por duracao, total_custom (so >4h), team_lines e memoria
- C:/Users/schim/Desktop/Manto_Platform/app/api/orcamento_read.py (30-58) — /api/orcamento/opcoes exige COMERCIAL/SUPERADMIN — e o motivo do gate de papel no card da contratacao
- C:/Users/schim/Desktop/Manto_Platform/app/educamanto/pdf.py (208-228) — Secao 'COM CONTRATACAO MANTO' no PDF com team_lines e total combinado por duracao (T022 entregue)
- C:/Users/schim/Desktop/Manto_Platform/frontend/packages/ui/src/components/ — 22 componentes, NENHUM tooltip/popover — a lacuna que forcou o uso do title nativo
- C:/Users/schim/Desktop/Manto_Platform/frontend/packages/ui/package.json (12-16) — Radix disponivel: dialog, slot, tabs. Nao ha @radix-ui/react-tooltip/popover instalado
- C:/Users/schim/Desktop/Manto_Platform/specs/235-educamanto-responsabilidades/spec.md (122-135, 162, 179, 194-197) — US4 (contratacao embutida), FR-005 (tooltip obrigatorio), FR-014/015/016 e o Edge Case da duracao vazia que hoje nao e respeitado
- C:/Users/schim/Desktop/Manto_Platform/specs/235-educamanto-responsabilidades/tasks.md (74-83) — Fase 6 (US4) com T019-T022 marcadas [x] — prova documental de que a agregacao nao foi perdida
- C:/Users/schim/Desktop/Manto_Platform/specs/235-educamanto-responsabilidades/quickstart.md (29, 52-54) — Roteiro de validacao: 'tooltip visivel em cada bloco' e bloco 6 da contratacao Manto
- C:/Users/schim/Desktop/Manto_Platform/docs/02_MAPA_DE_PAGINAS_E_UX.md (1234) — Documentacao viva da rota /educamanto ja descreve a contratacao Manto embutida como entregue

## Abordagem proposta pela investigacao
Tudo é frontend + um componente novo no design system. NÃO precisa de migração, campo novo de banco nem endpoint novo.

1) Criar o componente que falta — `frontend/packages/ui/src/components/info-tip.tsx` (exportar em `frontend/packages/ui/src/index.ts`).
   - `<button type="button">` com o ⓘ (área de toque ≥ 24px, `aria-label`, `aria-describedby`, `aria-expanded`).
   - Abre em hover E em clique E em foco (teclado); fecha em Escape, blur e clique fora — mesmo padrão de `frontend/packages/ui/src/components/filter-dropdown.tsx`.
   - Painel `role="tooltip"`, `max-w-xs`, texto com quebra, `z-50`, posicionado relativo ao botão; entrada/saída em Framer Motion 150–200ms respeitando `useReducedMotion()` (Princípio IX).
   - Sem dependência nova: escrever à mão (o Radix instalado é só dialog/slot/tabs). Se preferir Radix, seria `@radix-ui/react-popover` — mas popover à mão aqui é mais barato que uma dependência nova.

2) Trocar o `title` pela `InfoTip` em `EducaMantoCalculadoraPage.tsx:567-575`, e endurecer o carregamento dos textos (mesmo bloco, :554-575):
   - Mapa fixo de rótulos em pt-BR no front como fallback (`{som: "Sonorização", iluminacao: "Iluminação", alimentacao: "Alimentação"}`) para nunca exibir a chave crua.
   - Enquanto `textosQuery.isLoading`, renderizar a InfoTip desabilitada (ou um Skeleton de 12px); se `isError`, exibir uma linha de aviso discreta no card de Responsabilidades ("Não foi possível carregar as dicas") — hoje não há nenhum feedback, o que contraria a regra de feedback imediato do CLAUDE.md.

3) Corrigir os 4 defeitos da contratação Manto (mesmo arquivo da calculadora):
   - `configParaInput` (:134-148): enviar `contratacao_manto` sempre que `c.ativa` for true (com `duracoes` como estão), para que a validação do servidor em `app/educamanto/quote_ops.py:82-88` finalmente dispare; e, em paralelo, desabilitar "Gerar orçamento" com mensagem inline quando `ativa && duracoes.length === 0` (servidor manda, tela antecipa).
   - `duracoesDaContratacao` (:116-119): aceitar qualquer `duracaoCustom > 0` que não seja 1/2/3/4 (hoje `> 4` ignora silenciosamente quem digita 3) e, para 1–4, marcar o checkbox correspondente em vez de descartar.
   - `handleNovaPagina` (:386-389): copiar `contratacao` em profundidade (`{...c.contratacao, performers: c.contratacao.performers.map(p => ({...p})), acrescimos: c.contratacao.acrescimos.map(a => ({...a})), duracoes: [...c.contratacao.duracoes]}`) — hoje a nova página compartilha a mesma referência.
   - FR-015 (local herdado): incluir `event_location: config.endereco || undefined` no `payload` da contratação (:138-146). Não muda preço (`app/orcamento/quote_ops.py:390` só usa no texto), mas fecha o requisito.

4) Descoberta (é o que fez o João achar que sumiu):
   - Mover o card "Contratação Manto" para logo depois de "Dias e ensemble" (antes de Transporte), ou colocar um botão "+ Contratação Manto" na barra de abas de páginas.
   - Quando `config.contratacao.ativa`, marcar a aba da página ("Página 1 · UAA + Manto") e acrescentar, sob os dois cards grandes Sem NF/Com NF (:1005-1028), uma linha explícita: "Estes valores NÃO incluem a contratação Manto — veja os totais combinados abaixo". Hoje o vendedor pode copiar o número errado.

5) Verificação: rodar o bloco 6 do `specs/235-educamanto-responsabilidades/quickstart.md` contra `manto_local` (1 ator + coordenador, durações 1h e 2h, conferir `ceil100(liquido_edu + total_1h)` e `ceil100(soma ÷ 0,84)`), gerar o PDF e conferir a seção "COM CONTRATAÇÃO MANTO"; `npx tsc --noEmit` limpo em `frontend/apps/internal`; e atualizar `docs/03_HISTORICO_MUTACOES.md` no topo.

## Riscos mapeados
- Mexer em EducaMantoCalculadoraPage.tsx toca a mesma tela em produção desde 17/08 — regressão ali afeta a venda do EducaManto inteira, não só a contratação. Validar o quickstart completo (blocos 2, 4, 6 e 7) antes de mergear.
- Passar a enviar contratacao_manto mesmo com durações vazias faz o servidor devolver 400 num caso que hoje passa silenciosamente: orçamentos que hoje 'funcionam' vão começar a ser recusados até o vendedor marcar uma duração. É o comportamento que a spec pede, mas é uma mudança visível para quem já usa.
- PerformersEditor e AcrescimosEditor são fonte única com /orcamento (OrcamentoCalculadoraPage.tsx:467/484) — qualquer ajuste neles reflete na calculadora de eventos tradicional; validar o bloco 10 do quickstart (/orcamento intacta).
- Componente novo em @manto/ui entra em todos os apps do monorepo (internal, portal, public): garantir que o build dos três continue limpo e que o InfoTip não vaze estilo para telas públicas mobile-first.
- Deploy: o bundle do frontend é cacheado no navegador. Depois do push, o João precisa recarregar forçado para ver o ⓘ novo — senão vira a mesma conversa do 'verifiquei em produção mas o usuário está com a versão antiga'.
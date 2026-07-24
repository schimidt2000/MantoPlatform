# Phase 0 Research: Revisão de Mídia estilo Vimeo

Nenhum `NEEDS CLARIFICATION` ficou pendente no Technical Context do plan.md — as decisões abaixo
documentam as escolhas técnicas feitas (não havia ambiguidade real, mas registra-se o raciocínio
para quem revisitar a feature depois).

## Decisão 1 — Player de vídeo: `<video>` nativo + controles custom, sem biblioteca externa

- **Decision**: Construir o player sobre o elemento `<video>` HTML5 nativo (`controls={false}`),
  com uma camada de UI própria em React (`VideoPlayer.tsx` + `VideoScrubber.tsx`) controlando
  play/pause/seek/velocidade via `ref` e os eventos padrão (`timeupdate`, `loadedmetadata`, `play`,
  `pause`, `ratechange`).
- **Rationale**: Todos os requisitos da spec (scrubber com marcadores, velocidades fixas, atalhos de
  teclado, tempo formatado) são alcançáveis com a API nativa do `<video>` (`currentTime`,
  `duration`, `playbackRate`, `paused`). Adicionar uma lib de player (video.js, Plyr, react-player)
  traria peso de bundle e uma segunda camada de abstração sem necessidade real — viola YAGNI/
  Governança da constituição ("na dúvida, escolha o caminho mais simples").
- **Alternatives considered**:
  - `video.js`/Plyr: descartado — a customização visual pedida (marcadores no scrubber ancorados em
    comentários) exige um scrubber próprio de qualquer forma, então a lib só adicionaria overhead
    sem resolver a parte específica do requisito.
  - `react-player`: descartado — é um wrapper genérico multi-fonte (YouTube, Vimeo, etc.); aqui o
    arquivo é sempre um `<video src>` direto do storage do projeto, sem necessidade da abstração.

## Decisão 2 — Marcadores do scrubber: cálculo derivado, sem estado novo no backend

- **Decision**: Os marcadores de comentário no scrubber são calculados no frontend a partir da lista
  de comentários já retornada por `useRevisaoComments` (`timecode / duration * 100%`), sem endpoint
  novo.
- **Rationale**: O dado (`timecode` por comentário) já existe; criar um endpoint agregado só para
  "posições de marcador" duplicaria informação sem necessidade (Princípio I).
- **Alternatives considered**: Endpoint dedicado `/asset/<id>/markers` — descartado, redundante.

## Decisão 3 — Status de aprovação: coluna nova em `ReviewAsset`, não tabela separada

- **Decision**: Adicionar `status = db.Column(db.String(20), nullable=False, default="em_revisao",
  server_default="em_revisao")` diretamente em `ReviewAsset`, sem tabela de histórico de status.
- **Rationale**: A spec (FR-013–FR-017) pede um valor atual por material, não um histórico auditável
  de mudanças de status (isso está fora de escopo — ver Assumptions do spec.md). Uma tabela separada
  seria complexidade não justificada (YAGNI).
- **Alternatives considered**: Tabela `review_asset_status_history` — descartada por não haver
  requisito de auditoria na spec; pode ser adicionada depois se for pedida.

## Decisão 4 — Reset de status ao substituir versão: dentro de `replace_asset()`, não um hook separado

- **Decision**: `review_ops.replace_asset()` passa a setar `asset.status = "em_revisao"` no mesmo
  fluxo que já reseta `finalized_at`/`file_removed` ao trocar de versão.
- **Rationale**: É o único ponto do sistema que já centraliza "o que muda quando a versão troca"
  (Princípio I — fonte única). Duplicar essa regra em outro lugar (ex.: no endpoint da API) quebraria
  a arquitetura em camadas (Princípio III).

## Decisão 5 — Testes e2e: Playwright com vídeo real de fixture

- **Decision**: O teste e2e usa um arquivo de vídeo pequeno (poucos segundos, alguns KB) commitado em
  `frontend/apps/internal/e2e/fixtures/` para upload via a tela de criação de espaço já existente
  (`RevisaoSpaceCreatePage`), e então exercita play/pause/seek/comentário/status na tela nova.
- **Rationale**: Sem um arquivo de vídeo real, não dá para verificar `duration`/`timeupdate`/seek de
  fato — mocks de rede não cobrem o comportamento do elemento `<video>` do browser.
- **Alternatives considered**: Mockar a resposta da API com uma URL de vídeo público externo —
  descartado por gerar dependência de rede externa instável no CI/execução local.

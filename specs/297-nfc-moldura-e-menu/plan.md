<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 297 — vídeo leve com moldura, menu na tag NFC e recado da cliente

**Branch**: `297-nfc-moldura-e-menu` | **Data**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/297-nfc-moldura-e-menu/spec.md`

**Nota**: preenchido pelo `/speckit-plan`. A constituição (`.specify/memory/constitution.md`,
v3.0.0) é lida em tempo de execução — o Constitution Check abaixo é o que ela cobra.

## Resumo

Um pipeline de conversão de vídeo resolve, de uma vez, a queixa e o pedido: todo vídeo enviado para
uma tag NFC passa a ser convertido para 1080 de largura em pé, com a moldura PNG da Manto gravada na
mesma passagem. Isso derruba o arquivo de até 147 MB para cerca de 15 MB, que é o que faz a cliente
conseguir assistir e o gerenciador voltar a tocar dez cards sem estourar o navegador. Em volta dele,
a página pública ganha uma máquina de cenas — capa, abertura com som, menu de três botões, mensagem
especial e recado — e o ERP ganha o estado do processamento e a caixa de recados.

A conversão é assíncrona por necessidade, não por elegância: o contêiner tem **uma CPU só**,
compartilhada com os três workers do gunicorn. Ela roda numa thread de fundo, um vídeo por vez, com
`nice -n 19`, seguindo o molde de thread que a casa já usa em cinco lugares.

Pesquisa completa, com medições: [research.md](./research.md). Modelo de dados:
[data-model.md](./data-model.md). Contratos de API: [contracts/](./contracts/). Como validar de
ponta a ponta: [quickstart.md](./quickstart.md).

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy) no backend; TypeScript + React 18 (Vite)
no frontend

**Dependências principais**: Flask, SQLAlchemy, Alembic (migrations à mão); React, TanStack
Query, Tailwind CSS, shadcn/ui (`@manto/ui`), Framer Motion, `@manto/api-client`
(`apiFetch`/`assetUrl`), `@manto/money`. **Nenhuma dependência nova**: o `ffmpeg 5.1.9` já existe em
`/usr/bin/ffmpeg` no contêiner do Render, com `libx264`, `aac`, `scale`, `overlay` e `scale2ref`
(research D2). Pillow, que já está no `requirements.txt`, valida a transparência da moldura.

**Armazenamento**: PostgreSQL — produção no Render (`manto-postgres`, `render.yaml`); verificação
contra a cópia `manto_local`. Vídeos no disco persistente do `manto-backend`, em
`instance/nfc_media/`, que ganha três subpastas: `entrada/` (o arquivo cru, efêmero),
`mestres/` (a versão 1080p sem moldura) e `sistema/` (moldura e vídeo de abertura). Os arquivos
entregues continuam na raiz da pasta, com os mesmos nomes de hoje.

**Verificação**: `specs/297-nfc-moldura-e-menu/verify_297.py` contra `manto_local` (login só pela
API; escrita por conexão separada); `cd frontend && npm run typecheck` (três SPAs); telas abertas no
Browser pane; `/nfc/<code>` em viewport mobile 375x812.

**Plataforma-alvo**: web — Render (Flask API JSON + 3 SPAs servidas por `frontend/server.js`);
staff em desktop, a página da tag em smartphone, à noite, muitas vezes em 4G.

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: vídeo entregue com cerca de 15 MB por 30 s; o envio responde em até 5 s
(a conversão não bloqueia a requisição); a conversão de um vídeo de 40 s termina em poucos minutos
mesmo dividindo a CPU com o ERP.

**Restrições**:
- `/nfc/<code>` é URL gravada em tag física: **imutável**. Nada de rota nova nesse prefixo.
- A resolução pública precisa continuar indistinguível entre código inexistente, tag desativada e
  tag sem vídeo (SC-006, herdado da 255).
- Uma CPU e 2 GB de RAM no contêiner, compartilhados com o ERP (research D5).
- Arquivo temporário nunca em `/tmp`, que é RAM no Render e já matou o serviço uma vez.
- Rota pública nova fora de `/api` exigiria entrada em `BACKEND_PREFIXES` — por isso tudo aqui fica
  sob `/api`, que já é proxiado.
- Superfície pública mobile-first: 320 a 430px sem rolagem horizontal, toque ≥ 44px,
  `useReducedMotion` em toda animação.

**Escala/escopo**: 1 tabela nova, 11 colunas novas em `nfc_tag_deliveries`, 2 colunas novas em
`site_settings`, 1 migration aditiva, 7 endpoints (3 alterados, 4 novos) mais 2 auxiliares de
recado, 1 thread de fundo, 2 módulos de núcleo novos, 4 componentes React alterados e 2 novos,
1 página pública reescrita, 1 comando de CLI para o reprocessamento dos dez existentes.

## Constitution Check

*GATE: aprovado antes da Phase 0; reavaliado após a Phase 1.*

| Princípio / seção | Como o plano cumpre (ou por que não se aplica) |
|---|---|
| I. Reutilizar antes de criar | Molde de thread de `_start_virtual_sweep` (`app/__init__.py:318-364`); claim por `UPDATE` condicional de `app/calendar/sync.py:122`; sino via `notificacoes_ops.emitir` (`:97-107`); caminho de arquivo em `SiteSetting` como `logo_path` (`app/admin/config_ops.py:78-88`); upload com progresso de `apps/internal/src/lib/revisao.ts:53-89` e `UploadProgressBar`; polling de `adminConfig.ts:170-176`; cenas com `AnimatePresence mode="wait"` de `ProductGallery.tsx:112-154`; `fieldErrorsFrom` de `apps/public/src/lib/virtuais.ts:239-244`; `localStorage` no padrão de `wishlist.ts:33-47`. Detalhe em research D8 |
| II. Padrões de código | Type hints e docstrings Google em todo `video_ops.py`; funções ≤ 30 linhas (a conversão se divide em `montar_filtro`, `montar_comando`, `converter`); constantes em `app/constants.py`; `except Exception as exc:  # noqa: BLE001` com `logger.warning` na thread; `ruff check` nos tocados; TS estrito, sem `any` |
| III. Camadas / API First | `video_ops.py` e `nfc_recados_ops.py` são núcleo puro, sem `flask.request`; `nfc_read.py`/`nfc_write.py` só validam RBAC e serializam; nenhum módulo novo em `app/api/` (as rotas entram nos dois arquivos que já existem, então não há import a acrescentar em `app/api/__init__.py`); tudo sob `/api`, nada a mexer em `BACKEND_PREFIXES` |
| IV. Não quebrar o que funciona | A migration é aditiva e as 10 entregas existentes nascem `pronto`, com o arquivo atual como entregue **e** como mestre até serem reprocessadas; o endpoint público mantém o shape de hoje e só ganha campos; o espelho admin da 265 não muda de contrato; o reprocessamento só apaga o arquivo velho depois que o novo existe e foi sondado |
| V. UI/UX com feedback | Botão de envio com progresso real (hoje são minutos de botão mudo); card com estado "preparando" que se atualiza sozinho; erro de conversão visível com botão de tentar de novo; recado com estado de envio, agradecimento e erro por campo; toasts e textos em pt-BR |
| VI. Esteira (Nível 1) | Esteira completa; artefatos mínimos em `specs/297-nfc-moldura-e-menu/` |
| VII. Living Spec | A spec foi atualizada **antes** deste plano: a decisão D4 trocou "arquivo original" por "mestre sem moldura" em FR-002, FR-007, SC-007 e na história 1 |
| VIII. Verify antes do núcleo | `verify_297.py` é a tarefa T005, na fase Foundational, falhando primeiro por falta das colunas e do endpoint |
| IX. Dinheiro BRL | Não se aplica: a feature não toca valor monetário |
| X. Mobile-first público | A página da tag é o caso mais mobile do sistema. Cenas em coluna `max-w-md`, botões `min-h-[48px]`, vídeo em `aspect-[9/16]`, conferência obrigatória em 375x812 |
| XI. Framer Motion | Cenas com `AnimatePresence mode="wait"`, 150–350 ms, usando o helper `enter(delay)` que já existe em `NfcPage.tsx:60-67` e devolve `{}` sob `useReducedMotion` |
| XII. Combobox / Maps | Não se aplica: nenhuma lista longa nem endereço |
| XIII. RBAC declarado | Sete linhas na tabela de `docs/01` §4.3. Os quatro endpoints do ERP usam `require_3d_access()`; os três públicos são deliberadamente sem login, com limite de taxa no que escreve |
| XIV. Config / efeito externo | `MANTO_SPOTIFY_URL` é constante de código, como já é o Instagram (Princípio XIV proíbe endereço público em variável de ambiente); nenhuma env nova; o caminho da moldura e da abertura é dado do banco, não configuração de ambiente |
| Stack | Migration à mão, `down_revision = "b7d2e4f1a9c3"` (head conferido); nenhum Jinja novo; nenhum segredo |
| Operação e Deploy | Não toca `startCommand`. A migration é aditiva, sem ensaio destrutivo. O `ffmpeg` não declarado no `render.yaml` vira dívida em `docs/05`, com degradação segura no código. A conversão respeita a CPU única com `nice` e um vídeo por vez |

**Resultado do gate**: aprovado, sem violação a justificar. Reavaliado após a Phase 1: sem mudança.

## Estrutura do projeto

### Documentação (esta feature)

```text
specs/297-nfc-moldura-e-menu/
├── spec.md              # /speckit-specify + /speckit-clarify
├── plan.md              # este arquivo
├── research.md          # Phase 0 — D1 a D8, com as medições
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1 — os 7 endpoints
├── checklists/          # /speckit-checklist
├── tasks.md             # /speckit-tasks
└── verify_297.py        # Princípio VIII — escrito antes do núcleo
```

### Código (caminhos reais)

```text
app/models.py                                  # NfcTagDelivery ganha 9 colunas; NfcTagMessage novo;
                                               #   SiteSetting ganha 3 colunas
migrations/versions/<rev>_nfc_moldura_e_recados.py   # aditiva, à mão
app/impressoes3d/video_ops.py                  # NOVO — núcleo puro: sondar, converter, moldura
app/impressoes3d/nfc_ops.py                    # add_delivery aceita `com_moldura`; fila e processamento
app/impressoes3d/nfc_recados_ops.py            # NOVO — registrar, listar e marcar lido
app/api/nfc_write.py                           # upload com moldura, reprocessar, moldura, abertura, recado
app/api/nfc_read.py                            # payload do resolve, vídeo de abertura, lista de recados
app/notificacoes/notificacoes_ops.py           # KIND novo + destinatários + produtor do recado
app/__init__.py                                # _start_nfc_video_worker + errorhandler(429)
app/constants.py                               # Spotify, largura máxima, extensões da moldura
frontend/apps/internal/src/components/nfc/     # VideoDialog, NfcVideoCard, NfcVideosPanel, + MolduraDialog, RecadosDaTag
frontend/apps/internal/src/lib/nfc.ts          # tipos novos, upload com progresso, polling
frontend/apps/public/src/pages/NfcPage.tsx     # máquina de cenas
frontend/apps/public/src/lib/nfc.ts            # tipos do payload novo, envio do recado, memória do aparelho
frontend/server.js                             # MEDIA_PATTERNS cobre o upload da tag (research D6)
```

**Decisão de estrutura**: a conversão mora num módulo próprio (`video_ops.py`) e não dentro de
`nfc_ops.py` porque ela não sabe o que é uma tag — recebe caminhos e devolve informação de vídeo.
Isso a torna testável sozinha e reaproveitável pelo vídeo da Loja Virtual (feature 205), que tem o
mesmo problema de peso e não entra nesta feature. Os recados ganham `nfc_recados_ops.py` em vez de
crescer `nfc_ops.py`, que já tem 500 linhas e trata de outro assunto.

## Sequência de implementação

Cinco blocos, na ordem em que devem ser feitos e commitados. Cada um deixa o sistema íntegro.

1. **Fundação** — migration, colunas, modelos, `verify_297.py` falhando pelos motivos certos.
2. **Conversão** (História 1) — `video_ops.py`, fila, thread de fundo, upload assíncrono, comando de
   reprocessamento dos dez existentes. Aqui a queixa já morre.
3. **Moldura** (História 2) — cadastro do PNG, caixinha no diálogo, aplicação na conversão.
4. **Página pública** (Histórias 3 e 4) — cenas, menu, vídeo de abertura, recado, endpoints públicos.
5. **Gerenciador** (História 5) — retrato, estado, recados na tag, sino.

O bloco 2 é o que se publica primeiro se o dono quiser aliviar a dor antes do resto.

## Riscos e como cada um é contido

| Risco | Contenção |
|---|---|
| A conversão come a CPU e o ERP fica lento | `nice -n 19`, `-threads 1`, um vídeo por vez, e a fila só acorda a cada 20 s |
| Três workers processam o mesmo vídeo | Claim atômico por `UPDATE ... WHERE processing_status = 'pendente'` com `rowcount == 1`, extensão do padrão de `app/calendar/sync.py:122` |
| Deploy no meio de uma conversão | O container morre e o arquivo temporário fica órfão; ao subir, a entrega volta para `pendente` se estava `processando` há mais de 30 min, e o temporário é apagado |
| O `ffmpeg` sumir da imagem base do Render | `ffmpeg_disponivel()` no início: sem ele a entrega fica `pronto` com o arquivo como veio, `processing_error` preenchido e aviso na tela. Nunca perde o vídeo |
| Upload de 250 MB cortado pelo proxy aos 180 s | `MEDIA_PATTERNS` do `frontend/server.js` passa a cobrir a rota de upload (research D6) |
| Moldura PNG sem transparência cobre o vídeo inteiro | `imaging.tem_transparencia_real` recusa o cadastro com mensagem clara |
| Moldura em proporção diferente de 9:16 estica | O cadastro avisa quando a proporção foge de 9:16, mas aceita — a decisão é do dono |
| O reprocessamento dos dez roda em produção e derruba algo | Comando de CLI manual, um por vez, com `--dry-run` primeiro, rodado pelo dono no Shell do Render fora do horário |

## Rastreamento de complexidade

> Preencher SÓ se o Constitution Check tiver violação a justificar.

Sem violações. Duas decisões que ampliam levemente o escopo, ambas justificadas:

| Decisão | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| `@app.errorhandler(429)` devolvendo o envelope JSON | FR-013 exige mensagem legível ao limitar o recado, e hoje o `flask-limiter` devolve HTML cru, que o front traduz como "Ocorreu um erro inesperado" | Construir o 429 à mão só na rota do recado repetiria em cada rota futura o que um handler resolve uma vez; e as treze rotas públicas com limite hoje já sofrem do mesmo defeito |
| `MEDIA_PATTERNS` no `frontend/server.js` | O upload que esta feature torna rotineiro (arquivo grande, porque o servidor agora comprime) é exatamente o que o prazo de 180 s corta | Deixar para depois significaria enviar vídeo de 150 MB por uma rota que pode desistir no meio, e o defeito só apareceria em conexão lenta, na casa da equipe |

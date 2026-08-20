# Research — Feature 255: Tags NFC

Decisões técnicas da Phase 0. Nenhum NEEDS CLARIFICATION restou na spec; este arquivo registra as escolhas de implementação e por quê.

## 1. Formato e geração do código

- **Decision**: `code = <prefixo>-<sufixo>` com sufixo de 6 caracteres sorteados de `23456789ABCDEFGHJKMNPQRSTUVWXYZ` (alfabeto sem `0/O`, `1/I/L`), gerado com `secrets.choice`. Armazenado em MAIÚSCULAS; lookup público normaliza para maiúsculas (tag gravada é imutável, mas alguém pode digitar o código à mão a partir da etiqueta).
- **Rationale**: 31⁶ ≈ 887 milhões de combinações por prefixo — inviável de adivinhar no volume da Manto (dezenas/mês), atendendo SC-006. Alfabeto sem ambiguidade evita erro humano ao conferir a etiqueta. `secrets` (CSPRNG) porque o sufixo é, na prática, um token de acesso a conteúdo futuramente pessoal.
- **Alternatives considered**: sufixo sequencial (rejeitado — adivinhável, viola privacidade da spec); UUID/token longo (rejeitado — URL feia e desnecessária para o risco); hashids (rejeitado — dependência nova para nada).
- **Colisão**: retry em loop (até 20 tentativas) checando unicidade; com 887M de espaço, colisão real é ruído estatístico.

## 2. Número sequencial humano (pedido do usuário durante o plan)

- **Decision**: coluna `sequence` inteira, numerada **por item do acervo** (1, 2, 3… por linha de produto), imutável, com constraint única `(item_id, sequence)`. Atribuída na criação: `max(sequence do item) + 1`, dentro da mesma transação da criação.
- **Rationale**: a equipe corta e grava várias tagsinhas de uma vez e precisa anotar fisicamente "nº 1, nº 2…" para depois alocar "nº X → cliente Y" no ERP. O código aleatório é péssimo rótulo humano; o número é o elo entre o mundo físico e o sistema. Por item (não global) porque é assim que a operação pensa: "luminária v1, tag 14".
- **Alternatives considered**: numeração global (rejeitada — mistura linhas de produto); usar o próprio sufixo como rótulo (rejeitado — ilegível/inanotável); sem número, confiando na ordem da lista (rejeitado — ordem muda com filtros).
- **Concorrência**: volume minúsculo e criação centralizada; `max+1` na transação + constraint única como rede de segurança (conflito improvável → erro claro, nunca duplicata silenciosa).

## 3. Sincronização automática com presentes 3D

- **Decision**: função `sync_event_gift_tags` chamada por `add_event_gift` e `update_event_gift` (em `app/impressoes3d/impressoes3d_ops.py`), antes do commit, na mesma transação. Regra: alvo = soma das `quantity` dos presentes do item NFC naquele evento; existentes = tags `(event_id, item_id)`; cria só a diferença positiva. Nunca apaga (redução de quantidade e remoção do presente não tocam nas tags — FR-003/US2).
- **Rationale**: contar por `(evento, item)` — e não por linha de presente — sobrevive a presentes deletados/recriados e a dois presentes do mesmo item no mesmo evento, sem duplicar tags.
- **Alternatives considered**: FK `gift_id` na tag (rejeitado — presente é deletável e a tag é eterna; o vínculo estável é o evento); SQLAlchemy event listeners (rejeitado — mágica implícita; chamada explícita nos dois pontos de escrita é auditável e segue o padrão do módulo).

## 4. Resolução pública e privacidade

- **Decision**: `GET /api/nfc/<code>` sem login, sempre **200** com o mesmo shape: código válido+ativo → `{product: {name, photo_url}, campaign: null, instagram_url}`; inválido/desativado → `{product: null, campaign: null, instagram_url}`. Contadores (`access_count`, `last_accessed_at`) atualizados só em tag válida/ativa, com commit isolado e tolerante a falha (métrica nunca derruba a página).
- **Rationale**: FR-007/SC-006 — resposta de código errado indistinguível de tag desativada; nunca 404 (o front nem precisa de caminho de erro). `instagram_url` vem do servidor (constante `MANTO_INSTAGRAM_URL` em `app/constants.py`): todo conteúdo da página é decidido server-side — coerente com a filosofia da URL eterna. Handle real confirmado com o usuário antes do deploy.
- **Alternatives considered**: 404 para código inválido (rejeitado — vaza existência e cria caminho de erro no front); Instagram hardcoded no bundle (rejeitado — conteúdo é do servidor).

## 5. Serving da página pública na raiz do domínio

- **Decision**: replicar o mecanismo `CADASTRO_PREFIX` em `frontend/server.js`: requisições `/nfc/*` servem `apps/public/dist` **sem reescrever** `req.url`; o `App.tsx` da vitrine trata `/nfc` como superfície de raiz (mesma lógica de `isCadastroSurface`, generalizada), rodando o Router sem o basename `/catalogo` e sem o `WishlistFloat`.
- **Rationale**: é o padrão já provado em produção para URL curta na raiz servida pelo bundle da vitrine; assets continuam em `/catalogo/assets/*` (base do Vite), que segue alcançável.
- **Alternatives considered**: redirect 302 para `/catalogo/nfc/...` (rejeitado — barra de endereço feia, e o padrão /f existe por legado de links impressos, não por preferência); página Jinja no Flask (proibido pela constituição); app Vite novo (rejeitado — overhead de build/rota para uma página).
- **Dev**: em dev o app público roda na raiz (`npm run dev:public`), então `/nfc/:code` funciona direto; proxies `/api` e `/uploads` já existem em `apps/public/vite.config.ts` (foto do acervo vem de `/uploads/acervo_3d_photos/*` via `assetUrl()`).

## 6. Animação de portal

- **Decision**: Framer Motion na própria página (`NfcPage.tsx`): véu/portal circular que se expande (clip-path/scale) revelando o conteúdo, 300–350ms de fases encadeadas; com `useReducedMotion()`, conteúdo aparece com fade discreto (ou direto). Sem biblioteca nova.
- **Rationale**: Princípio XI; framer-motion já é dependência do monorepo frontend.
- **Alternatives considered**: Lottie/vídeo (rejeitado — peso no 4G da cliente, SC-001); CSS puro (ok, mas o padrão do projeto é Framer Motion).

## 7. RBAC e reuso no admin

- **Decision**: endpoints admin reusam `require_3d_access`/`has_3d_access` de `app/api/impressoes3d_read.py` (gate `ARTISTA_3D`/`SUPERADMIN`); "cliente do evento" na lista reusa `client_of_event` de `app/api/agenda_read.py`; combobox de evento reusa o componente pesquisável existente do ERP.
- **Rationale**: Princípio I — os três já são fonte única dos respectivos comportamentos.

## 8. Métricas de acesso

- **Decision**: `access_count` + `last_accessed_at` na própria `nfc_tags` (FR-012), sem tabela de eventos de acesso e sem tela.
- **Rationale**: insumo barato para o futuro ("quantas clientes encostaram?"); tabela de log seria overengineering para dezenas de tags.
- **Alternatives considered**: tabela `nfc_accesses` (adiada — se campanhas futuras exigirem analytics por acesso, nasce lá).

## 9. Prévia Open Graph do link /nfc

- **Decision**: fora do escopo v1 — link é aberto por toque NFC, não compartilhado em chat; o `index.html` genérico da vitrine responde.
- **Rationale**: o mecanismo OG do server.js existe para links compartilhados no WhatsApp (catálogo); aqui não há esse fluxo. Se surgir, o `catalogOgTarget` ganha um caso novo.

# Constituição da Plataforma Manto

> Este documento define os princípios inegociáveis do projeto. Toda especificação
> (`/speckit-specify`), todo plano (`/speckit-plan`) e toda implementação
> (`/speckit-implement`) DEVEM respeitá-lo. Em caso de conflito, esta constituição
> prevalece sobre conveniência ou pressa.

## Princípios Fundamentais

### I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)
Antes de escrever qualquer código novo, é OBRIGATÓRIO verificar se já existe algo
parecido no projeto. Lógica duplicada é a principal causa de bugs e de "saída do
padrão" neste sistema.
- Procure funções, rotas, templates e padrões equivalentes antes de implementar.
- Se existir algo parecido mas imperfeito, estenda ou refatore — não crie uma
  segunda versão paralela.
- Um mesmo comportamento (ex.: botão de WhatsApp, cálculo de cachê, parsing de
  evento) deve ter UMA fonte de verdade no código.

### II. Padrões de código Python obrigatórios
Todo código Python segue o mesmo padrão, sem exceções:
- **Type hints** em todas as funções e métodos.
- **Docstrings** (Google style) em classes e funções públicas.
- **Nomes descritivos** — sem abreviações obscuras (`user_count`, não `uc`).
- **Funções pequenas**: máximo ~30 linhas. Se passar, extraia funções.
- **Aninhamento máximo de 3 níveis** de indentação.
- **Constantes em UPPER_CASE** no topo do módulo ou em `config.py` — zero strings
  mágicas espalhadas.
- **Nunca** usar `except Exception` sem logar o erro.

### III. Arquitetura em camadas
A responsabilidade de cada camada é respeitada:
- **Rotas/views não fazem regra de negócio** — apenas orquestram e chamam serviços.
- Regra de negócio fica em funções/serviços testáveis, sem dependência de HTTP.
- Acesso ao banco é isolado; o resto do código não espalha queries soltas.
- Configuração é centralizada (`config.py` / variáveis de ambiente), nunca hardcoded.
- Dependência só aponta para baixo: View → Serviço → Repositório → Modelo.

### IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)
Estabilidade vale mais que velocidade.
- Rode os testes relevantes ANTES de cada commit.
- Mudanças em pequenos passos verificáveis; cada funcionalidade = um commit atômico.
- Ao alterar um trecho compartilhado (ex.: sync de eventos, `models.py`), verifique
  todos os pontos que dependem dele antes de declarar "pronto".
- Se uma mudança toca a interface, confirme no app real que continua funcionando —
  não confie só na leitura do código.

### V. UI/UX consistente e com feedback (em português)
Toda interface segue o padrão visual do sistema, fala com o usuário em pt-BR e
**nunca deixa o usuário sem resposta**.
- Cores SEMPRE via variáveis CSS — zero cores hardcoded no HTML.
- Todo estado assíncrono tem feedback visual: **loading, erro e sucesso**.
- **Nenhum botão fica "morto" ao ser clicado (NÃO-NEGOCIÁVEL)**: todo botão que
  dispara uma ação (salvar, criar, enviar, sincronizar, aprovar, excluir — rápida
  ou lenta) DEVE mudar de aparência de forma visível ao ser clicado, até a
  resposta chegar — não basta desabilitar via atributo `disabled` sem nenhuma
  mudança visual perceptível (opacidade, cursor, texto). "Cliquei e não vi nada
  acontecer" é sempre um bug de UI, mesmo que o clique tenha sido processado nos
  bastidores. Um clique a mais nunca pode criar registro duplicado. Cobertura
  automática: formulários HTML comuns (`<form>`) herdam esse comportamento do
  guard global (`base.html` / `_form_scripts.html` dos formulários públicos) sem
  precisar de código por tela; ações disparadas por JavaScript puro (fetch fora
  de um `<form>`, botões com `onclick`) DEVEM implementar o próprio feedback
  visual manualmente, pois o guard global não as cobre.
- **Nunca limpar o que o usuário preencheu**: um erro de validação JAMAIS apaga os
  dados já digitados. O formulário preserva os valores e aponta o(s) campo(s) com
  problema.
- **Falha de validação sempre tem feedback visível no campo**: ao bloquear um envio,
  destaque/realce (ex.: borda vermelha + leve "shake") o(s) campo(s) faltante(s) e
  leve o foco até ele. Bloquear em silêncio é proibido.
- Ações destrutivas (deletar, remover) exigem confirmação.
- Mensagens de erro são amigáveis — nunca expor stack trace ao usuário final.
- Espaçamentos em múltiplos de 4px; mesma paleta e mesmos componentes em telas novas.

### VI. Planejar antes de codar
Nenhuma mudança grande começa direto no código.
- Fluxo: ENTENDER → ESPECIFICAR → PLANEJAR → IMPLEMENTAR → TESTAR → REVISAR.
- Se um requisito não está claro, PERGUNTE antes de assumir.
- Para features, use o fluxo spec-kit: `/speckit-specify` → `/speckit-plan` →
  `/speckit-tasks` → `/speckit-implement`.

### VII. Valores monetários sempre no padrão brasileiro (NÃO-NEGOCIÁVEL)
Todo valor em dinheiro, em QUALQUER lugar do sistema, é formatado no padrão
brasileiro: ponto como separador de milhar e vírgula como separador decimal, com
duas casas decimais. Ex.: `R$ 4.000,00`, `R$ 1.234,56` — nunca `4000`, `4000.00`
ou `4,000.00` (padrão americano é proibido).
- **Na exibição**: nenhum valor monetário aparece "cru" (ex.: `4000`) nem no padrão
  americano. Sempre milhar com `.`, decimal com `,` e duas casas.
- **Na digitação**: todo campo de entrada de valor formata automaticamente enquanto
  o usuário digita, para o padrão brasileiro (milhar com `.`, decimal com `,`). O
  usuário não precisa digitar os separadores manualmente.
- **Fonte única (NÃO-NEGOCIÁVEL)**: a formatação para exibição e o parsing/máscara
  de digitação têm UMA implementação reutilizável (um filtro/format no backend e um
  helper de máscara no frontend) — proibido reinventar formatação por tela.
- **No backend o valor continua numérico**: a máscara é só de apresentação; o valor
  enviado/persistido é convertido de volta para número (`,` decimal → ponto) antes
  de salvar. Nunca persistir a string formatada.

### VIII. Superfícies públicas são mobile-first
O Portal do Artista, o `/cadastro` público e o espaço de revisão são usados majoritariamente
em smartphones. Toda tela nova ou tocada nessas superfícies DEVE:
- Funcionar sem rolagem horizontal de 320px a 430px de largura.
- Ter alvos de toque confortáveis (≥ 44px) nas ações principais.
- Não usar texto informativo abaixo de 12px.
- Considerar o teclado virtual (campo de digitação e ação de envio visíveis com ele aberto).
- Ser conferida em viewport mobile ANTES de declarar pronto.

### IX. Movimento com propósito (transições suaves em superfícies voltadas ao público)
Uma mudança de estado visual sem transição — trocar uma imagem, redimensionar um
elemento, abrir/fechar algo — vira um "tranco": o usuário só vê o antes e o depois, e
isso passa sensação de descuido. Movimento bem aplicado é sofisticação, não enfeite.
- Em superfícies pensadas para causar boa impressão em quem não é da equipe (catálogo
  público, Portal do Artista, páginas voltadas à cliente final), toda mudança de estado
  visual perceptível DEVE ter uma transição suave (CSS `transition`/`animation`, ou JS
  quando a propriedade não anima de forma nativa/confiável entre navegadores).
- **Respeita `prefers-reduced-motion` (NÃO-NEGOCIÁVEL)**: quem configura menos movimento
  no sistema operacional recebe a versão sem animação (ou bem reduzida) — nunca ignorar
  essa preferência de acessibilidade.
- Movimento tem propósito: comunica causa e efeito (o que mudou, e por causa de quê) —
  não é decoração adicionada por adicionar. Duração típica de 150–350ms com curva suave
  (`ease`/`cubic-bezier`) — perceptível sem atrasar a interação.
- Telas puramente administrativas/internas não precisam do mesmo capricho visual das
  públicas, mas nenhuma tela (interna ou pública) pode trocar de estado de forma abrupta
  a ponto de parecer quebrada.

## Stack e Restrições Técnicas

- **Backend**: Python + Flask + SQLAlchemy. Entrada: `python run.py`.
- **Banco**: PostgreSQL em produção (Railway); cópia local de produção `manto_local`
  (Postgres) para desenvolvimento/verificação — **nunca** confie no SQLite vazio de
  `instance/` para validar (não pega bugs Postgres-only). Scripts em `scripts/db/`.
- **Migrations SEMPRE escritas à mão**: o autogenerate (`flask db migrate`) está quebrado
  por drift pré-existente. Toda mudança em `app/models.py` gera migration manual
  (`down_revision` = head atual) com upgrade/downgrade completos e backfill quando preciso.
- **Frontend**: Jinja2 + HTML/CSS/JS vanilla. Sem framework JS.
- **Integrações**: Google Calendar (OAuth 2.0) e Google Sheets (service account).
- **RBAC**: papéis SUPERADMIN, CASTING, FIGURINO, COMERCIAL, FINANCEIRO, VENDAS,
  ENSAIO, RH. Toda rota nova respeita o controle de acesso por papel já existente.
- **Comunicação com o usuário e textos de interface**: português (pt-BR).
- **Segredos**: nunca commitar senhas, tokens ou chaves. Use variáveis de ambiente.

## Portões de Qualidade (antes de "pronto")

Uma tarefa só está concluída quando:
- [ ] **Verificação funcional automatizada da feature executada e passando** contra a cópia
  local de produção (`manto_local`): script com o test client do Flask cobrindo os fluxos
  da feature (sucesso, erro e permissões). Regra prática: requests do test client SEMPRE
  fora de `with app.app_context()` (contexto persistente vaza o usuário logado entre
  requests); blocos de contexto curtos só para preparar dados e conferir o banco.
- [ ] Sem lint nos arquivos tocados (`ruff check <arquivos>`).
- [ ] Arquivos **novos** formatados com `ruff format`; em arquivos legados, siga o estilo
  circundante (não reformatar o arquivo inteiro — evita diffs gigantes não relacionados).
- [ ] Funções/classes novas têm docstring e type hints. (mypy é recomendado; passa a ser
  obrigatório quando estiver instalado no ambiente do projeto.)
- [ ] Casos de erro tratados; nada de `except` silencioso — todo `except` amplo registra o
  erro em log (`logging`), mesmo quando a recuperação é seguir em frente.
- [ ] Nenhum segredo hardcoded.
- [ ] Migration manual criada se `models.py` mudou (e aplicada na cópia local).
- [ ] Comportamento conferido no app real quando há mudança de interface (viewport mobile
  incluído quando for superfície pública — Princípio VIII).
- [ ] Todo botão de ação nesta tela muda de aparência visível ao ser clicado (Princípio V) —
  herdado automaticamente se for um `<form>` comum; implementado manualmente se a ação for
  disparada por JavaScript puro (fetch fora de formulário, `onclick`).
- [ ] **Changelog do time atualizado** (`docs/changelog.html`): toda feature/mudança visível
  ao usuário ganha uma entrada nova, em português simples (o que mudou, não como) — sem
  remover entradas antigas. Republicar no mesmo link já existente (nunca criar um link novo).

## Governança

- Esta constituição prevalece sobre qualquer outra prática ou atalho.
- Toda complexidade adicional precisa ser justificada — na dúvida, escolha o caminho
  mais simples (YAGNI).
- Planos (`plan.md`) e tarefas (`tasks.md`) que violem um princípio devem ser
  corrigidos antes da implementação, não depois.
- Alterar esta constituição é uma decisão deliberada: registre o que mudou e o
  porquê, e suba a versão abaixo.
- Para orientação detalhada de runtime, o Claude também segue `CLAUDE.md` e os
  arquivos em `.claude/skills/`.

**Versão**: 1.6.0 | **Ratificada**: 2026-05-29 | **Última alteração**: 2026-07-20

> **Changelog**
> - **1.6.0** (2026-07-20): Novo Princípio IX — movimento com propósito. Motivado por
>   incidente real (feature 142: troca de foto/proporção na galeria do catálogo público
>   trocava de estado sem nenhuma transição, "dando um tranco" na página). Toda mudança de
>   estado visual perceptível em superfícies voltadas ao público exige transição suave,
>   respeitando `prefers-reduced-motion`.
> - **1.5.0** (2026-07-14): Novo item no portão de qualidade — toda feature ganha uma
>   entrada no changelog do time (`docs/changelog.html`, publicado como página web para
>   apresentar à equipe), em linguagem simples, sempre republicado no mesmo link. Registra
>   o que já foi entregue de forma contínua, sem depender de reconstruir o histórico do
>   zero a cada pedido.
> - **1.4.0** (2026-07-13): Princípio V reforçado — "prevenir envio duplicado" virou "nenhum
>   botão fica morto ao ser clicado" (NÃO-NEGOCIÁVEL): `disabled` sozinho, sem mudança visual
>   perceptível, não conta como feedback. Motivado por incidente real (gasto extra com nota
>   fiscal grande, upload lento em 4G, usuário sem nenhum sinal de "enviando" travou o celular
>   e abortou o envio — feature 124). Novo item no portão de qualidade cobrando essa checagem
>   por tela tocada.
> - **1.3.0** (2026-07-03): Portões de qualidade tornados EXECUTÁVEIS no ambiente real —
>   o portão `pytest tests/` (suíte inexistente) foi substituído pela verificação funcional
>   automatizada por feature contra `manto_local` (test client, requests fora de
>   `app_context`); `ruff format` restrito a arquivos novos (legado segue estilo circundante);
>   mypy rebaixado a recomendação até existir no ambiente. Novo Princípio VIII — superfícies
>   públicas mobile-first (portal, /cadastro, revisão). Stack atualizada: migrations sempre
>   manuais (autogenerate quebrado) e verificação contra a cópia local Postgres, nunca
>   SQLite. `except` amplo agora exige log explicitamente no portão.
> - **1.2.0** (2026-06-04): Novo Princípio VII — todo valor monetário no padrão
>   brasileiro (milhar com `.`, decimal com `,`, duas casas), tanto na exibição
>   quanto na digitação (máscara automática), com fonte única de formatação e valor
>   numérico preservado no backend.
> - **1.1.0** (2026-06-04): Princípio V reforçado com regras concretas de feedback —
>   prevenção de envio duplicado (botão desabilita + loading), proibição de limpar o
>   formulário em erro, e feedback visível no campo ao bloquear envio.

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
- Procure componentes React, hooks, rotas de API, utilitários e padrões equivalentes antes de implementar.
- Se existir algo parecido mas imperfeito, estenda ou refatore — não crie uma
  segunda versão paralela.
- Um mesmo comportamento (ex.: botão de WhatsApp, cálculo de cachê, parsing de
  evento, componente de Input monetário) deve ter UMA fonte de verdade no código.

### II. Padrões de código Python e TypeScript obrigatórios
Todo código do projeto segue padrões estritos de tipagem e clareza, sem exceções:
- **Backend (Python)**:
  - **Type hints** em todas as funções e métodos.
  - **Docstrings** (Google style) em classes e funções públicas.
  - **Nomes descritivos** — sem abreviações obscuras (`user_count`, não `uc`).
  - **Funções pequenas**: máximo ~30 linhas. Se passar, extraia funções.
  - **Aninhamento máximo de 3 níveis** de indentação.
  - **Constantes em UPPER_CASE** no topo do módulo ou em `config.py` — zero strings
    mágicas espalhadas.
  - **Nunca** usar `except Exception` sem logar o erro.
- **Frontend (TypeScript / React)**:
  - **TypeScript estrito**: proibidão o uso de `any` explícito ou implícito. Defina interfaces/types para todas as props, respostas de API e estados.
  - **Componentes modulares**: componentes funcionais React pequenos e com responsabilidade única.
  - **Estilização**: estritamente via **Tailwind CSS** e **shadcn/ui**. Proibido criar arquivos `.css` Vanilla soltos ou estilos inline (`style={{...}}`).

### III. Arquitetura Desacoplada e em Camadas (API First)
A separação entre Backend e Frontend é total e inegociável:
- **Backend é 100% API RESTful JSON**: rotas Flask/Python NUNCA retornam HTML (`render_template` é proibido). Todas as respostas são JSON padronizados (`jsonify`).
- **Rotas/views não fazem regra de negócio** — apenas orquestram e chamam serviços.
- Regra de negócio fica em funções/serviços testáveis em Python, sem dependência de HTTP.
- Acesso ao banco é isolado; o resto do código não espalha queries soltas.
- Configuração é centralizada (`config.py` / variáveis de ambiente), nunca hardcoded.
- Dependência no Backend só aponta para baixo: View/Endpoint → Serviço → Repositório → Modelo.

### IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)
Estabilidade vale mais que velocidade.
- Rode os testes e verificações de tipos (`tsc`) relevantes ANTES de cada commit.
- Mudanças em pequenos passos verificáveis; cada funcionalidade = um commit atômico.
- Ao alterar um trecho compartilhado (ex.: schemas de API, contratos JSON, `models.py`), verifique
  todos os pontos do Frontend e Backend que dependem dele antes de declarar "pronto".
- Se uma mudança toca a interface, confirme no app real que continua funcionando —
  não confie só na leitura do código.

### V. UI/UX moderna, consistente e com feedback (em português)
Toda interface segue o padrão visual moderno (Tailwind + shadcn/ui), fala com o usuário em pt-BR e
**nunca deixa o usuário sem resposta**.
- Design System unificado via Tailwind CSS e componentes `shadcn/ui` — zero cores ou estilos hardcoded fora do tema.
- Todo estado assíncrono (requisições de API) tem feedback visual obrigatório via TanStack Query / React: **Skeletons/Loading, erro e sucesso**.
- **Nenhum botão fica "morto" ao ser clicado (NÃO-NEGOCIÁVEL)**: todo botão que
  dispara uma ação (salvar, criar, enviar, sincronizar, aprovar, excluir — rápida
  ou lenta) DEVE mudar de aparência de forma visível ao ser clicado (ex.: spinner interno do `shadcn/ui`, opacidade reduzida, texto "Salvando...", estado `disabled`), até a
  resposta da API chegar. "Cliquei e não vi nada acontecer" é sempre um bug de UI. Um clique a mais nunca pode criar registro duplicado.
- **Nunca limpar o que o usuário preencheu**: um erro de validação da API JAMAIS apaga os
  dados já digitados no formulário React. O formulário preserva os estados e aponta o(s) campo(s) com
  problema.
- **Falha de validação sempre tem feedback visível no campo**: ao bloquear um envio,
  destaque/realce (ex.: borda vermelha + mensagem do `react-hook-form` / `zod`) o(s) campo(s) faltante(s) e
  leve o foco até ele. Bloquear em silêncio é proibido.
- Ações destrutivas (deletar, remover) exigem confirmação via modal/dialog do `shadcn/ui`.
- Mensagens de erro são amigáveis e exibidas via Toasts/Alerts em pt-BR — nunca expor stack trace ou erros brutos do banco ao usuário final.
- Espaçamentos em múltiplos do Tailwind (4px); mesma paleta e mesmos componentes em telas novas.

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
- **Na digitação**: todo campo de entrada de valor usa um componente React de Input Monetário dedicado que formata automaticamente enquanto
  o usuário digita, para o padrão brasileiro (milhar com `.`, decimal com `,`). O
  usuário não precisa digitar os separadores manualmente.
- **Fonte única (NÃO-NEGOCIÁVEL)**: a formatação para exibição e o parsing/máscara
  de digitação têm UMA implementação reutilizável (um utilitário/hook no frontend e um
  helper no backend) — proibido reinventar formatação por tela.
- **No backend o valor continua numérico**: a máscara no React é só de apresentação; o valor
  enviado via JSON/persistido no Python é convertido de volta para número (float/decimal) antes
  de salvar. Nunca persistir a string formatada no banco.

### VIII. Superfícies públicas são mobile-first
O Portal do Artista, o `/cadastro` público e o espaço de revisão são usados majoritariamente
em smartphones. Toda tela nova ou tocada nessas superfícies DEVE:
- Funcionar sem rolagem horizontal de 320px a 430px de largura.
- Ter alvos de toque confortáveis (≥ 44px) nas ações principais.
- Não usar texto informativo abaixo de 12px.
- Considerar o teclado virtual (campo de digitação e ação de envio visíveis com ele aberto).
- Ser conferida em viewport mobile ANTES de declarar pronto.

### IX. Movimento fluido e com propósito (Framer Motion)
Uma mudança de estado visual sem transição — trocar de página, redimensionar um
elemento, abrir/fechar modais, filtrar listas — vira um "tranco". Movimento bem aplicado com Framer Motion é sofisticação e comunicação de estado.
- Toda mudança de página, abertura de modais/drawers, expansão de cards e atualizações de listas DEVEM utilizar transições suaves do **Framer Motion** ou animações utilitárias do Tailwind.
- **Respeita `prefers-reduced-motion` (NÃO-NEGOCIÁVEL)**: componentes animados via Framer Motion DEVEM respeitar as configurações do SO do usuário usando `useReducedMotion()` do Framer Motion ou utilitários CSS correspondentes.
- Movimento tem propósito: comunica causa e efeito (o que mudou, e por causa de quê). Duração típica de 150–350ms com curvas suaves (`easeOut` / `easeInOut`).

## Stack e Restrições Técnicas

- **Arquitetura**: SPA Desacoplada (Headless / API REST).
- **Backend**: Python + Flask + SQLAlchemy (servindo estritamente JSON). Entrada API: `python run.py`.
- **Frontend**: React (Vite) + TypeScript + Tailwind CSS + `shadcn/ui` + Framer Motion.
- **Gerenciamento de Estado de API**: TanStack Query (React Query) para busca, cache e mutações HTTP.
- **Banco**: PostgreSQL em produção (Railway); cópia local de produção `manto_local`
  (Postgres) para desenvolvimento/verificação — **nunca** confie no SQLite vazio de
  `instance/` para validar. Scripts em `scripts/db/`.
- **Migrations SEMPRE escritas à mão**: toda mudança em `app/models.py` gera migration manual
  (`down_revision` = head atual) com upgrade/downgrade completos.
- **Proibições de Stack**: Proibido Jinja2, HTML/CSS/JS Vanilla legados, jQuery, Bootstrap, `render_template` no Flask e manipulação direta de DOM (`querySelector`).
- **Integrações**: Google Calendar (OAuth 2.0) e Google Sheets (service account).
- **RBAC**: papéis SUPERADMIN, CASTING, FIGURINO, COMERCIAL, FINANCEIRO, VENDAS,
  ENSAIO, RH. Toda rota de API nova valida permissões JSON via decorators ou middlewares.
- **Comunicação com o usuário e textos de interface**: português (pt-BR).
- **Segredos**: nunca commitar senhas, tokens ou chaves. Use variáveis de ambiente (`.env`).

## Portões de Qualidade (antes de "pronto")

Uma tarefa só está concluída quando:
- [ ] **Frontend compila sem erros de TypeScript** (`npm run build` ou `npx tsc --noEmit` sem avisos ou erros).
- [ ] **Verificação funcional automatizada da API/Backend executada e passando** contra a cópia
  local de produção (`manto_local`): testes cobrindo os novos/alterados endpoints JSON (sucesso 200/201, erros 400/401/403/500).
- [ ] Sem lint nos arquivos Python e TS/TSX tocados (`ruff check <arquivos>` no backend e ESLint/Biome no frontend).
- [ ] Funções/classes novas têm docstring e type hints no Python; componentes e hooks novos têm interfaces/types explícitos no TypeScript.
- [ ] Casos de erro tratados no React (Error Boundaries, Toasts de erro) e no Flask (JSON de erro amigável, log amplo com `logging`).
- [ ] Migration manual criada se `models.py` mudou (e aplicada na cópia local).
- [ ] Comportamento de UI verificado no app real (transições fluidas via Framer Motion, feedback de loading nos botões e viewport mobile conferido).
- [ ] **Changelog do time atualizado** (`docs/changelog.html`): toda feature/mudança visível
  ao usuário ganha uma entrada nova, em português simples.

## Governança

- Esta constituição prevalece sobre qualquer outra prática ou atalho.
- Toda complexidade adicional precisa ser justificada — na dúvida, escolha o caminho
  mais simples (YAGNI).
- Planos (`plan.md`) e tarefas (`tasks.md`) que violem um princípio devem ser
  corrigidos antes da implementação, não depois.
- Alterar esta constituição é uma decisão deliberada: registre o que mudou e o
  porquê, e suba a versão abaixo.

**Versão**: 2.0.0 | **Ratificada**: 2026-07-20 | **Última alteração**: 2026-07-20

> **Changelog**
> - **2.0.0** (2026-07-20): **MIGRAÇÃO ARQUITETURAL MAJOR.** Transição do Frontend estático Jinja2/Vanilla para uma SPA desacoplada moderna em **React (Vite) + TypeScript + Tailwind CSS + shadcn/ui + Framer Motion**. O Backend Flask foi restrito estritamente a servir respostas API RESTful JSON (`render_template` e CSS/JS Vanilla removidos da constituição). Princípios de UI/UX, Typechecking estrito em TS e animações com Framer Motion integrados aos Princípios V, IX e aos Portões de Qualidade.
> - **1.6.0** (2026-07-20): Novo Princípio IX — movimento com propósito. Toda mudança de
>   estado visual perceptível em superfícies voltadas ao público exige transição suave.
> - **1.5.0** (2026-07-14): Novo item no portão de qualidade — registro contínuo no changelog do time (`docs/changelog.html`).
> - **1.4.0** (2026-07-13): Princípio V reforçado — "nenhum botão fica morto ao ser clicado" (NÃO-NEGOCIÁVEL).
> - **1.3.0** (2026-07-03): Portões de qualidade tornados EXECUTÁVEIS no ambiente real; Princípio VIII (Mobile-first).
> - **1.2.0** (2026-06-04): Princípio VII — todo valor monetário no padrão brasileiro.
> - **1.1.0** (2026-06-04): Princípio V reforçado com regras concretas de feedback.
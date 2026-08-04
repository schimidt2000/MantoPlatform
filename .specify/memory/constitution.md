### Constituição da Plataforma Manto
Este documento define os princípios inegociáveis do projeto. Por adotarmos o Spec-Driven Development, este arquivo atua como o DNA arquitetural do sistema e reside obrigatoriamente em `.specify/memory/constitution.md`. Toda especificação (`/speckit.specify`), todo plano (`/speckit.plan`) e toda implementação (`/speckit.implement`) DEVEM respeitá-lo. Em caso de conflito, esta constituição prevalece sobre conveniência ou pressa.

#### Princípios Fundamentais

##### I. Reutilizar antes de criar (NÃO-NEGOCIÁVEL)
Antes de escrever qualquer código novo, é OBRIGATÓRIO verificar se já existe algo parecido no projeto. Lógica duplicada é a principal causa de bugs e de "saída do padrão" neste sistema.
* Procure componentes React, hooks, rotas de API, utilitários e padrões equivalentes antes de implementar.
* Se existir algo parecido mas imperfeito, estenda ou refatore — não crie uma segunda versão paralela.
* Um mesmo comportamento (ex.: botão de WhatsApp, cálculo de cachê, parsing de evento, componente de Input monetário) deve ter UMA fonte de verdade no código.

##### II. Padrões de código Python e TypeScript obrigatórios
Todo código do projeto segue padrões estritos de tipagem e clareza, sem exceções:
* **Backend (Python)**:
  * **Type hints** em todas as funções e métodos.
  * **Docstrings** (Google style) em classes e funções públicas.
  * **Nomes descritivos** — sem abreviações obscuras (`user_count`, não `uc`).
  * **Funções pequenas**: máximo ~30 linhas. Se passar, extraia funções.
  * **Aninhamento máximo de 3 níveis** de indentação.
  * **Constantes em UPPER_CASE** no topo do módulo ou em `config.py` — zero strings mágicas espalhadas.
  * **Nunca** usar `except Exception` sem logar o erro.
* **Frontend (TypeScript / React)**:
  * **TypeScript estrito**: proibidão o uso de `any` explícito ou implícito. Defina interfaces/types para todas as props, respostas de API e estados.
  * **Componentes modulares**: componentes funcionais React pequenos e com responsabilidade única.
  * **Estilização**: estritamente via **Tailwind CSS** e **shadcn/ui**. Proibido criar arquivos `.css` Vanilla soltos ou estilos inline (`style={{...}}`).

##### III. Arquitetura Desacoplada e em Camadas (API First)
A separação entre Backend e Frontend é total e inegociável:
* **Backend é 100% API RESTful JSON**: rotas Flask/Python NUNCA retornam HTML (`render_template` é proibido). Todas as respostas são JSON padronizados (`jsonify`).
* **Rotas/views não fazem regra de negócio** — apenas orquestram e chamam serviços.
* Regra de negócio fica em funções/serviços testáveis em Python, sem dependência de HTTP.
* Acesso ao banco é isolado; o resto do código não espalha queries soltas.
* Configuração é centralizada (`config.py` / variáveis de ambiente), nunca hardcoded.
* Dependência no Backend só aponta para baixo: View/Endpoint → Serviço → Repositório → Modelo.

##### IV. Não quebrar o que funciona (NÃO-NEGOCIÁVEL)
Estabilidade vale mais que velocidade.
* Rode os testes e verificações de tipos (`tsc`) relevantes ANTES de cada commit.
* Mudanças em pequenos passos verificáveis; cada funcionalidade = um commit atômico.
* Ao alterar um trecho compartilhado (ex.: schemas de API, contratos JSON, `models.py`), verifique todos os pontos do Frontend e Backend que dependem dele antes de declarar "pronto".
* Se uma mudança toca a interface, confirme no app real que continua funcionando — não confie só na leitura do código.

##### V. UI/UX moderna, consistente e com feedback (em português)
Toda interface segue o padrão visual moderno (Tailwind + shadcn/ui), fala com o usuário em pt-BR e **nunca deixa o usuário sem resposta**.
* Design System unificado via Tailwind CSS e componentes shadcn/ui — zero cores ou estilos hardcoded fora do tema.
* Todo estado assíncrono (requisições de API) tem feedback visual obrigatório via TanStack Query / React: **Skeletons/Loading, erro e sucesso**.
* **Nenhum botão fica "morto" ao ser clicado (NÃO-NEGOCIÁVEL)**: todo botão que dispara uma ação (salvar, criar, enviar, sincronizar, aprovar, excluir — rápida ou lenta) DEVE mudar de aparência de forma visível ao ser clicado (ex.: spinner interno do shadcn/ui, opacidade reduzida, texto "Salvando...", estado `disabled`), até a resposta da API chegar. "Cliquei e não vi nada acontecer" é sempre um bug de UI. Um clique a mais nunca pode criar registro duplicado.
* **Nunca limpar o que o usuário preencheu**: um erro de validação da API JAMAIS apaga os dados já digitados no formulário React. O formulário preserva os estados e aponta o(s) campo(s) com problema.
* **Falha de validação sempre tem feedback visível no campo**: ao bloquear um envio, destaque/realce o(s) campo(s) faltante(s) e leve o foco até ele. Bloquear em silêncio é proibido.
* Ações destrutivas (deletar, remover) exigem confirmação via modal/dialog do shadcn/ui.
* Mensagens de erro são amigáveis e exibidas via Toasts/Alerts em pt-BR — nunca expor stack trace ou erros brutos do banco ao usuário final.

##### VI. Spec-Driven Development e o Caminho Completo (Full Path)
Nenhuma mudança grande começa direto no código. A Plataforma Manto é um sistema de produção complexo, e por isso deve usar a esteira completa do Spec Kit com seus "Portões de Qualidade" para blindar a arquitetura:
1. `/speckit.specify` — Definir o "o que" e o "porquê".
2. `/speckit.clarify` — Resolver ambiguidades *antes* do plano.
3. `/speckit.plan` — Definir arquitetura, stack e bancos de dados.
4. `/speckit.checklist` — Test-driven requirements (garantir que a spec responde a tudo).
5. `/speckit.tasks` — Quebrar em tarefas de implementação.
6. `/speckit.analyze` — Verificar conflitos e furos entre spec, plan e tasks *antes* de codar.
7. `/speckit.implement` — Codar (escopado em partes menores se a feature for gigante).
8. `/speckit.converge` — Analisar a conclusão da implementação e iterar os gaps pendentes.

##### VII. Living Spec (Persistência da Especificação)
O modelo adotado para a manutenção do ciclo de vida das features é o **Living Spec**. 
* Quando o comportamento desejado do sistema mudar, a alteração deve ser feita **PRIMEIRO** no arquivo `spec.md`.
* Após a atualização da spec, os artefatos de planejamento (`plan.md`, `tasks.md`) e o código final devem ser regenerados ou revisados a partir dela para manter a harmonia do sistema. A especificação não é descartável, ela é o contrato atualizado do produto.

##### VIII. Test-First Imperative
Os testes ou scripts de verificação funcional automatizada (como os scripts `verify_*.py` validados contra o `manto_local`) devem ser pensados e documentados **antes** da implementação do código. Na criação de `tasks.md`, as tarefas focadas em scripts de verificação funcional e testes de contrato devem ser ordenadas para serem escritas antes das tarefas de construção do núcleo de negócio. 

##### IX. Valores monetários sempre no padrão brasileiro (NÃO-NEGOCIÁVEL)
Todo valor em dinheiro, em QUALQUER lugar do sistema, é formatado no padrão brasileiro (ex.: R$ 4.000,00, R$ 1.234,56). Padrão americano é proibido.
* **Na exibição**: nenhum valor monetário aparece "cru". Sempre milhar com `.`, decimal com `,` e duas casas.
* **Na digitação**: todo campo de entrada de valor usa um componente React de Input Monetário dedicado que formata automaticamente enquanto o usuário digita.
* **Fonte única (NÃO-NEGOCIÁVEL)**: a formatação para exibição e a máscara de digitação usam a biblioteca `@manto/money` — proibido reinventar formatação por tela.
* **No backend o valor continua numérico**: a máscara é só de apresentação; o JSON e o Python operam e persistem como `Numeric/Decimal`.

##### X. Superfícies públicas são mobile-first
O Portal do Artista, o `/cadastro` público e o espaço de revisão são usados majoritariamente em smartphones. Toda tela nestas superfícies DEVE:
* Funcionar sem rolagem horizontal de 320px a 430px de largura.
* Ter alvos de toque confortáveis (≥ 44px) nas ações principais.
* Não usar texto informativo abaixo de 12px.
* Ser conferida em viewport mobile ANTES de declarar pronto.

##### XI. Movimento fluido e com propósito (Framer Motion)
Uma mudança de estado visual sem transição vira um "tranco".
* Toda mudança de página, abertura de modais/drawers, expansão de cards e atualizações de listas DEVEM utilizar transições suaves do **Framer Motion** (150–350ms).
* **Respeita `prefers-reduced-motion` (NÃO-NEGOCIÁVEL)**: todo uso do Framer Motion DEVE respeitar `useReducedMotion()`.
* O movimento comunica causa e efeito.

##### XII. Tratamento de dados complexos, comboboxes e autocomplete (NÃO-NEGOCIÁVEL)
1. **Fim dos dropdowns estáticos grandes**: campo de seleção com **mais de 10 itens** NUNCA é um `<select>` nativo. Usa obrigatoriamente o `Combobox` pesquisável de `@manto/ui`.
2. **Visualizadores inline (avatares e miniaturas)**: buscas de Talento ou Personagem/Figurino devem exibir miniatura (**circular** para pessoas, **quadrada** para figurinos/personagens). Sem foto, usar placeholder (`AvatarThumb`).
3. **Autocomplete de endereço mandatório**: todo input de endereço usa o `GoogleAddressInput`.
4. **A chave do Google nunca vai para o navegador**: passa via endpoint do Flask (lendo `SiteSetting.google_maps_api_key`).
5. **Economia de quota é regra**: busca preditiva é sempre debounced (hoje 350ms, min. 3 caracteres).

#### Stack e Restrições Técnicas
* **Arquitetura**: SPA Desacoplada (Headless / API REST).
* **Backend**: Python + Flask + SQLAlchemy (servindo estritamente JSON).
* **Frontend**: React (Vite) + TypeScript + Tailwind CSS + shadcn/ui + Framer Motion.
* **Gerenciamento de Estado**: TanStack Query (React Query).
* **Banco**: PostgreSQL em produção (Railway); cópia local de produção `manto_local` (Postgres) para desenvolvimento/verificação — **nunca** confie no SQLite vazio de `instance/` para validar. Use `scripts/db/run-local.ps1`.
* **Migrations SEMPRE escritas à mão**: toda mudança em `app/models.py` gera migration manual no Alembic (`down_revision` = head atual).
* **Proibições de Stack**: Jinja2, HTML/CSS/JS Vanilla legados, jQuery, Bootstrap, `render_template` no Flask e manipulação direta de DOM (`querySelector`).
* **Segredos**: Nunca commitar senhas, tokens ou chaves (`.env`).

#### Portões de Qualidade (antes de "pronto")
Uma tarefa só está concluída quando:
* [ ] **Frontend compila sem erros** (`npx tsc --noEmit` limpo).
* [ ] **Verificação funcional automatizada da API** executada contra a cópia de produção (`manto_local`), nunca SQLite.
* [ ] `/speckit.converge` executado no final do ciclo para garantir que todos os artefatos se alinharam (sem gaps pendentes).
* [ ] Sem lint nos arquivos Python (`ruff check`) e TypeScript.
* [ ] Migration manual criada se `models.py` mudou.
* [ ] **Changelog do time atualizado** (`docs/changelog.html` está **congelado** — registre as mutações incrementais apenas no topo de `docs/03_HISTORICO_MUTACOES.md`).

#### Governança
* Esta constituição prevalece sobre qualquer outra prática ou atalho.
* Toda complexidade adicional precisa ser justificada em planejamento.
* Planos (`plan.md`) e tarefas (`tasks.md`) que violem um princípio devem ser corrigidos antes da implementação, não depois.

**Versão**: 2.2.0 | **Ratificada**: 2026-07-20 | **Última alteração**: 2026-07-30

**Changelog**
* **2.2.0** (2026-07-30): Adaptação para o fluxo oficial do Spec-Driven Development (Spec Kit v0.15+). Sintaxe dos comandos atualizada de hifens para pontos (`/speckit.specify`). Inclusão do Caminho Completo (Clarify, Checklist, Analyze, Converge). Adoção explícita dos princípios de Living Spec e Test-First Imperative, formalizados na esteira como Princípios VII e VIII. O arquivo foi movido permanentemente para `.specify/memory/constitution.md`.
* **2.1.0** (2026-07-28): Novo Princípio — dados complexos, comboboxes e autocomplete (`<select>` nativo proibido >10 itens).
* **2.0.0** (2026-07-20): MIGRAÇÃO ARQUITETURAL MAJOR. Transição do Frontend estático para SPA em React (Vite) + TS + Tailwind. Backend restrito a API JSON.
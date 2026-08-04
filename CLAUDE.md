### CLAUDE.md — Instruções para o Claude Code

Este arquivo é lido automaticamente pelo Claude Code ao abrir o projeto. Ele define como o Claude deve trabalhar neste projeto (backend Python/Flask + frontend React/TypeScript), utilizando Spec-Driven Development (SDD) e tirando proveito máximo das capacidades agenticas dos modelos da geração 5.

---

#### 🏗️ Sobre o Projeto
* **Nome**: Plataforma Manto
* **Descrição**: Sistema empresarial ERP para gestão de eventos, talentos, figurino, financeiro e agenda. Integrado com Google Calendar e Google Sheets.
* **Arquitetura**: SPA desacoplada — **Frontend React** (Vite + TypeScript + Tailwind CSS + shadcn/ui + Framer Motion + TanStack Query) consumindo o **Flask como API JSON estrita** (`/api/*`). Banco: SQLite (dev casual) → PostgreSQL (produção, Railway).
* **Padrões obrigatórios (fonte única)**: Valor monetário sempre via `@manto/money` (formatBRL/parseBRL); arquivos servidos pelo Flask sempre usam `assetUrl()` de `@manto/api-client`; núcleo de negócio sempre em módulos `*_ops.py` (nunca duplicar lógica).

---

#### 🤖 Autonomia e Configuração de Execução (Opus 5 / Sonnet 5)
Este projeto utiliza Spec-Driven Development (SDD) integrado nativamente com o Spec Kit (`/speckit.*`).

* **Adaptive Thinking e Esforço**: O *Adaptive Thinking* já está ligado por padrão na geração 5. A resolução de features via SDD (Plan, Tasks, Implement) exige alto nível de raciocínio. Utilize o parâmetro `effort` em `xhigh` ou `max`. Garanta que o `max_tokens` esteja configurado para suportar saídas longas (64k a 128k).
* **Concisão e Ação**: Vá direto ao ponto. Responda de forma concisa e evite preâmbulos longos ou resumos verbosos do que você acabou de fazer. Seu foco é gerar código e evoluir os artefatos de especificação.
* **Escopo Focado (Sem Over-verification)**: Limite-se estritamente à tarefa especificada no documento atual da esteira do SDD (`spec.md`, `plan.md` ou `tasks.md`). O modelo verifica seu próprio trabalho naturalmente de forma extremamente eficaz; **NÃO** execute rotinas extras de auto-verificação ou re-checagem, a menos que o artefato do SDD exija isso explicitamente.
* **Controle de Subagentes**: Execute a implementação do código diretamente usando as ferramentas disponíveis. Não delegue a resolução de problemas para subagentes a menos que o escopo da tarefa explicitamente exija paralelização extrema (evite a tendência do Opus 5 de criar subagentes desnecessários).
* **Comunicação e Fluxo**: Se a especificação do SDD estiver ambígua, pergunte antes de iniciar o plano. Faça pequenos commits atômicos e atualize os arquivos de `tasks.md` sem inventar passos que não estavam descritos na especificação.

---

#### 🐍 Qualidade de Código Python
* **Type hints** em todas as funções e métodos.
* **Docstrings** em classes e funções públicas (formato Google style).
* **Nomes descritivos**: sem abreviações obscuras.
* **Funções pequenas**: máximo ~30 linhas; evite aninhamento superior a 3 níveis de indentação.
* **Constantes em UPPER_CASE** no topo do módulo ou em `config.py`.
* **Nunca** use `except Exception` sem logar o erro.

---

#### 🎨 UI/UX — React (Tailwind + shadcn/ui + Framer Motion)
Toda interface deve seguir a Constituição do projeto, comunicando-se em pt-BR.
* **Hierarquia e Consistência**: Só Tailwind CSS + componentes `@manto/ui`. Zero CSS Vanilla solto.
* **Feedback imediato (NÃO-NEGOCIÁVEL)**: Toda ação tem loading/erro/sucesso via TanStack Query. Nenhum botão fica "morto" ao clique.
* **Preservação de Estado**: Nunca limpe o que o usuário preencheu em caso de erro da API; aponte o erro no campo correspondente usando a interface visual.
* **Mobile-first**: Obrigatório começar pelo mobile em superfícies públicas.
* **Movimento fluido (Princípio IX)**: Toda mudança de estado visual exige transições suaves via Framer Motion (150–350ms), respeitando obrigatoriamente `useReducedMotion()`.

---

#### 🏛️ Arquitetura Backend
* **Routes não fazem lógica de negócio** — só validam RBAC, chamam `*_ops` e serializam.
* **`*_ops.py` são puros**: nunca importam `flask.request`, `render_template` ou afins.
* **RBAC em endpoint de API é função**, não decorator Flask (chamada no início da view).

---

#### 🔧 Comandos e Regras de Testes (NÃO-NEGOCIÁVEL)
* A produção roda em PostgreSQL. **Todo teste/verificação DEVE rodar contra a cópia local do banco real (`manto_local`)** — **nunca** contra o SQLite vazio de `instance/`. Use `.\scripts\db\run-local.ps1`.
* Typecheck de frontend deve passar limpo: execute `npx tsc --noEmit` dentro de `apps/internal` ou `apps/public`.

---

#### 📝 REGRA OBRIGATÓRIA DE DOCUMENTAÇÃO VIVA
Sempre que concluir o ciclo de uma tarefa/feature da esteira do SDD (após a fase Implement), você deve atualizar obrigatoriamente os artefatos vivos em `docs/`:
1. **`docs/01_SISTEMA_E_BANCO.md`**: Atualize schema, models, rotas, RBAC e o "estado do repositório" no cabeçalho.
2. **`docs/02_MAPA_DE_PAGINAS_E_UX.md`**: Documente rotas novas/alteradas, UX e vínculos.
3. **`docs/03_HISTORICO_MUTACOES.md`**: Adicione uma nova entrada **no topo** (append-only) com migration, motivação, regras de negócio e pegadinhas encontradas.

*(Nota: O arquivo `docs/changelog.html` está congelado e não deve mais ser atualizado para economizar tokens e evitar conflitos).*
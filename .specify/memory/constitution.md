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
- **Prevenir envio duplicado (NÃO-NEGOCIÁVEL)**: todo botão que dispara uma ação
  lenta (salvar, criar, enviar, sincronizar) DEVE se desabilitar e mostrar estado
  de carregamento ao ser clicado, até a resposta chegar. Um clique a mais nunca
  pode criar registro duplicado.
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

## Stack e Restrições Técnicas

- **Backend**: Python + Flask + SQLAlchemy. Entrada: `python run.py`.
- **Banco**: SQLite em desenvolvimento; PostgreSQL/AWS RDS em produção. Migrations
  via Alembic (Flask-Migrate) — toda mudança em `app/models.py` gera migration.
- **Frontend**: Jinja2 + HTML/CSS/JS vanilla. Sem framework JS.
- **Integrações**: Google Calendar (OAuth 2.0) e Google Sheets (service account).
- **RBAC**: papéis SUPERADMIN, CASTING, FIGURINO, COMERCIAL, FINANCEIRO, VENDAS,
  ENSAIO, RH. Toda rota nova respeita o controle de acesso por papel já existente.
- **Comunicação com o usuário e textos de interface**: português (pt-BR).
- **Segredos**: nunca commitar senhas, tokens ou chaves. Use variáveis de ambiente.

## Portões de Qualidade (antes de "pronto")

Uma tarefa só está concluída quando:
- [ ] Os testes relevantes passam (`pytest tests/ -v`).
- [ ] Sem erros de tipo nos arquivos tocados (`mypy app/`).
- [ ] Código formatado e sem lint (`ruff format app/` e `ruff check app/`).
- [ ] Funções/classes novas têm docstring e type hints.
- [ ] Casos de erro tratados; nada de `except` silencioso.
- [ ] Nenhum segredo hardcoded.
- [ ] Migration criada se `models.py` mudou.
- [ ] Comportamento conferido no app real quando há mudança de interface.

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

**Versão**: 1.2.0 | **Ratificada**: 2026-05-29 | **Última alteração**: 2026-06-04

> **Changelog**
> - **1.2.0** (2026-06-04): Novo Princípio VII — todo valor monetário no padrão
>   brasileiro (milhar com `.`, decimal com `,`, duas casas), tanto na exibição
>   quanto na digitação (máscara automática), com fonte única de formatação e valor
>   numérico preservado no backend.
> - **1.1.0** (2026-06-04): Princípio V reforçado com regras concretas de feedback —
>   prevenção de envio duplicado (botão desabilita + loading), proibição de limpar o
>   formulário em erro, e feedback visível no campo ao bloquear envio.

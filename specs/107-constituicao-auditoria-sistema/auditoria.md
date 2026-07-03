# Auditoria Geral do Sistema — Manto Platform

**Data**: 2026-07-03 · **Feature**: 107 · **Método**: varreduras automatizadas (regex/grep
sobre todo o código) + inspeção dirigida por módulo + acúmulo das auditorias das features
104 (revisão mobile), 105 (upload/convite) e 106 (portal + cadastro).

## Resumo executivo

| | Crítico | Alto | Médio | Baixo | Total |
|---|---|---|---|---|---|
| ✅ Corrigido nesta feature | 1 | 4 | 3 | 2 | **10** |
| 📋 Backlog | 0 | 2 | 4 | 3 | **9** |

Corrigidos: moeda fora do padrão BR em 5 telas internas (11 ocorrências, 2 delas em formato
americano visível), 9 pontos de erro engolido sem log + 1 `print()` de debug, exclusão de
usuário sem confirmação, proteção GLOBAL contra duplo envio (cobre os 45 forms internos),
5 `alert()` de erro substituídos por feedback inline.

## Achados por módulo

### Agenda / Eventos (`app/calendar/`, `event_*.html`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| `event_create.html`: 5 valores de orçamento com formatação monetária reinventada (fonte única violada) | Alto | B | ✅ `\| brl` |
| Validação "cliente obrigatório" usava `alert()` genérico (event_detail) | Médio | B | ✅ mensagem inline |
| 2 `except Exception` sem log (cálculo de transporte/geocode) | Médio | B | ✅ log warning |
| `except` sem log no fetch de evento do Google (service.py) | Médio | B | ✅ log warning |
| Form de criação de evento: proteção de duplo envio já existia | — | — | ✔ ok |
| Exclusões (evento, ensaio, observação, material): todas com confirmação/modal | — | — | ✔ ok |
| Lint legado (imports desordenados, vars não usadas, `zip` sem strict) em routes.py | Baixo | M | 📋 |

### Home / Dashboard (`app/__init__.py`, `home.html`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| KPI de desempenho em formato monetário AMERICANO ("R$ 4,000") | **Alto** | B | ✅ `\| brl` |
| Bug conhecido: tarefas de figurino usam a query de casting (memória do projeto) | Alto | M | 📋 corrigir na próxima feature da home |

### Talentos (`app/talents/`, `talent_detail.html`, `desempenho.html`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| `talent_detail.html`: 2 valores em formato AMERICANO | **Alto** | B | ✅ `\| brl` |
| `desempenho.html`: 2 valores com formatação reinventada (sem decimais) | Médio | B | ✅ `\| brl` |
| `importer.py`: 2 `except Exception` amplos em parsing de data | Baixo | B | ✅ estreitados p/ exceções específicas |

### Financeiro / Vendas (`app/financeiro/`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| `dashboard.html`: macro `money()` local reimplementando formatação BR | Alto | B | ✅ delega ao `\| brl` |
| `pagamentos.html`: erro ao salvar status usava `alert()` | Médio | B | ✅ mensagem inline na célula |

### Admin (`app/admin/`, `admin_*.html`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| **Excluir usuário SEM confirmação** (1 clique deletava) | **Crítico** | B | ✅ confirm adicionado |

### Figurino (`app/figurino/`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| `drive_service.py`: erro de thumbnail via `print()` (invisível em produção) | Médio | B | ✅ logger |
| `figurino_form.html`: erro ao girar foto usava `alert()` | Baixo | B | ✅ mensagem inline |
| `routes.py:368`: `except` retorna o erro ao chamador (não engole) | — | — | ✔ ok |

### Ferramentas / Orçamento (`app/tools/`, `app/orcamento/`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| `settings.html`: 5 `alert()` (validação + erros de rede) | Médio | B | ✅ feedback inline único |
| `resultado.html`: `alert` de fallback de cópia manual | — | — | ✔ aceitável (fallback raro) |

### Clientes / Gastos / EducaManto

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| Exclusões com confirmação; forms leves | — | — | ✔ ok |
| Duplo envio: sem proteção própria | Médio | B | ✅ coberto pela proteção global (base.html) |

### Infra transversal (`storage.py`, `email_service.py`, `models.py`, `cli.py`)

| Achado | Sev. | Esf. | Status |
|---|---|---|---|
| 5 `except Exception` engolindo erro sem log (S3 delete, compressão, notificações, pieces JSON, CLI) | Alto | B | ✅ log warning em todos |
| **Proteção global de duplo envio** ausente (45 forms POST, só 16 protegidos) | Alto | B | ✅ handler global no `base.html` (respeita `defaultPrevented`; `setTimeout` preserva valor do submitter) |

### Revisão / Portal / Cadastro / Auth

Auditados e reformados nas features **104, 105 e 106** (mobile-first, conclusão de
comentários, progresso de upload, validação com feedback). Sem achados novos nesta passada.

## Backlog priorizado (para futuras features)

| # | Item | Sev. | Esf. | Recomendação |
|---|---|---|---|---|
| 1 | Bug das tarefas de figurino na home (query igual à de casting) | Alto | M | Feature dedicada — corrigir query em `app/__init__.py` rota `/` |
| 2 | 68 usos de `innerHTML` sem escape aparente (XSS interno) | Alto | A | Revisar por tela; começar pelas que interpolam dados de terceiros (nomes de clientes/talentos) |
| 3 | Suíte pytest + mypy no ambiente | Médio | A | Infra de fixtures contra manto_local; tornar portões mais fortes na constituição v1.4 |
| 4 | `datetime.utcnow()` deprecado (Py 3.12+) em todo o models/rotas | Médio | M | Migração mecânica p/ `datetime.now(UTC)` com verificação de timezone |
| 5 | Lint legado (I001/F841/F541/B905/UP*) em módulos antigos | Médio | M | Limpar por módulo quando tocado (não em massa) |
| 6 | Cores hardcoded em templates internos (centenas) | Baixo | A | Trocar por variáveis quando cada tela for tocada (regra já na constituição V) |
| 7 | Rate limiter com storage em memória (aviso em produção multi-worker) | Médio | B | Configurar storage (Redis/memcached) no Railway ou aceitar limitação documentada |
| 8 | Threads de sync (talent/calendar) sem observabilidade de falha | Baixo | M | Health-check/última execução em /admin |
| 9 | `terms.html` box com padding 32px em 320px (apertado, não quebrado) | Baixo | B | Ajustar junto com a próxima mudança do termo |

## Verificação

Script `verify_107.py`: varreduras (zero `{:,` em templates, zero `except` silencioso nos
pontos tratados, zero `print(` de debug em app) + renderização das telas tocadas via test
client contra `manto_local` — resultado na seção de verificação da feature.

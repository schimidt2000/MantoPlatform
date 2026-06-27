# CLAUDE.md — Instruções para o Claude Code

> Este arquivo é lido automaticamente pelo Claude Code ao abrir o projeto.
> Ele define como o Claude deve trabalhar neste projeto Python.

---

## 🏗️ Sobre o Projeto

- **Nome**: Plataforma Manto
- **Descrição**: Sistema empresarial ERP para gestão de eventos, talentos, figurino, financeiro e agenda. Integrado com Google Calendar e Google Sheets.
- **Stack**: Python + Flask + SQLAlchemy
- **Frontend**: Jinja2 templates + HTML/CSS/JS vanilla (sem framework JS)
- **Banco de dados**: SQLite (desenvolvimento) → PostgreSQL/AWS RDS (produção)
- **Integrações**: Google Calendar API (OAuth 2.0), Google Sheets API (service account)

---

## 📁 Estrutura do Projeto

```
Manto_Platform/
├── CLAUDE.md
├── run.py                 ← entrypoint (python run.py)
├── requirements.txt
├── migrations/            ← Alembic (Flask-Migrate)
├── instance/
│   └── uploads/           ← arquivos enviados (contratos, fotos, figurinos)
└── app/
    ├── __init__.py        ← app factory + rota home
    ├── config.py
    ├── models.py          ← todos os modelos SQLAlchemy
    ├── static/            ← CSS, JS, imagens
    ├── templates/         ← Jinja2 templates
    ├── auth/              ← login, logout, perfil
    ├── admin/             ← gestão de usuários, settings, desempenho
    ├── calendar/          ← agenda, eventos, sync Google Calendar
    ├── talents/           ← banco de talentos, import Google Sheets
    ├── figurino/          ← fichas de figurino
    ├── financeiro/        ← dashboard financeiro, pagamentos, salários
    ├── rh/                ← RH (em construção)
    └── tools/             ← calculadora de transporte
├── .claude/
│   └── skills/
│       ├── python-quality.md
│       ├── ui-ux.md
│       ├── autonomy.md
│       └── architecture.md
```

---

## 🐍 Qualidade de Código Python

### Antes de escrever qualquer código:
1. Verifique se já existe algo parecido no projeto — **não duplique lógica**
2. Pense na interface pública da função/classe antes da implementação
3. Escreva o teste ANTES do código (TDD: Red → Green → Refactor)

### Padrões obrigatórios:
- **Type hints** em todas as funções e métodos
- **Docstrings** em classes e funções públicas (formato Google style)
- **Nomes descritivos**: sem abreviações obscuras (`user_count`, não `uc`)
- **Funções pequenas**: máximo ~30 linhas; se passar, extraia funções
- **Evite aninhamento profundo**: máximo 3 níveis de indentação
- **Constantes em UPPER_CASE** no topo do módulo ou em `config.py`
- **Nunca use `except Exception` sem logar o erro**

### Ferramentas que devem ser usadas:
```bash
# Verificar tipos
mypy app/

# Linting e formatação
ruff check app/
ruff format app/

# Testes
pytest tests/ -v --cov=app
```

### Exemplo de código de qualidade:
```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class User:
    """Representa um usuário do sistema."""
    id: int
    name: str
    email: str
    is_active: bool = True

def get_active_users(users: list[User]) -> list[User]:
    """Retorna apenas usuários ativos.
    
    Args:
        users: Lista completa de usuários.
        
    Returns:
        Lista filtrada com apenas usuários ativos.
    """
    return [u for u in users if u.is_active]
```

---

## 🎨 UI/UX — Quando Houver Interface

### Princípios de design que devem ser seguidos:
- **Hierarquia visual clara**: o usuário deve saber onde olhar primeiro
- **Feedback imediato**: toda ação deve ter resposta visual (loading, erro, sucesso)
- **Consistência**: mesma paleta, mesmos espaçamentos, mesmos componentes
- **Mobile-first**: comece pelo mobile, expanda para desktop

### Paleta e tipografia:
- Use variáveis CSS para todas as cores — zero cores hardcoded no HTML
- Escolha fontes com personalidade (Google Fonts): evite Inter, Arial, Roboto
- Espaçamento baseado em múltiplos de 4px (4, 8, 12, 16, 24, 32, 48...)

### Componentes obrigatórios:
- Estado de loading para operações assíncronas
- Mensagens de erro amigáveis (nunca exponha stack traces ao usuário)
- Confirmação antes de ações destrutivas (deletar, etc.)
- Feedback de sucesso após operações importantes

### Ao criar qualquer tela nova:
1. Defina o objetivo da tela (o que o usuário precisa fazer aqui?)
2. Liste os elementos necessários (formulários, tabelas, botões)
3. Pense no estado vazio (o que aparece quando não há dados?)
4. Pense nos erros (o que aparece quando algo dá errado?)
5. Só então escreva o código

---

## 🤖 Autonomia — Como o Claude Deve Trabalhar

### Fluxo de desenvolvimento:
```
1. ENTENDER → Perguntar se a tarefa não está clara
2. PLANEJAR  → Mostrar o plano ANTES de escrever código
3. EXECUTAR  → Implementar em pequenos passos verificáveis
4. TESTAR    → Rodar os testes após cada mudança
5. REVISAR   → Checar qualidade antes de declarar "pronto"
```

### Regras de autonomia:
- **Nunca assuma**: se houver dúvida sobre um requisito, pergunte antes
- **Mostre o plano**: antes de mudanças grandes, liste o que será alterado
- **Pequenos commits**: cada funcionalidade = um commit atômico
- **Não quebre o que funciona**: rode os testes antes de cada commit
- **Relate o progresso**: informe o que foi feito e o que falta

### Quando travar:
1. Tente 2 abordagens diferentes
2. Se ainda travar, pare e explique o problema claramente
3. Não fique em loop — peça ajuda ao usuário

### Antes de qualquer task grande, fazer:
```bash
# Verificar estado atual dos testes — SEMPRE contra a cópia local manto_local (Postgres),
# nunca contra o SQLite vazio. Ver a "REGRA DE TESTES" em "🔧 Comandos do Projeto".
pytest tests/ -v

# Verificar se não há erros de tipo
mypy app/

# Garantir que o código está formatado
ruff format app/ --check
```

---

## 🏛️ Arquitetura

### Estrutura de módulos Python:
```
src/
├── __init__.py
├── config.py          ← configurações e variáveis de ambiente
├── models/            ← modelos de dados (dataclasses, Pydantic, SQLAlchemy)
│   └── __init__.py
├── services/          ← lógica de negócio (pura, sem HTTP)
│   └── __init__.py
├── api/ ou views/     ← rotas HTTP (só chama services)
│   └── __init__.py
├── repositories/      ← acesso ao banco de dados
│   └── __init__.py
└── utils/             ← funções utilitárias genéricas
    └── __init__.py
```

### Regras de arquitetura:
- **Separação de responsabilidades**: routes não fazem lógica de negócio
- **Services são puros**: não importam nada de HTTP/web
- **Repositories abstraem o banco**: o resto do código não faz queries diretas
- **Config centralizado**: zero strings mágicas espalhadas no código
- **Injeção de dependência**: prefira receber dependências no construtor

### Dependências entre camadas (só pode depender da camada abaixo):
```
API/Views → Services → Repositories → Models
              ↓
           Utils (qualquer camada pode usar)
```

### Configuração via variáveis de ambiente:
```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-key")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

config = Config()
```

---

## ✅ Checklist Antes de Dizer "Pronto"

- [ ] Todos os testes passando (`pytest`) — **rodados contra `manto_local` (Postgres), não SQLite**
- [ ] Sem erros de tipo (`mypy`)
- [ ] Código formatado (`ruff format`)
- [ ] Sem warnings de linting (`ruff check`)
- [ ] Funções novas têm docstring
- [ ] Casos de erro tratados
- [ ] Sem secrets/senhas hardcoded no código
- [ ] Variáveis com nomes claros e descritivos

---

## 🔧 Comandos do Projeto

> ⚠️ **REGRA DE TESTES — LEIA ANTES DE VERIFICAR QUALQUER COISA**
> Produção roda em **PostgreSQL**. Por isso, **todo teste/verificação DEVE rodar contra a
> cópia local do banco real** (`manto_local`, PostgreSQL 18 local) — **nunca** contra o
> SQLite vazio de `instance/`. O SQLite não pega bugs Postgres-only (ex.: `float−Decimal` no
> financeiro). Antes de verificar: garanta que `manto_local` está atualizado e aponte o app/
> teste para ele via `DATABASE_URL` (use `scripts/db/run-local.ps1`).
> Detalhes e setup: `scripts/db/README.md`.

```powershell
# Instalar dependências
pip install -r requirements.txt

# Rodar aplicação (SQLite de dev — só para uso casual)
python run.py

# ── BANCO DE TESTES (cópia real de produção) ──────────────────────────
# Rodar o app/verificações apontando para a cópia local (Postgres) — USE ISTO PARA TESTAR
.\scripts\db\run-local.ps1
#   (equivale a: $env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); python run.py)

# Atualizar a cópia local com o backup mais recente
.\scripts\db\refresh-local-db.ps1
# Baixar um dump novo do Railway E atualizar a cópia local
.\scripts\db\refresh-local-db.ps1 -Fresh
# Backup manual do banco de produção (também roda sozinho toda noite, 02:00)
.\scripts\db\backup-railway.ps1
# ──────────────────────────────────────────────────────────────────────

# Aplicar migrations do banco
python -m flask db upgrade

# Criar nova migration após alterar models.py
python -m flask db migrate -m "descrição"

# Rodar testes — SEMPRE contra manto_local (defina DATABASE_URL para a cópia local antes)
pytest tests/ -v

# Rodar com cobertura
pytest tests/ --cov=app --cov-report=html

# Verificar tipos
mypy app/

# Formatar código
ruff format app/

# Verificar lint
ruff check app/
```

---

## 📋 Skills Adicionais

O Claude deve ler os arquivos em `.claude/skills/` quando trabalhar nas áreas correspondentes:

- **`.claude/skills/python-quality.md`** → ao escrever ou revisar código Python
- **`.claude/skills/ui-ux.md`** → ao criar ou modificar interfaces
- **`.claude/skills/autonomy.md`** → ao planejar tarefas complexas
- **`.claude/skills/architecture.md`** → ao criar novos módulos/estruturas

---

*Gerado para uso com Claude Code (VSCode Extension)*
*Inspirado em: obra/superpowers, VoltAgent/awesome-agent-skills, nextlevelbuilder/ui-ux-pro-max-skill*

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/090-revisao-arquivos-temporarios/plan.md`
<!-- SPECKIT END -->

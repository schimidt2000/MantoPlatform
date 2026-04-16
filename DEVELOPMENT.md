# Guia de Desenvolvimento — Manto Platform

O sistema está em produção no Railway (auto-deploy via GitHub). Este guia define como desenvolver localmente e publicar mudanças com segurança.

---

## Branches

| Branch | Propósito |
|--------|-----------|
| `dev`  | Desenvolvimento diário — commits livres |
| `main` | Produção — Railway deploya automaticamente em todo push |

**Nunca commitar direto no `main`.** Todo desenvolvimento vai para `dev`, e só sobe para `main` quando estiver testado e pronto.

---

## Fluxo de trabalho

```bash
# 1. Garanta que está no dev
git checkout dev

# 2. Desenvolve, commita normalmente...
git add arquivo_modificado.py
git commit -m "feat: descrição da mudança"
git push origin dev

# 3. Quando a feature estiver pronta para produção:
git checkout main
git merge dev
git push origin main   # Railway detecta e deploya automaticamente

# 4. Volta para dev
git checkout dev
```

O Railway leva cerca de 2–3 minutos para buildar e deployar após o push.

---

## Rodando localmente

### Pré-requisitos
```bash
pip install -r requirements.txt
```

### Variáveis de ambiente

O arquivo `.env` (já criado, nunca commitado) carrega automaticamente via `python-dotenv`.

Preencha os campos marcados `COPIAR_DO_RAILWAY` com os valores do painel Railway:
- Railway dashboard → seu projeto → **Variables**

### Banco de dados local

Por padrão, sem `DATABASE_URL` no `.env`, o app usa **SQLite** (`instance/manto.db`). É o modo ideal para desenvolvimento — rápido, sem dependências externas.

Para criar/atualizar o banco local:
```bash
flask db upgrade
python seed.py   # cria superadmin se banco estiver vazio
```

### Rodando o servidor
```bash
python run.py
```

Acesse: http://localhost:5000

---

## Usando o PostgreSQL do Railway localmente (opcional)

A `DATABASE_URL` interna do Railway (`postgres.railway.internal`) **não funciona fora da rede Railway**. Para conectar localmente ao banco de produção:

1. No Railway dashboard → serviço **PostgreSQL** → aba **Connect**
2. Copie a **Public URL** (formato: `postgresql://postgres:SENHA@roundhouse.proxy.rlwy.net:PORTA/railway`)
3. Cole no `.env` local:
   ```
   DATABASE_URL=postgresql://postgres:SENHA@roundhouse.proxy.rlwy.net:PORTA/railway
   ```

> **Cuidado:** conectar ao banco de produção localmente permite alterar dados reais. Use apenas para inspecionar dados, nunca para testes destrutivos.

---

## Google OAuth em desenvolvimento

O Google OAuth exige que a URI de redirecionamento esteja registrada no Console do Google. Para usar localmente:

1. Acesse [console.cloud.google.com](https://console.cloud.google.com) → seu projeto → **APIs & Serviços → Credenciais**
2. Edite o **OAuth 2.0 Client ID**
3. Em **URIs de redirecionamento autorizados**, adicione: `http://localhost:5000/google/callback`
4. O `.env` local já aponta para essa URI:
   ```
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:5000/google/callback
   ```

---

## O que muda entre local e produção

| Variável | Local | Produção (Railway) |
|----------|-------|--------------------|
| `FLASK_ENV` | `development` | `production` |
| `DATABASE_URL` | SQLite (ausente) | PostgreSQL Railway |
| `PORTAL_URL` | `http://localhost:5000` | URL pública Railway |
| `GOOGLE_OAUTH_REDIRECT_URI` | `http://localhost:5000/google/callback` | URL pública + `/google/callback` |
| `USE_S3` | `false` (arquivos locais) | `false` ou `true` conforme config |
| `SECRET_KEY` | Qualquer valor | Chave segura gerada |

---

## Migrations

Após alterar `app/models.py`, gere uma nova migration:

```bash
flask db migrate -m "descrição curta da mudança"
flask db upgrade
```

Commite o arquivo gerado em `migrations/versions/` junto com o código que o motivou.

---

## Estrutura de módulos

```
app/
├── __init__.py        ← app factory + rotas globais (/health, /)
├── config.py          ← todas as configurações via env vars
├── models.py          ← todos os modelos SQLAlchemy
├── auth/              ← login, logout, OAuth Google
├── admin/             ← gestão de usuários, configurações
├── calendar/          ← eventos, agenda, sync Google Calendar
├── talents/           ← banco de talentos, import Sheets
├── figurino/          ← fichas de figurino, sync Drive
├── financeiro/        ← dashboard financeiro, pagamentos
├── tools/             ← calculadora de transporte
└── rh/                ← RH (scaffolding)
```

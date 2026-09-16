# Quickstart (Phase 1) — como provar que a Feature 300 funciona

Guia de execução e conferência. O código de implementação mora no `tasks.md`; aqui está só o que se
roda e o que se espera ver.

## 0. Ambiente

Todo script que sobe o app roda com estas variáveis — sem elas o `create_app()` liga as threads de
fundo, e o `manto_local` é espelho da produção, com token do Google e credenciais de e-mail reais:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'
```

O interpretador é o do projeto: `.\.venv\Scripts\python.exe`.

## 1. O verify

```bash
python specs/300-catalogo-rapido/verify_300.py
```

**Ele deve falhar antes da implementação** (Princípio VIII) — e falhar pelo motivo certo: a
contagem de consultas estoura o teto nos cenários 1, 3 e 4. Se passar com o código de hoje, o verify
está errado, não o código.

O critério é **contagem de consultas**, nunca relógio (R7). A técnica é um ouvinte de SQL:

- registra-se `before_cursor_execute` no engine, contando execuções;
- `db.session.expire_all()` antes de cada medida, para não medir cache de sessão;
- monta-se a listagem e compara-se o total com o teto.

Sete cenários, na ordem do `spec.md`. O cenário 5 **deve falhar** (papel sem permissão recebendo
recusa), e o 7 é a limpeza — `rollback()` antes, `user.roles.clear()` antes de apagar o usuário.

## 2. Os portões da constituição

```bash
cd frontend && npm run typecheck
```

Um comando, três SPAs — `npx tsc --noEmit` app a app **não** satisfaz o portão, porque esquece o
portal.

```bash
ruff check app/api/admin_catalogo_read.py app/api/catalogo_read.py app/admin/catalog_character_ops.py
```

`ruff format` em nenhum deles: são arquivos legado, e reformatar arquivo inteiro é proibido.

## 3. As telas, abertas de verdade

`tsc` limpo não é verificação de interface.

**Gerenciador** (`/admin/catalogo`, exige SUPERADMIN), no computador:

| O que abrir | O que conferir |
|---|---|
| Modo **Cards** | as capas aparecem; no inspetor, o endereço pedido é `/catalogo/midia/t/128/...`, não o original |
| Modo **Árvore** | idem nas capas e nos rostos; expandir um tema não trava |
| Modo **Personagens** | a lista monta; a animação de `layout` não salta quando a imagem chega |
| Rolagem | as imagens fora da tela **não** são pedidas até rolar até elas |
| Busca da própria listagem (campo do topo) | digitar uma palavra sem pausa gera **uma** requisição, não uma por tecla; a lista **não pisca esqueleto** a cada letra |
| Busca de personagem (painel do tema) | idem — mesma pausa de 300 ms |
| Busca no modo **Personagens** | continua **instantânea** de propósito: ali o filtro é client-side e não consulta o servidor |
| Tela de edição de um produto | o seletor de categorias enche sem que a listagem completa seja baixada |
| Produto com foto ausente | aparece o espaço reservado, nunca quadrado quebrado |

**Vitrine** (pública), em viewport mobile **375×812** (Princípio X):

| O que abrir | O que conferir |
|---|---|
| Grade geral | carrega; sem rolagem horizontal |
| Grade de **categorias** | as capas pedem variante, não o original — é a lacuna que a 270 deixou |
| Página de um produto | a **foto grande continua sendo o original** (decisão 9 da 270), e a tira de miniaturas continua em 128 |
| **Lista de desejos** | os quadrados de 64 px pedem a variante de 128 |

## 4. A medição, para comparar com o antes

Medido no espelho em 16/09/2026 (458 produtos, 457 ativos), pelo HTTP, com o ouvinte de SQL:

| Caminho | Antes | Depois |
|---|---|---|
| `GET /api/admin/catalogo` | 1.847 | **6** |
| `GET /api/admin/catalogo/personagens` | 474 | **6** |
| `GET /api/catalogo` | 917 | **4** |
| `GET /api/catalogo/categorias` | 492 | **4** |
| `GET /api/catalogo/categoria/<maior>` | 182 | **4** |

*(O gerenciador mede 1.847 pelo HTTP e 1.846 chamando a função direto: a diferença de 1 é o
`user_loader` da requisição autenticada. Os caminhos públicos não têm login e batem exatamente.)*

O que importa não é o número exato, e sim a propriedade: **a contagem não cresce com a quantidade
de produtos**. O teto de 10 é a aferição prática disso.

Conferido junto: as respostas seguem **idênticas** à referência, hash a hash — inclusive a da visão
Personagens, que caiu de 474 para 6 consultas com o mesmo sha256.

## 5. Depois do deploy (obrigatório)

O cache de miniaturas está frio (9 arquivos gerados em 128 px). Sem aquecer, a primeira pessoa a
abrir a tela paga a geração de centenas de miniaturas dentro de uma thread do gunicorn — a
assinatura exata do incidente da feature 263.

Com a **fila de push vazia** (um deploy troca o contêiner e mataria a rodada), no `manto-backend`:

```bash
cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask warm-thumbnails
```

Depois, provar que o backend está vivo por um endpoint `/api/` devolvendo JSON — nunca por `/health`
na URL pública, que cai no fallback da SPA e responde 200 com o Flask morto.

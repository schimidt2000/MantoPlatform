# Quickstart — 348 Origem completa

## Pré-requisitos

- Espelho `manto_348` restaurado do dump noturno (`backups/manto_2026-11-17_0200.dump`) e `.local-db-url` do worktree
  apontando para ele.
- `.venv` do checkout principal (junção) e `frontend/node_modules`.

## Migration

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
..\..\..\.venv\Scripts\flask.exe db upgrade   # d334b2c4e6f8 → a348c0d1e2f3
..\..\..\.venv\Scripts\flask.exe db downgrade d334b2c4e6f8; ..\..\..\.venv\Scripts\flask.exe db upgrade  # ida e volta
```

Esperado: `origem_codigos` criada; colunas novas presentes; `alembic_version = a348c0d1e2f3`.

## Verificação automática

```powershell
$env:PYTHONUTF8 = '1'; ..\..\..\.venv\Scripts\python.exe specs/348-origem-completa/verify_348.py
```

Esperado: todos os cenários OK, inclusive os que devem recusar (código usado/vencido, conversa inexistente, frente
fora da lista, venda sem frente, Figurino no PATCH comercial). Nenhuma conexão de saída (disjuntor de rede).

## Telas

Backend na 5348 (`run-local-sem-google.py` copiado com a porta trocada) e Vite na 6348 (config temporária com o proxy
na 5348), os dois a partir do worktree.

1. **Lista de desejos (390×844)**: abrir `/?gclid=teste348&gad_campaignid=999&utm_source=google` → conferir no
   `localStorage` os marcadores e o código; adicionar um personagem; "Enviar" → a URL do WhatsApp termina com
   `Código do site: #XXXXX`.
2. **Formulário (390×844)**: `/f/pre-contrato` na mesma aba; enviar → o `wa_link` leva a linha do código.
3. **Visita sem marcador** (aba anônima): a mensagem sai sem código.
4. **Aba Comercial (desktop e 390)**: evento com venda e título sem palavra de social → campo "Frente" vazio com
   "Sugestão pelo título: Festas"; salvar sem frente → erro no campo; escolher "Social" → salva, leitura mostra
   "Social". Evento ligado a conversa → linha "Origem da venda".

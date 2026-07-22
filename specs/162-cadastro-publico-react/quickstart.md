# Quickstart — Cadastro Público de Talentos em React (162)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:public                # frontend do app público, noutro terminal
```

## Roteiro manual

1. `/cadastro` (app `public`) — preencher todos os campos obrigatórios, anexar as 3 fotos/
   documentos obrigatórios (rosto, corpo inteiro, documento) e enviar. Deve navegar para a tela
   de confirmação.
2. Deixar um campo obrigatório em branco (ex.: e-mail) e tentar enviar — a mensagem de erro
   específica deve aparecer, sem apagar os demais campos já preenchidos.
3. Anexar um arquivo de tipo não permitido (ex.: `.gif` na foto do rosto) — erro específico sobre
   aquele anexo.
4. Digitar um CPF já cadastrado no campo de CPF — aviso de duplicidade deve aparecer antes de
   enviar o formulário completo.
5. Marcar "estrangeiro" — o campo de CPF deve deixar de ser obrigatório; os demais campos
   continuam exigidos.
6. Selecionar gênero "Outro" — campo de texto livre deve aparecer e ser usado como valor final.
7. Testar em viewport 320px e 430px (DevTools) — sem rolagem horizontal, teclado virtual não
   deve esconder o campo ativo nem o botão de envio.
8. Comparar com a tela antiga (`/cadastro` no Flask, `app.*`) para os mesmos dados de entrada —
   o talento resultante deve ter os mesmos campos preenchidos.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_162_cadastro_publico_react.py
```

Cobre: envio válido cria talento pendente com paridade de campos vs. caminho Jinja, erro por
campo obrigatório faltante, erro por upload inválido, CPF duplicado (bloqueia no POST final),
estrangeiro sem CPF, honeypot preenchido (não cria talento, responde sucesso), rate limit,
checagem de CPF (`GET /api/cadastro/check-cpf`) para CPF existente/inexistente/incompleto.

## Frontend

```powershell
npm run typecheck:public
npm run build:public
```

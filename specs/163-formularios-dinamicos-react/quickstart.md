# Quickstart — Formulários Dinâmicos Públicos em React (163)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:public                # frontend do app público, noutro terminal
```

## Roteiro manual

1. `/f/pre-contrato` (app `public`) — preencher todos os campos obrigatórios vigentes e enviar;
   deve navegar para a tela de confirmação e abrir o WhatsApp automaticamente (ou mostrar o botão
   se a abertura automática for bloqueada pelo navegador).
2. `/f/corporativo` — mesmo roteiro, conferindo que a mensagem final identifica "contrato
   corporativo".
3. Deixar um campo obrigatório em branco e um CPF/CNPJ/CEP inválido ao mesmo tempo — os dois
   erros devem aparecer, cada um junto ao seu campo, sem apagar os demais campos preenchidos.
4. Selecionar forma de pagamento "Outros" (se o formulário tiver esse campo) — o campo "Descreva
   outros" deve aparecer e ser obrigatório; escolher outra forma de pagamento deve escondê-lo.
5. Digitar um CEP válido num campo de CEP (se o formulário tiver) — logradouro/bairro/cidade/
   estado devem se preencher sozinhos; digitar um CEP inexistente não deve travar nada.
6. No painel administrativo (`/formularios/editor/comum`, autenticado, SUPERADMIN), adicionar um
   campo novo — reabrir `/f/pre-contrato` em React e conferir que o campo novo aparece, sem
   precisar de deploy.
7. Testar em viewport 320px e 430px (DevTools) — sem rolagem horizontal.
8. Comparar com a tela antiga (`/f/pre-contrato`/`/f/corporativo` no Flask, `app.*`) para os
   mesmos dados de entrada — a resposta salva e a mensagem de WhatsApp devem ser idênticas.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_163_formularios_dinamicos_react.py
```

Cobre: schema retornado por tipo de formulário, submissão válida (paridade de campos salvos vs.
o caminho Jinja), erro com múltiplos campos inválidos simultâneos, "Descreva outros" obrigatório
condicional, honeypot (sem salvar resposta), 404 para `form_type` inexistente.

## Frontend

```powershell
npm run typecheck:public
npm run build:public
```

# Quickstart: Transporte explícito por dias no EducaManto + calculadora em React

## Rodar localmente

```powershell
# Backend — SEMPRE contra a cópia local (Postgres), nunca o SQLite vazio
.\scripts\db\run-local.ps1

# Frontend (staff) — em outro terminal
cd frontend; npm run dev:internal
```

## Verificar a correção na tela Jinja (`/educamanto`)

1. Logar com um usuário Comercial/Superadmin/Ensaio/Revendedor EducaManto.
2. Abrir `/educamanto`, escolher um pacote, preencher **1 dia** (ex.: d1=1) → calcular a distância de
   um endereço fora de São Paulo → escolher van + carretinha + pessoas → conferir que o transporte é
   o valor de **uma** viagem (sem regressão).
3. Mudar para **múltiplos dias** (ex.: d1=2, d2=1 → total 3) → conferir que a linha de transporte
   mostra claramente "valor da viagem × 3 dias = total" e que esse total (não o valor de uma viagem
   só) é o que aparece somado no valor final sem/com nota.
4. Clicar em "Gerar orçamento" → conferir que o PDF gerado usa o mesmo valor de transporte já
   multiplicado.

## Verificar a nova tela React (`/educamanto` no app interno — rota a definir na implementação)

1. Acessar a tela React equivalente, selecionar o mesmo pacote/dias/ensemble/endereço/tipo de
   transporte/pessoas do teste acima.
2. Conferir que os valores sem/com nota e a linha de transporte (com a multiplicação por dias) batem
   exatamente com os valores obtidos na tela Jinja para os mesmos parâmetros.
3. Conferir o link de saída para a tela Jinja (PDF/histórico/CRUD de pacotes).

## Verificação funcional automatizada (obrigatória antes do merge)

Script com Flask test client contra `manto_local`, requests **fora** de `app.app_context()`:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts_temp\verify_171_educamanto_transporte.py
```

Cobrir: `GET /api/educamanto/packages` (200, 401 sem sessão, 403 papel sem acesso),
`GET /api/educamanto/distancia` (200, 400 endereço inválido/Maps não configurado),
`POST /api/educamanto/calcular` (200 com 1 dia = valor de uma viagem, 200 com múltiplos dias = valor
multiplicado, 200 sem `km_ida`/transporte ausente = transporte zero, 400 pacote inválido, 400 dias
zerados).

## Antes de declarar pronto

- `ruff check app/` limpo nos arquivos tocados/criados.
- `npx tsc --noEmit` e `npm run build` em `frontend/apps/internal` sem erros.
- Conferido no navegador (tela Jinja ajustada + tela React nova), não só nos testes automatizados.
- `docs/changelog.html` atualizado com a entrega, republicado no mesmo link existente.

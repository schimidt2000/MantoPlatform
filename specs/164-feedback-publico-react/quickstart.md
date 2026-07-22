# Quickstart — Feedback Público por Token em React (164)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:public                # frontend do app público, noutro terminal
```

## Roteiro manual

1. Gerar um token de teste (via `gerar_link` autenticado ou diretamente no banco) e abrir
   `/avaliar/<token>` no app `public` — deve mostrar o nome do evento (e a data, se houver).
2. Escolher 5 estrelas — etiquetas positivas devem aparecer (não as de atenção).
3. Escolher 3 estrelas — etiquetas de atenção devem aparecer (não as positivas); trocar de volta
   para 5 estrelas deve esconder as de atenção e mostrar as positivas de novo, sem etiqueta
   nenhuma pré-marcada.
4. Tentar enviar sem nome — erro claro, sem perder a nota já escolhida.
5. Preencher nome + nota (etiquetas e comentário opcionais) e enviar — tela de agradecimento
   aparece no lugar do formulário.
6. Abrir `/avaliar/token-que-nao-existe` — tela de "link inválido" deve aparecer.
7. Testar em viewport 320px e 430px (DevTools) — sem rolagem horizontal, estrelas com alvo de
   toque confortável.
8. Comparar com a tela antiga (`/avaliar/<token>` no Flask, `app.*`) para os mesmos dados de
   entrada — o registro de feedback salvo deve ser idêntico.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_164_feedback_publico_react.py
```

Cobre: `GET` com token válido/inválido, submissão válida com paridade de campos salvos vs. o
caminho Jinja, erro por nome/nota faltando, etiqueta fora de categoria descartada
silenciosamente.

## Frontend

```powershell
npm run typecheck:public
npm run build:public
```

# Quickstart — validar a Feature 315

## 1. Pré-requisitos

- Worktree `C:\tmp\mp315`, branch `315-pedido-de-cancelamento`; `.local-db-url` copiado; `frontend/node_modules`
  instalado.
- Ambiente de todo script com `create_app()`: `DATABASE_URL` de `.local-db-url`, `FLASK_ENV=development`,
  `MANTO_SEM_THREADS=1`, `PYTHONUTF8=1`, `PYTHONPATH` = raiz do worktree.
- Migration aplicada no `manto_local`: `flask db upgrade` (head novo sobre `c5d2f7a9e306`); conferir
  `flask db heads`.

## 2. Verify

```powershell
& $py specs\315-pedido-de-cancelamento\verify_315.py            # rodada inteira
& $py specs\315-pedido-de-cancelamento\verify_315.py '--so=1,5'  # iteração (aspas simples: PowerShell)
```

Esperado ao fim: todos os cenários OK; "chamadas ao Google: 0" nos cenários de pedir e recusar (os de cancelar e
excluir usam o Google falso). Regressão: `verify_306.py` (base 67/69), `verify_312.py` (27/27), `verify_303.py`,
`verify_311.py`, `verify_302.py`.

## 3. Portões

- `cd frontend && npm run typecheck`; `ruff check` nos arquivos tocados (comparar com HEAD).
- **Tela aberta** (skill `manto-conferir-tela`; backend do worktree na 5011 com o Google dublado, interno na 5193,
  portal num Vite próprio), com usuários descartáveis:
  1. Comercial: "Solicitar cancelamento" num evento simples (Parte com nome/PIX; Nada), num ensaio e num evento com
     cachê pago (item desabilitado com a frase), numa venda de vários dias (o 1º dia com a escolha do alcance; outro
     dia "vale só para ele"), numa venda virtual (só o motivo).
  2. Quadro do pedido como Comercial autor, Comercial colega, Casting e revendedor (o que cada um lê).
  3. Faixa: uma frase, duas frases, e em 375 px; o link de um pedido e a lista de vários.
  4. Selo na agenda (Mês, Dia, busca).
  5. Superadmin: "Analisar e decidir" (o diálogo de cancelar vazio com o pedido acima, só leitura); "Recusar pedido"
     com confirmação; a fila "Cancelamentos" com alcance e devolução; o sino (pedido e decisão).
  6. Portal: Agenda, Convites e Histórico em 375×812 com "Evento em confirmação".
- **Sem salvar cancelamento nem exclusão contra o Google real**: na tela, só o backend com o Google dublado.

## 4. Depois do deploy (com o dono)

- O pedido de 07/10 (evento 1350) aparece na faixa vermelha e na fila "Cancelamentos" para o dono decidir (cancelar,
  recusar ou devolver ao Google e recusar).
- Avisar a equipe: o botão chama-se "Solicitar cancelamento", pede a devolução combinada completa, e só o Superadmin
  fecha o pedido; não apagar no Google.

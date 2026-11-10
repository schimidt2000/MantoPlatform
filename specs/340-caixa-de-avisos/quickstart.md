# Roteiro de verificação — 340

## 1. Local (worktree `C:\tmp\mp340`, banco `manto_340`)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe -m flask db upgrade
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\340-caixa-de-avisos\verify_340.py
```

Esperado: todos os cenários `OK`, `0 FALHA · 0 BLOQUEADO`; os marcados "deve falhar" provam a
recusa (404). Regressão, com as mesmas variáveis: `verify_310.py`, `verify_205.py` (em
`scripts/db/` do checkout principal, se existir) e `verify_304.py`.

Portões: `ruff check` nos `.py` tocados; `ruff format` em `servicos/avisos/app.py`, no verify e na
migration; `cd frontend; npm run typecheck`; `python scripts/validar_startcommand.py` (o
`startCommand` do backend não muda, mas o arquivo muda).

Tela (skill `manto-conferir-tela`, viewport 375×812): abrir
`/catalogo/v/pedido/<token>?order_nsu=<nsu>&slug=x&transaction_nsu=y` com o backend local parado →
a página fica em "Confirmando…" e a aba Rede mostra o `POST …/retorno` repetido; subir o backend →
a tentativa seguinte passa e a página mostra o estado do pedido.

## 2. Produção (à noite, Events do Render abertos, com o dono)

Deploy: merge na `main` + push (skill `manto-deploy`). O Blueprint cria o `manto-avisos` sozinho.

1. **URL do serviço**: no painel, o `manto-avisos` tem de estar em
   `https://manto-avisos.onrender.com`. Se o Render deu outra, trocar `AVISOS_BASE_URL` em
   `app/config.py`, publicar e só então seguir. A loja está desligada: nenhum link nasceu com a URL
   errada.
2. **Sondas** (duas vezes cada, capturando `WebException` no PowerShell 5.1):
   - `GET https://manto-avisos.onrender.com/health` → 200 `{"ok": true}`;
   - `GET https://manto-avisos.onrender.com/health/banco` → 200;
   - `POST https://manto-avisos.onrender.com/api/webhooks/infinitepay/errado` com `{}` → 404;
   - backend vivo por um `/api/` com JSON (`GET /api/virtuais/vitrine`).
3. **Log do backend**: `[caixa-de-avisos] thread iniciada (intervalo: 10s)`; log do receptor sem
   segredo em nenhuma linha.
4. **Teste A pela caixa** (junto do roteiro da 310, com a loja ligada e a campanha de teste fora da
   vitrine): Pix de R$ 1 → no banco, a linha em `virtual_payment_inbox` com `drained_at` e
   `notification_id`, o aviso `efetivado`, o evento com Meet e o e-mail `compra_confirmada`.
5. **Teste do deploy**: reservar na campanha de teste, abrir o checkout, disparar um Manual Deploy
   do `manto-backend` e pagar durante a troca → a linha espera na caixa e vira venda até ~1 min
   depois de o backend voltar, sem ninguém tocar em nada. Conferir "Pagamentos a conferir" vazio.
6. **Push só de docs** (o próprio `docs(340)` de fechamento): nos Events, o `manto-backend` e o
   `manto-frontend` não fazem deploy.
7. Limpeza: `limpar_venda_teste.py --pedido N --execute` (310) e pausar a campanha de teste.

## 3. Desligar o caminho novo (sem deploy de código)

Se o receptor der problema: setar `INFINITEPAY_AVISO_BASE_URL=https://app.mantoproducoes.com.br`
no `manto-backend` (painel) — os links novos voltam a avisar pela rota antiga do backend. Links já
abertos continuam no endereço com que nasceram.

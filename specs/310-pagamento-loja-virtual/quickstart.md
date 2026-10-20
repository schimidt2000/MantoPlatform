# Quickstart — validar a 310

## 1. Local (antes do merge)

Worktree `C:\tmp\mp310`; venv do repo principal pelo caminho absoluto; `.local-db-url` copiado.

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\310-pagamento-loja-virtual\verify_310.py
```

Esperado: 44/44, e cada cenário marcado "deve falhar no HEAD" falha contra `98192e8` (rodar uma vez
com o núcleo antigo antes de implementar). Regressão: `verify_205.py` e `verify_304.py` verdes.
`npm run typecheck`; `ruff check` nos tocados; `node --check frontend/server.js`.

Migration: `flask db upgrade` e `flask db downgrade -1` no `manto_local` e num banco descartável com o
dump de produção do dia (`flask db upgrade && python seed.py`).

Tela aberta (Browser pane; Flask do worktree em `127.0.0.1:5001`, Vite em `127.0.0.1:5183`, porque as
portas padrão são do outro checkout):
- `/v/<slug>` em 375×812: horários só a partir de 2 h; reservar; voltar com `?order_nsu=…&slug=…`
  na página do pedido (dublê pago) → "pago" e URL limpa;
- página do pedido nos três estados de espera;
- Configurações: card de pagamento com interruptor, confirmação de segredo novo com a contagem,
  upload só do logo sem mexer nos e-mails;
- Interações Virtuais → Devoluções / Pagamentos a conferir; "Cancelar e abrir devolução" num pedido
  pago.

## 2. Produção (depois do deploy, à noite, com o dono)

1. Sondar o backend novo: `GET /api/virtuais/vitrine` → JSON; `GET /api/virtuais/pagamentos-a-conferir`
   sem sessão → 401 (rota nova = código novo no ar).
2. Card de pagamento: InfiniteTag `prime-dreams` já gravada (teste 0); **ligar o interruptor**.
3. IP do cliente (R8): reservar duas vezes de redes diferentes (Wi-Fi e 4G) na campanha de teste e ler
   no log a linha `[virtuais] origem: xff_itens=N publico=sim` — os dois `origem_hash` devem diferir.
4. Campanha de teste: `listada=false`, publicada, horários a mais de 2 h.
5. **Teste A de novo** (Pix R$ 1, caminho feliz) — regressão do contrato.
6. **Teste B — aviso perdido**: provado no verify (dublê), porque bloquear o aviso real em produção
   exigiria mexer no segredo com pedido aberto. Em produção, nos testes A e C, o log registra qual
   caminho decidiu (`origem=aviso|retorno|varredura`); anotar os dois. Se o retorno chegar antes do
   aviso em algum deles, o caminho do retorno está provado de verdade.
7. **Teste C — duas famílias**: reservar H com o telefone X, deixar a trava vencer sem pagar,
   reservar H com o telefone Y de outro aparelho, pagar o link de X → devolução `conflito_horario`
   em Devoluções; executar no app ("Devolver este Pix"); marcar concluída.
8. Limpeza: `limpar_venda_teste.py --pedido N --execute` (Shell, com OK); pausar a campanha de teste.
9. Só então: preços e horários reais do Papai Noel; publicar.

Regra durante a campanha (vai para a skill `manto-deploy`): nada de deploy entre 9h e 23h de
1º/11 a 25/12; depois de cada deploy, olhar "Pagamentos a conferir".

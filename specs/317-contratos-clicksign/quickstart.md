# Quickstart — Feature 317

## 1. Local (sem falar com a ClickSign)

```powershell
cd C:\tmp\mp317
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\317-contratos-clicksign\verify_317.py
```

Esperado: `26/26`, zero escape de rede (cenário 23). A trava `_suppress_clicksign()` vale para o `manto_local` mesmo com
`CLICKSIGN_ACCESS_TOKEN` no ambiente; só `CLICKSIGN_ALLOW_LOCAL_CALLS=true` libera (nunca no verify).

Tela: subir Flask + Vite do worktree (entrada temporária em `C:\Users\schim\.claude\launch.json`, ver memória 185b/299b)
e conferir com a skill `manto-conferir-tela`: Home (painel Contratos) como COMERCIAL e FINANCEIRO, a 375 px; evento com
contrato aguardando, assinado, vencido, sem contrato; menu ⋯ → "📝 Cobrar contrato" (texto copiado); faixa "A conferir";
diálogo "Ligar contrato da ClickSign".

## 2. Ensaio só leitura contra a ClickSign real (opcional, antes do merge)

`flask clicksign-sincronizar --desde 2026-06-01` **sem** `--aplicar`, com `CLICKSIGN_ALLOW_LOCAL_CALLS=true` e o token
local: mostra quantos ligaria / a conferir / artista / outros. Não grava (rollback) e só faz GET. Confere a cobertura do
leitor de nomes com os 235 envelopes reais.

## 3. Produção (depois do merge e do deploy, à noite)

1. Dono: `CLICKSIGN_ACCESS_TOKEN` no `manto-backend` (Render › Environment) — o token "Plataforma Manto".
2. Conferir a subida: log sem "integração ClickSign desligada"; `/api/` responde JSON.
3. Shell do Render: `MANTO_SEM_THREADS=1 flask clicksign-webhook --registrar https://<domínio>/api/webhooks/clicksign`
   (dry-run) → repetir com `--aplicar`. Confere `--listar`.
4. `MANTO_SEM_THREADS=1 flask clicksign-sincronizar --desde 2026-06-01` (dry-run) → ler os números com o dono →
   `--aplicar`.
5. Ponta a ponta: gerar um contrato de teste num fluxo, ver em ≤ 5 min "Aguardando assinatura" no evento de teste, assinar,
   ver "Assinado" + PDF anexado. Excluir o evento de teste.
6. Avisar a comercial (texto no `docs/03`).

## 4. Desligar

Apagar `CLICKSIGN_ACCESS_TOKEN` no Render (a integração some sem quebrar tela) e `flask clicksign-webhook --remover <id>
--aplicar`. Os dados gravados ficam.

# Quickstart — Upload e Gestão de Anexos do Evento (153)

## Rodar localmente

```powershell
.\scripts\db\run-local.ps1        # backend Flask contra manto_local
npm run dev:internal              # frontend (proxy Vite /api -> Flask), noutro terminal
```

Abra `/events/<id>` de um evento existente (tela React) logado como usuário com papel
Comercial/Financeiro/SUPERADMIN para ver todos os blocos novos.

## Roteiro manual

1. **Nota fiscal**: na seção "Notas fiscais" (nova), anexar um PDF com valor e data → aparece
   na lista com link "Abrir".
2. **Contrato**: seção "Contratos" (nova, dados já vinham da API mas não eram exibidos) —
   anexar um arquivo → aparece na lista; como SUPERADMIN, marcar "assinado" e depois excluir.
3. **Pagamento**: seção "Pagamentos" — adicionar comprovante com valor → link de download
   aparece ao lado do valor (antes só mostrava o valor); como SUPERADMIN, editar o valor e
   excluir.
4. **Reembolso**: seção "Reembolsos" — registrar um novo com comprovante do gasto → aparece
   pendente com link; marcar como cobrado anexando o comprovante de recebimento → vira
   "cobrado"; como SUPERADMIN, excluir.
5. **Observação com imagem**: seção "Observações" — escolher tipo "Imagem", anexar um arquivo
   → aparece a miniatura na lista, igual a uma observação de imagem criada pela tela antiga.
6. **Paridade Jinja**: repita os passos 1-5 na tela antiga (`/events/<id>`, form HTML) em outro
   evento e confira que nada mudou de comportamento.

## Verificação automatizada

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_153_upload_anexos.py
```

Cobre os 5 fluxos por paridade API×Jinja (multipart no test client via `data={...},
content_type="multipart/form-data"`), os limites de tamanho, os gates de SUPERADMIN, e a
refatoração de `_save_bounded_upload` (garante que os três `_handle_*` do Jinja continuam
salvando exatamente como antes).

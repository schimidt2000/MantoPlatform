# Quickstart: verificar a feature 181 localmente

1. **Backend** — rodar apontando para a cópia local (Postgres real):
   ```powershell
   .\scripts\db\run-local.ps1
   ```
2. **Frontend (staff)** em outro terminal:
   ```powershell
   cd frontend
   npm run dev:internal
   ```
3. Acessar `http://localhost:5173/casting/avaliacoes` (ou porta configurada) logado como um
   usuário sem SUPERADMIN e confirmar:
   - Nenhum toggle de "modo anônimo total" aparece.
   - Toda autoria mostra "Anônimo".
   - Pills de período incluem "Última semana"; categoria; filtrar por data do evento/avaliação.
   - Grid de gráficos (tendência, distribuição, categoria, ranking) aparece preenchido.
   - Em janela larga (≥1440px), o conteúdo ocupa a largura total (sem coluna estreita central).
4. Repetir logado como SUPERADMIN e confirmar que o toggle aparece e funciona (liga/desliga sem
   recarregar a página).
5. Checagem de tipos e build:
   ```powershell
   cd frontend\apps\internal
   npx tsc --noEmit
   npm run build
   ```
6. Verificação funcional automatizada (test client contra `manto_local`): script dedicado em
   `scripts/db/verify_181_avaliacoes.py` (criado durante `/speckit-implement`), cobrindo:
   - `GET /api/ratings?period=7d` retorna recorte de 7 dias com `recorte_label` contendo
     "última semana".
   - Usuário sem SUPERADMIN: `show_authors=false`, `is_superadmin=false`,
     `POST /api/ratings/modo-anonimo` retorna 403.
   - Usuário SUPERADMIN: `is_superadmin=true`; ao desativar `fully_anonymous`,
     `show_authors=true` e nomes reais aparecem; ao ativar, `show_authors=false` mesmo para o
     SUPERADMIN.

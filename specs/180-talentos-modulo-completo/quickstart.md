# Quickstart — Verificação da Reestruturação do Módulo de Talentos

## Pré-requisitos

1. Cópia local do banco real atualizada e migrada:
   ```powershell
   .\scripts\db\refresh-local-db.ps1
   python -m flask db upgrade
   ```
2. Backend rodando contra `manto_local`:
   ```powershell
   .\scripts\db\run-local.ps1
   ```
3. Frontend instalado (uma vez):
   ```powershell
   cd frontend; npm install
   ```

## Rodar em desenvolvimento

```powershell
cd frontend
npm run dev:internal
```

Acessar `http://localhost:5173/talents` (proxy Vite `/api` → Flask local).

## Roteiro manual de verificação

1. **Filtros**: abrir `/talents`, abrir o painel de filtros avançados, marcar 3+ critérios em
   categorias diferentes (ex.: Raça + Tamanho + Passaporte), clicar "Filtrar" — confirmar que só
   aplica ao clicar, não a cada seleção. Confirmar o checkbox "Já trabalhou com a Manto" está
   dentro do painel, não na barra principal.
2. **Grid**: redimensionar para ≥1440px — confirmar 5-6 colunas; cada card mostra o badge de
   medidas (altura • tamanho • calçado) sempre visível.
3. **Perfil — leitura**: abrir um talento qualquer. Confirmar zero controles de upload/edição
   visíveis. Confirmar os 4 KPIs do histórico, tabela de eventos, e a nova seção "Avaliações e
   Notas" (com estado vazio se o talento não tiver avaliações).
4. **Perfil — pendente**: abrir um talento com `status=pending` — confirmar painel de
   aprovação/rejeição no topo.
5. **Perfil — edição**: com um usuário CASTING/SUPERADMIN, clicar "Editar". Confirmar que os
   campos de escolha fechada (tamanho, calçado, passaporte) viram select/checkbox fechados, os
   uploads aparecem, e CPF só é editável se SUPERADMIN. Salvar e confirmar retorno automático ao
   modo leitura com os dados atualizados.
6. **Rota antiga**: acessar diretamente `/talents/123/edit` — confirmar redirect para
   `/talents/123?edit=1` já em modo edição.

## Verificação funcional automatizada (backend)

Seguir o padrão do projeto — script com Flask test client contra `manto_local`, requests fora de
`app_context`, cobrindo:
- `GET /api/talents/directory?height_op=eq&height_value=<cm>` retorna só talentos com aquela
  altura exata.
- `GET /api/talents/<id>` inclui `history.last_event` correto (ou `null` sem histórico).
- `GET /api/talents/<id>/ratings` retorna `received`/`given` corretos e respeita
  `show_authors`/modo anônimo para um usuário não-SUPERADMIN.
- `GET /api/talents/character-suggestions?q=...` — paridade com a resposta do endpoint Jinja
  para a mesma query.

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\python.exe scripts\db\verify_180_talentos.py
```

## Frontend — tipos e build

```powershell
cd frontend\apps\internal
npx tsc --noEmit
npm run build
```

## E2E — Playwright (novo)

Pré-requisitos: backend já rodando contra `manto_local` (passo 2 acima) em paralelo, e um usuário
CASTING/SUPERADMIN já existente na cópia local informado via variáveis de ambiente:

```powershell
cd frontend\apps\internal
npx playwright install --with-deps chromium   # uma vez
$env:E2E_USER_EMAIL = "seu-usuario-casting@manto.local"
$env:E2E_USER_PASSWORD = "sua-senha-local"
npm run e2e
```

Specs cobertos (ver `research.md` §8 para a estratégia de dados de teste):
- `e2e/talents-list.spec.ts`: login, aplicar filtros combinados, confirmar resultado e grid.
- `e2e/talents-detail.spec.ts`: criar um talento de teste via API, abrir o perfil, alternar
  leitura↔edição, editar um campo fechado, salvar, confirmar retorno ao modo leitura, depois
  remover o talento de teste (teardown).

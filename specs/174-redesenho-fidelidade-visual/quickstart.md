# Quickstart: Verificar a FASE B localmente

## Backend

```powershell
.\scripts\db\run-local.ps1
```

Verifica `GET /api/dashboard` (sem parâmetro e com `perf_range=30`) logado como cada papel
(CASTING, FIGURINO, FINANCEIRO, COMERCIAL, SUPERADMIN) e com "Ver como" ativo — confirmar que
`performance` só aparece para o SUPERADMIN real.

## Frontend

```powershell
cd frontend
npm run dev:internal
```

1. Abrir `/` (Dashboard) — conferir donuts de Casting/Figurino, painéis colapsáveis por setor
   com badges de urgência, e (como SUPERADMIN) o painel Performance com seletor de período.
2. Abrir `/agenda` — conferir grade mensal, navegação de mês, dia atual destacado, blocos
   coloridos por categoria; clicar num evento e confirmar navegação para o detalhe.
3. Abrir `/talents` — conferir mosaico de fotos grandes com badges de medida, aba
   Ativos/Pendentes, aprovar/rejeitar, busca/filtros.
4. Redimensionar para 375px em cada uma das 3 telas — sem overflow horizontal.
5. Amostrar 5 subpáginas (evento, figurino, financeiro, clientes, admin) e confirmar uso de
   `PageHeader`/`DenseCard` onde antes havia cabeçalho solto.

## Checagem de tipos e build

```powershell
cd frontend\apps\internal
npx tsc --noEmit
npm run build
```

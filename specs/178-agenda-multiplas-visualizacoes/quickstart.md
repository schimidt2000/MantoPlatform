# Quickstart: Agenda com múltiplas visualizações

## Rodar em desenvolvimento

```powershell
# Backend (sem mudanças nesta feature, mas precisa estar de pé para a API)
.\scripts\db\run-local.ps1

# Frontend — staff
cd frontend
npm run dev:internal
```

Acesse `http://localhost:5173/agenda` (ou porta configurada pelo Vite).

## Verificar manualmente

1. **Seletor de visão**: abrir `/agenda`, alternar Mês → Dia → Lista → Mês; confirmar que a
   data de referência não reseta a cada troca.
2. **Navegação**: em cada visão, testar ‹, "Hoje" e ›.
3. **Clique no dia (Mês)**: clicar no número de um dia com eventos e num dia vazio; confirmar
   que ambos abrem a visão Dia correta. Clicar num badge de evento deve ir direto para
   `/events/:id`, sem passar pela visão Dia.
4. **Visão Dia — overlap**: usar um dia com 2+ eventos em horários sobrepostos (via `manto_local`
   ou criando eventos de teste) e confirmar que os blocos aparecem lado a lado, legíveis.
5. **Visão Lista**: confirmar agrupamento por dia, ordem cronológica, e botão "Abrir" navegando
   corretamente.
6. **Responsividade**: redimensionar para 1920px+ (sem coluna central estreita) e para 320–375px
   (sem rolagem horizontal da página, texto legível) em cada visão.

## Checagens de tipo/build

```powershell
cd frontend/apps/internal
npx tsc --noEmit
npm run build
```

## Verificação visual (Playwright)

Rodar o app localmente e usar o Playwright MCP/CLI já disponível no ambiente para navegar até
`/agenda`, alternar as 3 visões e capturar screenshots em viewport desktop widescreen (1920×1080)
e mobile (375×812), conforme pedido pelo usuário antes do merge.

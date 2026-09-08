---
name: manto-conferir-tela
description: >
  Conferir uma tela React da Manto no Browser pane antes de declarar pronto (portão "tela aberta"
  da constituição). Use quando uma mudança toca UI, quando `tsc` está limpo mas a tela pode estar
  branca, ou quando o Browser pane "não reage" a input/clique (react-hook-form, Radix, Dialog que
  não fecha). Superfície pública sempre em viewport mobile.
---

# manto-conferir-tela — verificar UI de verdade

## Subir

- Backend: launch `manto-backend-local` (porta 5000) — sobe contra o `manto_local` com
  `MANTO_SEM_THREADS=1`. Frontend: `manto-internal` (5173), `manto-portal` (5174),
  `manto-public` (5175). Cada app precisa do SEU proxy de mídia no `vite.config.ts`
  (`/uploads`, `/catalogo/midia`, `/catalogo/og`, `/portal/photo`) — o proxy de um não vale para
  o outro.
- Tela atrás de login sem sessão: entry Vite temporária na raiz do app + cache do TanStack
  pré-carregado renderiza a tela real; sem `AppLayout`, então faltam 256px de sidebar na medição.
- Credenciais: a senha do SUPERADMIN local muda a cada verify — redefina antes (`set_password`).

## O que `tsc` não pega

- Componente que lê `data.campo_novo.x` de campo NOVO derruba a árvore inteira (tela branca)
  quando backend e bundle estão em versões diferentes — o estado normal por minutos em todo
  deploy. Tipar como opcional e sair com `null`.
- Grid com `minmax(0,1fr)` atrás de breakpoint estoura o celular: `[&>*]:min-w-0` no container;
  linha de botões `whitespace-nowrap` precisa de `flex-wrap`.
- `onError` de `<img>` não pega 404 vindo do cache do navegador — use `<Foto>` de `@manto/ui`.
- Rotas irmãs com o MESMO elemento não remontam o componente (`/novo` e `/:id/editar`): derive de
  `location.state` a cada render.

## Interagir pelo Browser pane

- `form_input` e clique em `<label>`/radio NÃO chegam ao react-hook-form: use o setter nativo do
  protótipo do input + `dispatchEvent(new Event('input', {bubbles: true}))` e `change`; submeta
  com `form.requestSubmit()`, não com `button.click()`.
- Triggers Radix (`Tabs`, `Select`, `DropdownMenu`) ignoram `.click()` programático: `read_page`
  + `computer` `left_click` por ref.
- Transição CSS congela na aba não composta: compare o `getComputedStyle` de um clone recém
  inserido ao lado do original.
- `Dialog` fechado não desmonta (exit do AnimatePresence sem rAF): `navigate(url, {force: true})`
  entre diálogos.
- Confira por estado derivado (`disabled`, `aria-invalid`, `[role="alert"]`), não pelo valor no
  DOM.
- O servidor Flask de dev serializa requisições: tela com 250 fotos deixa `img.complete` falso por
  dezenas de segundos — confira numa tela com poucas imagens.

## Mobile

`resize_window` preset mobile (375×812) e reload; sem rolagem horizontal de 320 a 430px
(`documentElement.scrollWidth` ≤ `clientWidth`); toque ≥ 44px; texto ≥ 12px; teclado virtual não
esconde a ação de envio.

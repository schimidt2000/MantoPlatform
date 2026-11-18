# Quickstart — validar a Feature 347

## 1. Verify

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim() -replace '/manto_local$', '/manto_347'; $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'; .\.venv\Scripts\python.exe specs/347-endereco-abre-no-mapa/verify_347.py
```

(`manto_347` = dump de 17/11 02h; o `manto_local` está sem a coluna da 344 — plan.md, Rastreamento de
complexidade.)

Esperado: todos os cenários `OK`, inclusive o que **deve falhar** (o montador ingênuo reprovado).
Contrato testado: [contracts/endereco-no-mapa.md](./contracts/endereco-no-mapa.md).

## 2. Typecheck

```powershell
cd frontend; npm run typecheck
```

## 3. Tela aberta (skill `manto-conferir-tela`, contra o `manto_local`)

App interno, logado como Superadmin, viewport 390×844 e depois tela larga:

1. Abrir um evento futuro com endereço → o endereço aparece com o ícone de local no cabeçalho e no
   "Local" de "Dados do evento".
2. Tocar no endereço → "Abrir endereço" com o endereço e Google Maps, Apple Mapas e Waze; conferir o
   `href` de cada link (endereço codificado) e `target="_blank"`.
3. Fechar por fora, pelo "Fechar" e por Esc → nenhum link seguido.
4. Abrir um evento **sem** endereço → nada tocável; "Local" = "—".

Portal do Artista, logado como um talento com evento futuro e convite pendente, viewport 375×812:

5. "Próximos eventos" → endereço tocável com alvo ≥ 44px; escolha abre igual ao app interno.
6. "Convites" → idem.
7. 320, 375 e 430px: sem rolagem horizontal (`document.documentElement.scrollWidth <= innerWidth`).
8. Tema escuro: a escolha e o endereço legíveis.

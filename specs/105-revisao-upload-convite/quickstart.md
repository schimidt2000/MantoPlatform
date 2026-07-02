# Quickstart — Revisão 105

## Rodar

```powershell
.\scripts\db\run-local.ps1   # app contra manto_local (Postgres) — sem migration nesta feature
```

## Roteiro de verificação

### US1 — Popup de histórico (P1)

1. Abrir qualquer material (`/revisao/<id>/asset/<id>`) → NENHUM popup sobreposto ao carregar.
2. Tocar no badge de versão (`v1 ▾`) → popup abre; fechar no ✕ → fecha; abrir de novo e
   clicar fora do cartão → fecha. Repetir 3× — consistente.

### US2 — Progresso de upload (P2)

1. `/revisao/novo`: preencher título, escolher um vídeo grande (100+ MB), criar → barra de
   progresso com % e "X MB de Y MB" subindo de verdade; botão desabilitado; campos bloqueados.
2. Ao terminar → cai na tela do espaço com flash "Espaço criado…" visível e destaque do
   convite (`?novo=1`).
3. DevTools → Network offline no meio do envio → mensagem de erro amigável; formulário
   editável com título/descrição/arquivos ainda preenchidos.
4. Criar espaço SEM arquivos → segue fluxo normal (sem barra), sem regressão.
5. Na tela do material: "Enviar nova versão" com arquivo grande → mesma barra de progresso.
6. Na tela do espaço: "Adicionar materiais" → mesma barra.

### US3 — Copiar convite (P3)

1. Na tela do espaço recém-criado: painel de destaque + botão "Copiar convite".
2. Tocar → botão vira "✓ Copiado!"; colar num editor → mensagem com título entre aspas e
   link `https://.../revisao/<id>` corretos (emoji/acentos preservados).
3. Acessar o link logado como revisor selecionado → cai no espaço; como usuário sem acesso →
   403 (permissões inalteradas).

## Portões

```powershell
ruff check app/revisao/ app/static/
ruff format app/revisao/ --check   # (arquivos tocados — estilo do projeto preservado)
```

Verificação automatizada: script com test client (requests FORA de app_context — ver memória
flask-test-client-app-context-leak) cobrindo: JSON mode das 3 rotas (redirect/erro 400),
fluxo tradicional intacto (302), `?novo=1` no redirect, permissões inalteradas.

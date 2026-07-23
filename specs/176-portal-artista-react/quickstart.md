# Quickstart: Portal do Artista — App React (fatia 1)

## Rodar localmente

```powershell
# Backend, apontando para manto_local (Postgres) — nunca o SQLite vazio
.\scripts\db\run-local.ps1

# Frontend (Portal do Artista)
cd frontend; npm run dev --workspace=apps/portal
```

Acessar o app em `http://localhost:5174` (porta já reservada no scaffold).

## Verificação funcional (obrigatória antes do merge)

Script com test client Flask contra `manto_local`, requests fora de `app.app_context()`,
cobrindo:

1. `POST /api/portal/auth/login` — 200 com talento válido, 401 com senha errada,
   `must_redirect_to_classic=true` quando `must_change_password`/termos pendentes.
2. `GET /api/portal/auth/me` — 401 sem sessão, 200 com sessão.
3. `POST /api/portal/auth/logout` — encerra a sessão (próxima chamada a `me` volta 401).
4. `GET /api/portal/agenda` — separação correta entre pendentes/futuros/histórico; cachê e
   situação de pagamento no histórico; aviso de alteração não reconhecida.
5. `POST /api/portal/invites/<id>/accept|reject` — muda `invite_status`; 404 para role de outro
   talento; idempotente ao repetir.
6. `POST /api/portal/roles/<id>/ack-change` — limpa o aviso de alteração.
7. `GET /api/portal/events/<id>/figurino` — 200 com ficha(s) quando escalado, 403 quando não
   escalado, `sheets: []` quando não há ficha ainda.
8. `POST /api/portal/profile/photo` e `/document` — sucesso substitui o arquivo anterior; 400
   para extensão/tamanho inválido.
9. Paridade: as mesmas ações via rota Jinja legada (`/portal/invites/<id>/accept` etc.)
   continuam funcionando sem regressão.

## Frontend

```powershell
cd frontend/apps/portal
npx tsc --noEmit
npm run build
```

Conferir manualmente em `npm run dev`: login → Agenda → Convites (aceitar/recusar) → Ficha de
Figurino → Fotos/Documentos — **obrigatoriamente em viewport mobile (320px e 375px)** antes de
"pronto" (Princípio VIII, não-negociável para esta superfície).

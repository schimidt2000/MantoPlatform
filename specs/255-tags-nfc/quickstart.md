# Quickstart — Feature 255: Tags NFC

Roteiro de validação ponta a ponta. Referências: [contracts/nfc-api.md](./contracts/nfc-api.md), [data-model.md](./data-model.md).

## Pré-requisitos

- Cópia local do banco real: `.\scripts\db\run-local.ps1` (Postgres `manto_local` — **nunca** SQLite).
- Backend: `FLASK_ENV=development` + app rodando em `localhost:5000` (trava de ambiente ativa — o espelho tem credenciais reais de Google/e-mail).
- Migration aplicada: `flask db upgrade` (head esperado: a migration desta feature).

## Verificação automatizada (obrigatória antes de cada commit relevante)

```bash
python scripts/verify_255_nfc.py
```

O script (padrão `verify_*` do projeto: login só pela API, imprime PASS/FAIL por cenário):
1. Login SUPERADMIN → habilita `nfc_prefix="01"` num item do acervo de teste.
2. Cria evento SHOW + presente 3D do item (quantity 2) → espera 2 tags novas `(event, item)`, códigos `01-XXXXXX` únicos, `sequence` contínua por item.
3. Aumenta quantity para 3 → espera +1 tag (total 3); reduz para 1 → espera ainda 3 (nunca apaga).
4. `POST /api/3d/nfc/lote` (quantity 2, sem evento) → 2 tags com `event_id null`.
5. `PATCH` associa evento a uma tag avulsa → `client_name` do contratante aparece na lista.
6. `GET /api/nfc/<code>` sem sessão → 200 com `product.name` + `campaign: null`; `access_count` incrementa.
7. `PATCH is_active=false` → `GET /api/nfc/<code>` devolve `product: null` (mesmo shape); código inventado idem (SC-006).
8. Item sem `nfc_prefix` + presente novo → zero tags (não-regressão do fluxo atual).
9. Limpeza: desfaz os registros de teste criados.

## Typecheck e build

```bash
cd frontend/apps/public && npx tsc --noEmit
```

```bash
cd frontend/apps/internal && npx tsc --noEmit
```

## Verificação visual (browser)

1. **Página pública** (dev: `npm run dev:public`, raiz em `localhost:5175`): abrir `/nfc/<code válido>` em viewport 375×812 →
   - animação de portal abre (e com reduced motion: aparece sem animação);
   - copy de boas-vindas + link do Instagram (handle confirmado com o usuário);
   - foto/nome do produto visíveis; sem rolagem horizontal em 320–430px; toque ≥ 44px.
   - `/nfc/QUALQUERCOISA` → mesma página em modo genérico, nunca erro.
2. **Admin** (`npm run dev:internal`): `/3d/tags` →
   - lista com **nº sequencial em destaque**, código, produto, evento, cliente, situação, copiar link;
   - gerar lote → botão com loading, toast de sucesso, linhas novas na lista;
   - associar evento via combobox pesquisável; ativar/desativar com confirmação visual;
   - nenhuma ação de exclusão em lugar algum.
3. **Produção (pós-deploy)**: `app.mantoproducoes.com.br/nfc/<code de teste>` abre sem login no celular; gravar uma tag física de teste e encostar o iPhone.

## Resultado esperado

Todos os cenários do verify em PASS, `tsc` limpo nos dois apps, página pública aprovada em mobile — só então marcar os portões de qualidade da constituição e atualizar `docs/01`, `docs/02` e `docs/03`.

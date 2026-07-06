# Data Model — Comissão EducaManto (109)

## Colunas novas

### `site_settings.educamanto_seller_id`

| Atributo | Valor |
|---|---|
| Tipo | Integer, FK `users.id` |
| Nullable | sim (`NULL` = sem responsável ⇒ comissão EDU segue regra comum) |
| UI | select de usuários na tela de configurações do admin |
| Backfill | `id` do usuário com email `gabriel@mantoproducoes.com.br` (no-op se não existir) |

### `commission_payments.payable_from`

| Atributo | Valor |
|---|---|
| Tipo | Date |
| Nullable | sim (`NULL` = comissão comum; ciclo pela `sale_date`) |
| Semântica | data da realização do evento (data de `start_at`); a comissão entra na planilha no mês seguinte a esta data (vencimento dia 5) |
| Escrita | `_sync_commission_payment` (EDU ⇒ data do evento; comum ⇒ `NULL`); estorno copia do original |
| Leitura | `_build_commission_items`: janela por `COALESCE(payable_from, sale_date)` |

## Property nova (sem coluna)

`CalendarEvent.is_educamanto` → `bool(self.title)` e título (upper) começa com
`EDUCAMANTO_TITLE_PREFIX` (`"(EDU"`). Query SQL equivalente: `title.ilike("(EDU%")`.

## Estados da comissão EDU

```text
venda registrada em evento "(EDU…"
        │ (responsável configurado e receives_commission)
        ▼
CommissionPayment(seller_id=responsável, sale_date=venda, payable_from=data do evento,
                  status=a_pagar)
        │ evento remarcado / taxa alterada / título editado → _resync_pending_commissions
        │ atualiza amount, seller_id, payable_from (só linhas a_pagar)
        ▼
planilha de pagamentos do mês seguinte a payable_from (dia 5) → pago
        │ evento cancelado após pago → estorno (amount negativo, payable_from copiado)
```

Sem responsável configurado ⇒ `payable_from = NULL` e beneficiário = vendedor (regra comum).

## Migration (manual — autogenerate quebrado)

```python
revision = "e5f6a7b8c9d0"
down_revision = "c3d4e5f6a7b8"

def upgrade():
    op.add_column("site_settings", sa.Column(
        "educamanto_seller_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("commission_payments", sa.Column(
        "payable_from", sa.Date(), nullable=True))
    op.execute(
        "UPDATE site_settings SET educamanto_seller_id = "
        "(SELECT id FROM users WHERE email = 'gabriel@mantoproducoes.com.br' LIMIT 1)"
    )

def downgrade():
    op.drop_column("commission_payments", "payable_from")
    op.drop_column("site_settings", "educamanto_seller_id")
```

Revision `e5f6a7b8c9d0` verificada como única em `migrations/versions/` (lição da 108:
colisão de id com migration antiga).

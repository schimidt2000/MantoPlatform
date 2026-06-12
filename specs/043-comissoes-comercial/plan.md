# Implementation Plan: Comissões visíveis para o comercial (somente leitura)

**Branch**: `043-comissoes-comercial` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

## Summary

Sem migration. Três pontos:

1. **Rota `comissoes`** (`app/financeiro/routes.py`): decorator passa de `require_financeiro` para
   `require_vendas`; computa `can_manage = _has_role(FINANCEIRO, SUPERADMIN)`; quando
   `not can_manage`, filtra `entries` e `estornos` por `seller_id == current_user.id`; passa
   `can_manage` ao template. `set_commission_status` e bulk continuam `require_financeiro`
   (já são rotas separadas — sem mudança).
2. **Template `financeiro/comissoes.html`**: coluna/botões de ação e "Marcar processado" só com
   `can_manage`; botão "← Financeiro" do topo só com `can_manage`; subtítulo "Suas comissões"
   quando restrito.
3. **`base.html`**: mover o link "Comissões" do bloco FINANCEIRO para o bloco
   COMERCIAL/FINANCEIRO/SUPERADMIN (junto de Pipeline de Vendas).

## Constitution Check
- **I. Reutilizar** ✅ — `require_vendas` e `_has_role` já existem; mesma tela para os 3 perfis.
- **IV. Não quebrar** ✅ — visão do financeiro/superadmin idêntica (can_manage=True).
- **V. UI/UX** ✅ — comercial vê tela limpa sem ações; estado vazio já existe.

## Verificação
- ruff (sem novos) + boot.
- Test client: comercial (user 3) vê apenas comissões próprias (seed com 2 vendedores), sem
  botões de ação ("Marcar pago"/"Reverter"/"Marcar processado" ausentes); POST set-status como
  comercial → 403 e nada muda; financeiro/superadmin (user 2) vê tudo com botões; sidebar do
  comercial tem "Comissões".

## Project Structure
```text
app/financeiro/routes.py             # comissoes: require_vendas + filtro por vendedor
app/templates/financeiro/comissoes.html  # can_manage
app/templates/base.html              # link Comissões p/ comercial
```

## Fora de escopo
- Mudar ações/fluxo do financeiro; relatório por período para vendedora (futuro).

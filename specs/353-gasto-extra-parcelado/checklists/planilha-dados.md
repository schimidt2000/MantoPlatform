# Checklist de requisitos: Planilha e integridade das parcelas — 353

**Purpose**: testar se spec e plano definem sem ambiguidade como a parcela vive na Planilha e como o valor do gasto
fica íntegro. **Created**: 2026-11-17 · **Profundidade**: padrão · **Público**: revisor do PR
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

## Planilha de Pagamentos

- [x] CHK001 - Está definido em que mês a parcela aparece (a data dela, não a do gasto)? [Clarity, Spec §FR-005, História 2]
- [x] CHK002 - Está definido que o gasto parcelado NÃO aparece também como item inteiro? [Completeness, Data-model §Invariantes 4]
- [x] CHK003 - Os atrasados de meses anteriores (331) estão cobertos para a parcela? [Coverage, Spec §FR-006, Plan §3]
- [x] CHK004 - A ação em lote está coberta, com um identificador que o lote atual aceita (inteiro por tipo)? [Coverage, Plan §3, Research R2]
- [x] CHK005 - O risco do tipo desconhecido cair no cachê está tratado no plano? [Edge Case, Plan §Restrições, Research R2]
- [x] CHK006 - A identificação "Parcela N de M" está definida (numeração por data)? [Clarity, Spec §FR-005, Plan §2.5]

## Valor e situação do gasto

- [x] CHK007 - A relação total × parcelas está definida sem margem (soma exata, calculada)? [Clarity, Spec §FR-002]
- [x] CHK008 - Estão listados todos os que reescrevem o valor do gasto e por isso não podem parcelar? [Completeness, Research R5, Contracts §Erros]
- [x] CHK009 - A situação do gasto derivada das parcelas está definida para os três estados? [Clarity, Spec §FR-007]
- [x] CHK010 - Está definido o que o PATCH faz quando o corpo não traz parcelas (bundle antigo)? [Edge Case, Contracts §PATCH]
- [x] CHK011 - Está definido o que acontece ao desligar parcelas com parcela paga? [Edge Case, Spec §Casos de borda]
- [x] CHK012 - A DRE está explicitamente fora da mudança (competência pela "Data do gasto")? [Consistency, Spec §FR-004, SC-003]

## Edição e travas

- [x] CHK013 - A trava da parcela paga cobre alterar data, alterar valor e remover? [Completeness, Spec §FR-008]
- [x] CHK014 - Está definido que parcela desmarcada na Planilha volta a ser editável? [Coverage, Spec §Casos de borda]
- [x] CHK015 - Os erros de parcela apontam a parcela certa (índice) sem apagar o digitado? [Clarity, Spec §FR-011, Contracts §Erros]
- [x] CHK016 - O limite de parcelas está quantificado? [Measurability, Spec §FR-001]

## RBAC

- [x] CHK017 - O tipo novo herda o gate da Planilha (Financeiro/Superadmin) e há cenário que deve falhar? [Coverage, Spec §RBAC, Verificação #10]

## Notas

- Rodada única: 17 itens atendidos. O Jinja de pagamentos (não servido em produção) segue mostrando o parcelado
  inteiro: registrado no plano como risco aceito.

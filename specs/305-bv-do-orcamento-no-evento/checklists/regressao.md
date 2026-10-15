# Checklist: o que não pode quebrar — qualidade dos requisitos

**Purpose**: portão antes do `/speckit-tasks` — a spec e o plano nomeiam o que existe hoje nos mesmos
caminhos e dizem que continua igual?
**Created**: 2026-10-14
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

- [x] CHK001 A criação de evento sem orçamento e de orçamento sem acréscimos está declarada como "igual a hoje"? [Spec verify 23, 24]
- [x] CHK002 A autoria da 301 no vínculo (409/404) está declarada como anterior à recusa do PIX? [Spec §RBAC; contracts/api.md]
- [x] CHK003 A recusa da 215b (taxa e vendedor) está declarada como anterior à regravação do BV? [Plan "Ordem"; Research R9]
- [x] CHK004 O 267c (lote não mexe em linha paga) está declarado como intocado? [Plan "Ordem"; data-model `commission_payments`]
- [x] CHK005 A Planilha, a DRE e a base da comissão estão declaradas sem mudança de código, só com dado novo? [Spec FR-026]
- [x] CHK006 O gêmeo Jinja tem o mesmo comportamento definido (recusa, rollback, aviso) e não ganha template novo? [Research R5, R9, R11]
- [x] CHK007 Satélite e cancelado têm comportamento definido em cada porta? [Spec casos de borda; Research R7, R9]
- [x] CHK008 A lista de verifies de regressão está nomeada (273, 267b, 301, 215b, 267c, 267 e os locais 249/251/210)? [Spec verify 27; quickstart §2]
- [x] CHK009 O passado está definido de forma testável (os 3 eventos, nenhuma comissão paga reescrita)? [Spec SC-008; verify 25, 45]
- [x] CHK010 As docstrings e textos que passam a mentir estão listados para o fecho? [Plan fase 10]

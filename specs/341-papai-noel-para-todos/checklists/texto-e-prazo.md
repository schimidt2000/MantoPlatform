<!-- ADAPTADO PARA A MANTO (2026-09-08) -->
# Texto e prazo Checklist: 341

**Propósito**: testar se a spec descreve por completo o texto sem idade e o prazo do vídeo
**Created**: 2026-11-10
**Feature**: [spec.md](../spec.md)

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_341.py` verde contra `manto_340`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [ ] CHK005 Migration manual criada e aplicada no banco de verificação
- [ ] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` (não toca)
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado (nenhum novo)
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`; `docs/04`
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Texto novo revisado pelo Princípio XV, lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Qualidade dos requisitos

- [x] CHK012 Todos os lugares que a família lê estão listados (site, ficha, pedido, e-mails, erros)? [Completeness, Spec §FR-001–FR-005]
- [x] CHK013 Está claro que a cartinha continua, condicionada à criança? [Clarity, Spec §FR-001, §FR-004]
- [x] CHK014 Está dito o que NÃO muda (chaves `child_*`)? [Consistency, Spec §FR-007]
- [x] CHK015 A regra do prazo cobre data futura, data passada e sem data? [Coverage, Spec §FR-009, H2]
- [x] CHK016 Está definido de onde o e-mail tira a data? [Clarity, Spec §FR-011, plan "Decisões"]
- [x] CHK017 O campo novo é opcional no React (deploy em duas versões)? [Edge Case, Spec §Casos de borda]
- [x] CHK018 As telas internas entram no escopo de forma explícita? [Completeness, Spec §FR-006]
- [x] CHK019 Há cenário que deve falhar (data inválida)? [Measurability, Spec §Verificação #7]

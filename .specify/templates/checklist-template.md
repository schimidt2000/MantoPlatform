<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# [TIPO DE CHECKLIST] Checklist: [FEATURE]

**Propósito**: [o que este checklist cobre]
**Created**: [AAAA-MM-DD]
**Feature**: [link para spec.md]

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e das tarefas.

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_NNN.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [ ] CHK005 Migration manual criada e aplicada no `manto_local` se `models.py` mudou; destrutiva ensaiada
- [ ] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml`
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

<!--
  ============================================================================
  Os itens abaixo são EXEMPLO. O /speckit-checklist substitui por itens reais a partir do
  pedido do usuário, dos requisitos da spec, do contexto do plano e das tarefas.
  NÃO deixe exemplos no checklist gerado. Mantenha o bloco "Portões da Manto" acima.
  ============================================================================
-->

## [Categoria 1]

- [ ] CHK011 Primeiro item, com ação clara
- [ ] CHK012 Segundo item

## [Categoria 2]

- [ ] CHK013 Item com critério específico

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência

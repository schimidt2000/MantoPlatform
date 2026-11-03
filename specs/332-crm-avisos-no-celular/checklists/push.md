<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist de avisos no celular: 332

**Propósito**: testar a qualidade dos requisitos de destino, ruído e falha do aviso no celular.
**Created**: 2026-11-03
**Feature**: [spec.md](../spec.md)

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_332.py` verde (e 325/328/330), com conexão separada e os cenários que falham
- [ ] CHK004 Tela aberta de verdade, em desktop e em 375×812
- [ ] CHK005 Migration manual criada e aplicada no `manto_local`
- [ ] CHK006 `scripts/validar_startcommand.py` — não se aplica
- [ ] CHK007 Gate de RBAC em todo endpoint novo e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Texto novo revisado pelo Princípio XV
- [ ] CHK011 Antes de "em produção": git limpo, `docs/03` batendo, sonda `/api/`

## Destino e ruído

- [x] CHK012 O destinatário do aviso de mensagem está definido nos dois casos (com e sem responsável) e no do responsável sem acesso? [Clarity, Spec §FR-003]
- [x] CHK013 Está definido o que NÃO toca (eco, reação, reenvio)? [Coverage, Spec §FR-003, SC-003]
- [x] CHK014 Está definido como várias mensagens da mesma conversa aparecem (substituem)? [Clarity, Spec §FR-004]
- [x] CHK015 O horário (a qualquer hora) e a relação com o alerta de 15 min estão explícitos? [Consistency, Clarifications]

## Falha e ambiente

- [x] CHK016 A falha do serviço de avisos e o aparelho que não existe mais têm comportamento definido? [Edge Case, Spec §FR-006/FR-007]
- [x] CHK017 O ambiente local e a falta de chaves estão definidos? [Completeness, Spec §FR-008/FR-009]
- [x] CHK018 O iPhone fora da Tela de Início, a permissão negada e o navegador sem suporte têm texto? [Coverage, Spec §Casos de borda]
- [x] CHK019 Está definido que o aviso nunca sai antes de o fato ser gravado? [Clarity, Spec §FR-006]

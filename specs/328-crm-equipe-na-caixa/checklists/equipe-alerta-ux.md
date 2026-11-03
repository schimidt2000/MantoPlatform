<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist de concorrência, alerta e UX: 328 Conversas em equipe

**Propósito**: testar a qualidade dos requisitos (não a implementação) em três frentes: a concorrência do
responsável, a regra de espera e alerta (horário de São Paulo) e a UX da caixa no celular (nota, respostas
rápidas, áudio).
**Created**: 2026-11-03
**Feature**: [spec.md](../spec.md)

**Nota**: profundidade padrão, para revisão. Os itens marcados foram avaliados na geração; o que faltava foi
corrigido na spec na mesma rodada (FR-012 com o limite e o microfone negado, FR-017 para o celular, FR-018 para
o aviso de transferência).

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_328.py` verde contra `manto_local`, conexão separada, cenários que falham
- [ ] CHK004 Tela aberta de verdade, em desktop e em 375×812
- [ ] CHK005 Migration manual criada e aplicada no `manto_local`
- [ ] CHK006 `scripts/validar_startcommand.py` — não se aplica
- [ ] CHK007 Gate de RBAC em todo endpoint novo e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única (`docs/01`, `02`, `03`; `04`, `05` se aplicável)
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Texto novo revisado pelo Princípio XV
- [ ] CHK011 Antes de "em produção": git limpo, `docs/03` batendo, sonda `/api/`

## Concorrência do responsável

- [x] CHK012 O que acontece quando duas pessoas respondem quase juntas uma conversa sem dono está definido (fica a primeira)? [Clarity, Spec §FR-002, Research §R1]
- [x] CHK013 A corrida do "Assumir" tem um resultado definido para quem perde, com o texto? [Completeness, Spec §FR-003, Contrato]
- [x] CHK014 Está definido quem pode ser destino de uma transferência e a recusa para quem não pode? [Clarity, Spec §FR-004]
- [x] CHK015 O caso do responsável que perdeu o papel ou foi desativado está tratado, para assumir e para o alerta? [Edge Case, Spec §Casos de borda]
- [x] CHK016 Está definido que o eco do celular não atribui, e por quê? [Clarity, Spec §FR-002, US1/AC5]
- [x] CHK017 A pessoa que recebe uma transferência é avisada? [Gap → resolvido, Spec §FR-018]

## Regra de espera e alerta

- [x] CHK018 O início da espera está definido sem ambiguidade (a primeira sem resposta, várias mensagens seguidas)? [Clarity, Spec §FR-006, Casos de borda]
- [x] CHK019 Está definido o que encerra a espera (envio aceito, eco, modelo) e o que não encerra (envio que falhou)? [Completeness, Spec §FR-006, Casos de borda]
- [x] CHK020 O horário está definido com fuso explícito e fronteira (9h ≤ hora < 21h, São Paulo)? [Clarity, Spec §FR-007, Casos de borda "Fronteira das 21h"]
- [x] CHK021 O "um aviso por espera" tem uma identidade definida? [Measurability, Spec §FR-007, Data model]
- [x] CHK022 O destinatário do alerta está definido nos dois casos (com e sem responsável)? [Coverage, Spec §FR-007]
- [x] CHK023 Está definido o que acontece com o aviso depois que alguém responde? [Completeness, Spec §FR-008]
- [x] CHK024 O tempo máximo entre completar 15 min e o aviso sair está quantificado? [Measurability, Spec §SC-002, Premissas]

## UX da caixa no celular (nota, respostas rápidas, áudio)

- [x] CHK025 A nota interna é visualmente distinguível da mensagem e está dito que nunca sai para a cliente? [Clarity, Spec §FR-009, US3]
- [x] CHK026 Está definido se inserir uma resposta rápida envia ou só preenche o campo? [Clarity, Spec §FR-011]
- [x] CHK027 O comportamento de `{nome}` sem nome de contato está definido? [Edge Case, Spec §Casos de borda]
- [x] CHK028 As regras de unicidade (título e atalho) e o formato do atalho estão especificados com o texto da recusa? [Completeness, Spec §FR-010, Contrato]
- [x] CHK029 A gravação tem limite de duração e um caminho para o microfone negado? [Gap → resolvido, Spec §FR-012]
- [x] CHK030 Os formatos por navegador e a conversão do webm estão definidos, inclusive a falha da conversão? [Coverage, Spec §FR-013, Premissas]
- [x] CHK031 Os alvos de toque e a largura da lista no celular estão especificados? [Gap → resolvido, Spec §FR-017]
- [x] CHK032 A exclusão de resposta rápida pede confirmação? [Consistency, Constituição V, Spec §US4]

## Notas

- O horário 9h–21h é constante (Premissas); se o dono pedir para configurar, vira requisito novo.

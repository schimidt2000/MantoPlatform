<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Deploy e confiabilidade do caminho do dinheiro Checklist: 340 — caixa de avisos

**Propósito**: testar se a spec e o plano descrevem por completo, sem ambiguidade, o receptor, o
dreno, o `render.yaml`, a segurança do segredo e a documentação operacional
**Created**: 2026-11-10
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e das tarefas. Profundidade
padrão; público: revisor do merge. Os itens de qualidade foram avaliados na hora; os que acusaram
lacuna levaram a correção da spec (anotada na linha).

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [x] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [x] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [x] CHK003 `verify_340.py` verde contra `manto_340`, escrita conferida por conexão separada, um cenário que falha
- [x] CHK004 Tela aberta de verdade; superfície pública em viewport mobile
- [x] CHK005 Migration manual criada e aplicada no `manto_340` se `models.py` mudou; destrutiva ensaiada
- [x] CHK006 `scripts/validar_startcommand.py` verde se tocou o `startCommand` do `render.yaml`
- [x] CHK007 Gate de RBAC declarado em todo endpoint novo/alterado e linha em `docs/01` §4.3
- [x] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03` sempre; `00`/`04`/`05` se aplicável
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [x] CHK010 Texto novo ou alterado (tela, e-mail, PDF, erro da API) revisado pelo Princípio XV: tom da superfície e glossário, lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Completude dos requisitos

- [x] CHK012 Há código de resposta definido para cada desfecho do receptor (guardado, segredo errado, corpo grande, excesso de chamadas, banco fora, caminho desconhecido)? [Completeness, Spec §FR-003–FR-007, contracts/manto-avisos.md]
- [x] CHK013 Está definido o que acontece quando o banco falha **na conferência do segredo**, antes de guardar? [Gap, Spec §FR-006] — *corrigido: FR-006 passou a cobrir "conferir ou guardar"*
- [x] CHK014 Está definido o destino da linha da caixa quando o registro na fila da 310 dá certo mas a decisão (`processar_aviso`) falha? [Gap, Spec §FR-012] — *corrigido: FR-012 diz que a caixa responde só até o registro; a decisão segue na varredura da 310*
- [x] CHK015 A retenção da caixa está definida ou explicitamente excluída? [Gap, Spec §Fora de escopo] — *corrigido: limpeza da caixa entrou em Fora de escopo*
- [x] CHK016 A ordem "confirmar a URL do receptor antes de ligar a loja" está documentada? [Completeness, Spec §Premissas, quickstart §2.1]
- [x] CHK017 Há caminho de volta para a rota antiga sem deploy de código? [Gap, Spec §FR-016] — *corrigido: FR-016 cita a env que devolve os links novos à rota do backend*

## Clareza dos requisitos

- [x] CHK018 A latência do caso normal está quantificada e amarrada a um evento observável? [Clarity, Spec §SC-002, §FR-014]
- [x] CHK019 "Por cliente" no limite de chamadas está definido (qual cabeçalho identifica o cliente)? [Clarity, Spec §FR-007, research R6]
- [x] CHK020 O teto de recusas guardadas está quantificado? [Ambiguity, Spec §FR-004] — *corrigido: 120 por hora*
- [x] CHK021 O limiar de "linha parada" está quantificado? [Clarity, Spec §FR-015]

## Consistência

- [x] CHK022 A regra do segredo do receptor é a mesma de `token_do_aviso_valido` (atual; anterior na janela; vazio nunca vale)? [Consistency, Spec §FR-002] — *corrigido: "vazio nunca vale" explícito*
- [x] CHK023 A política 404/400 do receptor é coerente com a 310 (FR-027a; "reenviar só com 400")? [Consistency, research R4]
- [x] CHK024 A troca da R-20 está listada para todos os lugares que a citam (DEVELOPMENT, skill, constituição, CLAUDE.md)? [Consistency, Spec §FR-021, §Docs]
- [x] CHK025 A História 5 e a pesquisa concordam sobre quem já filtra deploy por pasta (frontend e receptor por `rootDir`, backend por filtro)? [Consistency, Spec §H5, research R9]

## Cobertura de cenários e bordas

- [x] CHK026 O receptor fora do ar (falha do Render) tem tratamento declarado, mesmo que seja "rede da 310"? [Coverage, Spec §Casos de borda]
- [x] CHK027 Está coberto o receptor no ar antes de a migration do backend criar a tabela (primeiro deploy)? [Gap, Spec §Casos de borda] — *corrigido: borda nova (400, a operadora reenvia; loja desligada no primeiro deploy)*
- [x] CHK028 Dois drenos concorrentes estão cobertos? [Coverage, Spec §FR-011, verify 15]
- [x] CHK029 A ordem dreno → expiração está exigida? [Coverage, Spec §FR-013, verify 16]
- [x] CHK030 Links criados antes da troca de endereço estão cobertos? [Coverage, Spec §H2.3]
- [x] CHK031 O retorno forjado antes do aviso, pelo caminho da caixa, está coberto? [Coverage, Spec §Casos de borda, verify 17]

## Segurança

- [x] CHK032 Está exigido que o segredo não apareça em log, banco nem corpo de erro do receptor? [Completeness, Spec §FR-008]
- [x] CHK033 Está exigido que o corpo de erro do receptor não exponha detalhe interno (exceção, SQL)? [Gap, Spec §FR-006] — *corrigido: corpo fixo*
- [x] CHK034 O alcance da credencial de banco do receptor está declarado (mesmo usuário do backend) e aceito? [Assumption, Spec §Premissas] — *corrigido: premissa nova*
- [x] CHK035 As rotas de saúde estão declaradas sem dado? [Completeness, Spec §RBAC]

## Documentação operacional

- [x] CHK036 Os passos de produção têm resultado esperado verificável (código HTTP, linha de log, linha no banco)? [Measurability, quickstart §2]
- [x] CHK037 O motivo de não usar o plano gratuito está registrado? [Completeness, Spec §FR-018]
- [x] CHK038 Está definido como se percebe o receptor fora do ar no dia a dia? [Gap, Spec §FR-021] — *corrigido: a sonda do `manto-deploy` passa a incluir `/health/banco`*

## Notas

- Avaliação 1/1: 27/27 itens de qualidade passando depois das correções na spec (8 lacunas
  fechadas). Os portões CHK001–CHK011 são marcados no fim da implementação.

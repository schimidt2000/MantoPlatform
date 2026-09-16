# Desempenho Checklist: Catálogo rápido

**Propósito**: testar a QUALIDADE DOS REQUISITOS de desempenho e de preservação de contrato — se
estão completos, claros, mensuráveis e consistentes entre si — antes de gerar as tarefas. Não testa
implementação.
**Created**: 2026-09-16
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano e das tarefas. **Rodado contra
a spec na mesma sessão**: 11 itens falharam e viraram correção na spec (Princípio VII).

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

## Completude dos requisitos

- [x] CHK011 Todos os caminhos medidos como lentos têm requisito próprio? [Conflito, Spec §FR-001 × plan.md] — **FALHOU. Corrigido**: a visão Personagens (474 consultas, 2.320 na aba) agora é nomeada na História 1, no FR-001 e no cenário 1 do verify
- [x] CHK012 O requisito de carregamento antecipado cobre os dois lados com o mesmo critério? [Completude, Spec §FR-001, §FR-002] — passou; o FR-002 ganhou a grade de categorias, que faltava
- [x] CHK013 Está especificado o que acontece quando a geração da miniatura **falha**, e não só quando o arquivo está ausente? [Lacuna] — **FALHOU. Corrigido**: caso de borda novo
- [x] CHK014 Existe requisito de reversão declarado? [Lacuna, Exceção/Recuperação] — **FALHOU. Corrigido** pelo caso de borda da janela de deploy: como os dois caminhos de imagem já existem em produção e nada é gravado no banco, a reversão é um `git revert` simples, sem migração a desfazer
- [x] CHK015 O adiamento de imagens está especificado para a vitrine também? [Completude, Spec §FR-007] — **FALHOU. Corrigido**: o FR-007 agora diz que na vitrine o comportamento já existe e deve ser preservado, não reintroduzido
- [x] CHK016 Os requisitos dizem o que acontece com quem está com a tela aberta durante o deploy? [Lacuna] — **FALHOU. Corrigido**: caso de borda novo
- [x] CHK017 "Caixa pequena (até ~128 pixels)" é limite verificável? [Clareza, Spec §FR-004] — **FALHOU. Corrigido**: agora é "maior dimensão renderizada de até 64 px", com a razão do 128 explícita
- [x] CHK018 "Não cresce com o volume" e o teto de 10 dizem a mesma coisa? [Mensurabilidade] — passou: o teto é a aferição prática da propriedade, e a propriedade é o que o cenário prova
- [x] CHK019 O critério de bytes define em que momento se mede? [Clareza, Spec §SC-003] — **FALHOU. Corrigido**: "na primeira tela, antes de qualquer rolagem"
- [x] CHK020 Está declarado que os alvos de tempo são medidos no espelho? [Clareza] — passou
- [x] CHK021 "Byte a byte idêntica" está definida objetivamente? [Mensurabilidade] — passou; o FR-003 ganhou "mesmos nulos", alinhando com o contrato
- [x] CHK022 SC-006 tem dono e forma de aferição? [Mensurabilidade] — **FALHOU. Corrigido**: marcado como acompanhamento, não portão, com o dono nomeado e a razão de não travar a entrega
- [x] CHK023 A spec e os contratos concordam sobre quantos endpoints são novos? [Consistência] — passou (um, em ambos)
- [x] CHK024 A reversão da decisão 7 da 270 tem o mesmo alcance nos três artefatos? [Consistência] — passou
- [x] CHK025 As larguras citadas são as da allowlist? [Consistência] — passou
- [x] CHK026 Os números de "antes" são os mesmos nos três artefatos, da mesma data e espelho? [Consistência] — passou
- [x] CHK027 Há requisito para o caminho alternativo de cada história? [Cobertura] — passou (cenário de aceite 3 da História 1, cenário 1 do verify)
- [x] CHK028 Os cenários de exceção estão escritos como requisito? [Cobertura] — passou: FR-008 cobre o arquivo ausente, e os casos de borda foram ampliados
- [x] CHK029 Existe requisito para concorrência na geração da mesma miniatura? [Lacuna] — **FALHOU. Corrigido**: caso de borda apontando a corrida que a 270 já resolveu e que esta feature não pode reintroduzir
- [x] CHK030 A superfície pública tem requisito de viewport móvel? [Cobertura, Princípio X] — passou
- [x] CHK031 O requisito é propriedade estrutural, não número de hoje? [Não-funcional] — passou
- [x] CHK032 Há requisito sobre o custo da primeira visita com cache frio? [Não-funcional] — passou (premissa do aquecimento, com dono e condição)
- [x] CHK033 Acessibilidade das imagens foi considerada ou deixada deliberadamente? [Lacuna] — **FALHOU. Corrigido**: declarado que não muda, e por quê
- [x] CHK034 O aquecimento tem dono, momento e condição? [Premissa] — passou
- [x] CHK035 A premissa do espelho é falseável? [Premissa] — passou (458 produtos, conferível na produção)
- [x] CHK036 A dependência do motor da 270 está documentada como inalterada? [Dependência] — passou
- [x] CHK037 "Telas de lista do catálogo" está delimitado o bastante? [Ambiguidade] — passou: a spec nomeia os três modos e o Fora de escopo nomeia as telas excluídas
- [x] CHK038 O que fica de fora separa "não entra agora" de "não deve existir nunca"? [Ambiguidade] — passou: o palco é permanente (decisão 9), as outras telas internas são adiamento
- [x] CHK039 Há conflito entre "o contrato não muda" e o endpoint novo? [Conflito] — **FALHOU (aparente). Corrigido**: o FR-003 agora diz que o endpoint novo acrescenta caminho sem alterar os existentes

## Notas

- Marque como concluído: `[x]`
- Anote achados na própria linha
- Itens numerados em sequência para referência
- **Resultado desta rodada**: 29 itens de requisito avaliados, **11 falharam e foram corrigidos na
  spec antes de gerar as tarefas**. O mais grave foi o CHK011 — sem ele, as tarefas nasceriam sem o
  endpoint que responde por 474 das 2.320 consultas da aba Personagens.
- Os dez Portões da Manto (CHK001–CHK010) seguem abertos: são conferidos ao fim da implementação,
  não agora.

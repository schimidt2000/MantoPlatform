# Checklist de revisão dos requisitos: Feature 317

**Purpose**: testar a escrita da spec/plan (não o código) nos cinco focos pedidos: integração externa, vínculo
automático, situação/listas × cobrança da 299, RBAC e cobertura do verify
**Created**: 2026-10-22 · **Público**: revisor do PR · **Profundidade**: padrão
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

Legenda das resoluções: **→ spec** = corrigido na spec nesta passada; **→ plan** = já coberto no plano/contratos;
**→ dono** = depende de decisão do dono (nenhum item ficou nesse estado).

## Integração externa — segurança do aviso, trava local, segredos

- [x] CHK001 - A spec define o que torna um aviso da ClickSign aceitável (assinatura correta) e o que acontece com o
      inválido? [Completeness, Spec §FR-016] → spec + contracts/api.md (404, sem efeito)
- [x] CHK002 - Está escrito que o conteúdo do aviso nunca decide a situação (sempre se confirma na ClickSign)?
      [Clarity, Spec §FR-016, Casos de borda] → spec
- [x] CHK003 - Há requisito para aviso repetido, fora de ordem e perdido? [Coverage, Spec §Casos de borda, §FR-015]
- [x] CHK004 - O limite de tamanho e de frequência do aviso está documentado? [Gap] → plan/contracts (64 KB, 60/min)
- [x] CHK005 - A regra "nenhuma cópia local fala com a ClickSign" é mensurável? [Measurability, Spec §FR-017, §SC-006]
      → cenário 23 do verify
- [x] CHK006 - Onde mora cada segredo (token × segredo do aviso) e por quê está registrado? [Completeness, Spec §FR-017]
      → research R-05
- [x] CHK007 - O comportamento sem credencial (integração desligada) cobre todas as telas afetadas? [Coverage, Spec
      §FR-018, Casos de borda]
- [x] CHK008 - A troca/revogação do segredo do aviso tem requisito? [Gap] → data-model (`_anterior` 24 h) + quickstart §4
- [x] CHK009 - A spec trata dado pessoal do signatário (o que se guarda e o que não)? [Gap, LGPD] → **spec** (Premissas:
      só nome, telefone, e-mail e canal; CPF e endereço da ClickSign não são guardados)
- [x] CHK010 - O consumo de cota da API (50 req/10 s) e o volume do retroativo estão quantificados? [Clarity] → research
      (Portão 0) + plan (metas)

## Vínculo automático — falso positivo

- [x] CHK011 - O critério de "candidato único" está definido sem ambiguidade (quais telefones, qual data)? [Clarity,
      Spec §FR-004] → research R-02 (data de qualquer dia do grupo; três fontes de telefone)
- [x] CHK012 - O desempate pelo tema tem regra objetiva? [Clarity, Spec §FR-004] → research R-02 (normalizado, contém)
- [x] CHK013 - A divergência entre telefone do nome e telefone do signatário tem tratamento? [Edge Case, Gap] → research
      R-02 ("a conferir", motivo `telefone_diverge`)
- [x] CHK014 - FR-002 e a pesquisa concordam sobre documento "outro" com data legível? [Conflict, Spec §FR-002 × R-03] →
      **spec** (FR-002 ajustado: "outro" com data legível vai para "A conferir")
- [x] CHK015 - Está escrito que o vínculo manual e o descarte nunca são desfeitos pela sincronização? [Completeness, Spec
      §FR-005] → spec + data-model (transições)
- [x] CHK016 - Duas pessoas ligando o mesmo documento ao mesmo tempo está coberto? [Edge Case, Gap] → **spec** (Casos de
      borda)
- [x] CHK017 - A venda excluída e a passagem de grupo têm requisito para o vínculo? [Coverage, Spec §Casos de borda]
- [x] CHK018 - O SC-001 diz como se mede ("9 de cada 10 sem clique")? [Measurability, Spec §SC-001] → **spec** (contagem
      por origem do vínculo nos documentos de cliente criados no período)
- [x] CHK019 - O SC-002 é verificável? [Measurability, Spec §SC-002] → **spec** (motivo visível + desligar registrado)

## Situação e listas × cobrança da 299

- [x] CHK020 - A unidade (venda = principal) é a mesma da cobrança de valor? [Consistency, Spec §Premissa 1, §FR-008]
- [x] CHK021 - A diferença com a 299 sobre cortesia está explícita? [Consistency, Spec §Premissa 2, Clarify]
- [x] CHK022 - Os grupos da Home têm fronteira de data definida (futuro × já aconteceu)? [Clarity, Spec §FR-010] →
      **spec** (FR-010 diz qual grupo leva evento passado)
- [x] CHK023 - A régua de cor está quantificada para cada situação, não só "aguardando"? [Clarity, Spec §Premissa 5] →
      data-model (regras derivadas) e **spec** (FR-010 cita sem contrato e vencido)
- [x] CHK024 - Há uma fonte só para "situação do contrato" (evento, Home, coluna Contrato de /vendas)? [Conflict, Gap] →
      **spec** (FR-019: a coluna Contrato de /vendas passa a ler a mesma situação)
- [x] CHK025 - O texto da mensagem tem variação definida por canal e prazo? [Completeness, Spec §FR-011]
- [x] CHK026 - O registro da cobrança diz o que aparece e onde ("cobrado por X em DD/MM")? [Clarity, Spec §FR-010–011]
- [x] CHK027 - O botão desativado lista todos os motivos com o texto? [Completeness, Spec §História 2 cenário 3, FR-012]

## RBAC

- [x] CHK028 - Cada endpoint novo tem papéis declarados? [Completeness, Spec §RBAC] → spec + contracts/api.md
- [x] CHK029 - O FINANCEIRO vê mas não cobra/confirma, e isso está igual na Home e no evento? [Consistency, Spec §Decisão
      3, História 2 cenário 4]
- [x] CHK030 - O que CASTING e outros papéis veem (nada) está escrito? [Coverage, Spec §RBAC, verify 17]
- [x] CHK031 - A trava do cancelado (312) vale para ligar/cobrar? [Consistency, Spec §FR-005, FR-012] → contracts (409)

## Cobertura do verify

- [x] CHK032 - Toda história e todo FR têm cenário no verify? [Traceability, Spec §Verificação] — FR-019 ganhou cenário 9
- [x] CHK033 - Há cenários que DEVEM falhar para segurança e RBAC? [Coverage, Spec §Verificação 13, 15, 16, 17]
- [x] CHK034 - O verify declara como evita rede de verdade? [Completeness, Spec §Verificação] → dublê + disjuntor
- [x] CHK035 - As regras de integridade de outras features (306, 312) estão previstas no verify? [Coverage, Spec
      §Verificação 25] → plan (verify_306/312)

## Notas

- 35 itens, 35 resolvidos. Mudanças na spec feitas nesta passada: CHK009, 014, 016, 018, 019, 022, 023, 024.

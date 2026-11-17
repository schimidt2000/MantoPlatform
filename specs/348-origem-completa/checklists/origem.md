# Checklist de requisitos: origem (atribuição, código do site, frente, contrato, RBAC, texto)

**Purpose**: testar a qualidade da escrita dos requisitos da 348 antes das tarefas (não testa a implementação)
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/](../contracts/)

Profundidade: padrão · Público: revisor (sessão principal no lote de merge) · Itens marcados = o requisito está
escrito e claro; o resultado de cada um está na seção Notas.

## Atribuição (contato congelado por venda, cliente recorrente)

- [x] CHK001 - A regra que escolhe o contato de origem de uma venda está escrita com tipos, janela e desempate? [Clarity, Spec §FR-012, research R7]
- [x] CHK002 - O momento de referência da janela está definido para cada caminho (envio do orçamento, criação com conversa, herança do orçamento)? [Completeness, Spec §FR-011, §FR-013, §FR-014]
- [x] CHK003 - O caso da cliente recorrente (dois anúncios, duas vendas) tem cenário de aceite com resultado esperado para cada venda? [Coverage, Spec §História 3 cenário 2]
- [x] CHK004 - A proibição de ligar venda à conversa pela ficha está escrita como requisito, não só como premissa? [Completeness, Spec §FR-015]
- [x] CHK005 - O que acontece com a origem do evento quando o orçamento é trocado ou desligado está especificado sem conflitar com a ligação feita pela 349? [Consistency, Spec §FR-013]
- [x] CHK006 - A venda orgânica (conversa sem contato na janela) tem representação definida e distinta de "sem conversa"? [Clarity, Spec §FR-012, contracts/consumidores.md]
- [x] CHK007 - O satélite de grupo tem regra de leitura da origem e da frente? [Edge Case, Spec §História 4 cenário 4, data-model]
- [x] CHK008 - A conversa apagada tem efeito definido sobre orçamento e evento? [Edge Case, Spec §Casos de borda]

## Código do site (privacidade, validade, falhas)

- [x] CHK009 - A lista exata de marcadores guardados está escrita, e a condição de "sem marcador" é objetiva? [Clarity, Spec §FR-004, §FR-005]
- [x] CHK010 - A validade de 90 dias vale igual no navegador, no servidor e na leitura da mensagem? [Consistency, Spec §Clarifications, §FR-004, §FR-009]
- [x] CHK011 - O formato do código e da linha na mensagem estão definidos, incluindo o alfabeto e o tamanho? [Clarity, Spec §Clarifications, research R4]
- [x] CHK012 - A regra "o primeiro uso vence" e o tratamento de código usado, vencido ou inexistente estão escritos? [Coverage, Spec §FR-009, §História 2 cenário 4]
- [x] CHK013 - A falha ao criar o código tem requisito de não bloquear página, formulário e WhatsApp? [Exception Flow, Spec §FR-008]
- [x] CHK014 - Está definido o que o servidor guarda da procedência e da página (host e caminho, sem query nem dado pessoal)? [Non-Functional/Privacidade, data-model]
- [x] CHK015 - A base para guardar os marcadores sem consentimento está registrada, e a pendência do aviso de privacidade aparece como premissa do dono? [Assumption, Spec §Clarifications, §Premissas]
- [x] CHK016 - A retenção do código não usado está decidida (e registrada como dívida)? [Gap resolvido no clarify, Spec §Clarifications]
- [x] CHK017 - As páginas que não criam código (loja virtual) estão nomeadas? [Boundary, Spec §FR-004, §Clarifications]
- [x] CHK018 - O limite de chamadas do endpoint público está quantificado? [Clarity, contracts/api.md]
- [x] CHK019 - O reenvio do aviso pela Meta tem comportamento definido para o código (não religa) e para o contato (não duplica)? [Edge Case, Spec §Casos de borda]

## Frente (sugestão × definida, compatibilidade com a 345)

- [x] CHK020 - "Sugestão certa" e "sugestão por exclusão" estão definidas pela regra exata de 16/11? [Clarity, Spec §Clarifications]
- [x] CHK021 - A obrigatoriedade da frente tem gatilho objetivo (bundle novo + venda > 0 + sem cortesia + nenhuma frente)? [Measurability, Spec §FR-020]
- [x] CHK022 - O comportamento com o bundle antigo (sem o campo) está especificado? [Compatibilidade, Spec §FR-020, armadilha 21]
- [x] CHK023 - A spec garante que os números por frente da 345 não mudam para eventos sem frente gravada? [Consistency, Spec §SC-006, research R9]
- [x] CHK024 - A frente na criação do evento tem regra própria (só a sugestão certa)? [Completeness, Spec §FR-021]
- [x] CHK025 - A frente no evento cancelado segue regra declarada? [Edge Case, Spec §Casos de borda]
- [x] CHK026 - O "null" no corpo da aba Comercial tem efeito definido (não apaga)? [Clarity, contracts/api.md]

## Contrato para a 349 e a 351

- [x] CHK027 - O ponto de entrada da 349 (criar evento com conversa) está especificado com validação e erro? [Completeness, Spec §FR-014, contracts/api.md]
- [x] CHK028 - A função única da frente tem nome, retorno e equivalência Python × SQL documentados? [Clarity, Spec §FR-018, contracts/consumidores.md]
- [x] CHK029 - O caminho de leitura da origem da venda até a campanha e o conjunto está documentado? [Completeness, contracts/consumidores.md]
- [x] CHK030 - O destino normativo do contrato (`docs/01`) está nomeado? [Traceability, Spec §Docs a atualizar]

## RBAC

- [x] CHK031 - Todo endpoint novo ou alterado tem papel declarado? [Completeness, Spec §RBAC]
- [x] CHK032 - A exposição da origem e da frente no detalhe está limitada ao bloco comercial, e o link para a conversa respeita o acesso às Conversas? [Consistency, Spec §FR-016, contracts/api.md `pode_abrir`]
- [x] CHK033 - Há cenário de verificação que DEVE falhar para papel sem permissão? [Coverage, Spec §Verificação cenário 14]

## Texto (Princípio XV)

- [x] CHK034 - Os textos novos do app interno estão escritos e no tom operacional (imperativo curto, "Selecione")? [Clarity, plan §Constitution Check XV, contracts/api.md]
- [x] CHK035 - A linha que vai para a mensagem da cliente está escrita e é curta e clara (superfície pública)? [Clarity, Spec §Clarifications]
- [x] CHK036 - Os rótulos das frentes vêm de uma fonte só (as frentes da 345), sem sinônimo novo? [Consistency, contracts/api.md `opcoes`]

## Notas

- Iteração 1 (17/11): CHK016 e CHK017 eram lacunas e foram resolvidos no clarify (retenção do código; loja fora).
  CHK018 e CHK026 estavam só no contrato de API: aceito, porque são detalhe de endpoint, e a spec aponta para o
  contrato. CHK032 ganhou o `pode_abrir` no contrato (Financeiro vê o bloco comercial mas não usa Conversas).
- Todos os 36 itens passam.

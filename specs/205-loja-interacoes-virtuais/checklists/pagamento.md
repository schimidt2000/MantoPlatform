# Pagamento, Idempotência e Concorrência — Checklist de Requisitos: Loja de Interações Virtuais

**Purpose**: Auditar a **qualidade dos requisitos escritos** sobre dinheiro, posse de horário e
reprocessamento. Não testa comportamento do sistema — testa se o que está escrito é completo, claro,
consistente e mensurável o bastante para alguém implementar sem adivinhar.
**Created**: 2026-07-30
**Feature**: [spec.md](../spec.md)
**Profundidade**: portão formal — item não resolvido bloqueia `/speckit.tasks`

## Completude dos requisitos de pagamento

- [ ] CHK001 Os requisitos definem o que constitui "pagamento confirmado" de forma única e sem depender do canal pelo qual a informação chegou? [Completeness, Spec §FR-027, §FR-027b]
- [ ] CHK002 Está especificado o que acontece quando o valor pago é **maior** que o total do pedido (a operadora devolve `paid_amount` separado de `amount`)? [Gap, Spec §FR-027b]
- [ ] CHK003 Está especificado o que acontece com pagamento **parcial** ou com valor menor que o total congelado? [Gap, Spec §FR-027c]
- [ ] CHK004 Os requisitos cobrem o pedido que nunca chega a gerar link de pagamento (falha na criação)? [Coverage, Spec §FR-021]
- [ ] CHK005 Está definido por quanto tempo um link de pagamento permanece válido depois que o soft lock expira? [Gap, Ambiguity]
- [ ] CHK006 Os requisitos dizem se o mesmo pedido pode ter mais de uma tentativa de cobrança, e como as tentativas se relacionam? [Gap]
- [ ] CHK007 Está especificado o que o sistema faz com um pagamento recebido para pedido já `pago` (pagamento em duplicidade real, não reentrega de aviso)? [Gap, Edge Case]
- [ ] CHK008 Os requisitos definem o tratamento de um pagamento que chega para pedido `cancelado` ou `expirado` que já teve devolução aberta? [Gap, Edge Case]

## Clareza e mensurabilidade

- [ ] CHK009 O termo "reconsultar a cobrança" está definido de forma verificável — quais campos precisam conferir para autorizar a liberação? [Clarity, Spec §FR-027b]
- [ ] CHK010 "Reter o pedido para nova tentativa" está quantificado: quantas tentativas, em que intervalo, e qual o estado final se todas falharem? [Ambiguity, Spec §FR-027d]
- [ ] CHK011 "Sinalizar à equipe" está definido de forma objetiva — onde a sinalização aparece e o que a faz desaparecer? [Ambiguity, Spec §FR-027c, §FR-034, §FR-043]
- [ ] CHK012 O prazo do soft lock (15 minutos) está declarado como contado a partir de qual instante exato? [Clarity, Spec §FR-017]
- [ ] CHK013 Os critérios de sucesso sobre duplicidade são objetivamente verificáveis sem acesso ao código? [Measurability, Spec §SC-004, §SC-006]
- [ ] CHK014 "Abaixo de 1% dos pedidos pagos" em SC-012 tem base de cálculo e janela de medição definidas? [Measurability, Spec §SC-012]

## Consistência entre requisitos

- [ ] CHK015 O ciclo de vida do pedido na seção de entidades bate com todos os estados citados nos requisitos e cenários? [Consistency, Spec §Key Entities, §FR-042]
- [ ] CHK016 Os requisitos de expiração (FR-018) e de reconsulta antes de liberar (FR-041a) estão descritos sem se contradizerem sobre quando o horário volta ao estoque? [Consistency, Spec §FR-018, §FR-041a]
- [x] CHK017 SC-005 ("no máximo 16 minutos") continua coerente com FR-041a, que insere uma reconsulta antes da liberação? [Conflict, Spec §SC-005, §FR-041a] — **resolvido**: FR-018a/018b criaram a tolerância de 5 min com retry e SC-005 passou a declarar os dois prazos (16 min normal, 21 min com operadora fora)
- [ ] CHK018 Os valores congelados (FR-022) estão descritos de forma consistente com a conferência de valor da reconsulta (FR-027b)? [Consistency]
- [ ] CHK019 A revisão registrada em Clarifications sobre estorno está refletida sem resíduo em todos os pontos que antes prometiam estorno automático? [Consistency, Spec §Clarifications]

## Cobertura de concorrência

- [ ] CHK020 Os requisitos descrevem o resultado esperado da disputa simultânea pelo mesmo horário do ponto de vista de **ambos** os visitantes? [Coverage, Spec §FR-020, US2 cenário 5]
- [ ] CHK021 Está especificado o comportamento quando a última unidade de vídeo gravado é disputada por dois checkouts simultâneos? [Coverage, Spec §FR-023]
- [ ] CHK022 Os requisitos cobrem a corrida entre a expiração do soft lock e a chegada do pagamento do mesmo pedido? [Coverage, Spec §FR-041a]
- [ ] CHK023 Está definido o que acontece se o admin pausar a campanha no exato momento em que uma reserva está sendo criada? [Gap, Edge Case]
- [ ] CHK024 Os requisitos dizem se um mesmo pedido pode trocar de horário, e o que acontece com o horário anterior? [Gap, Spec §FR-020a]

## Idempotência e reprocessamento

- [ ] CHK025 Está declarado qual identificador estabelece que dois avisos representam o mesmo pagamento? [Completeness, Spec §FR-028]
- [ ] CHK026 Os requisitos definem o que deve ser idempotente item a item — evento, escala, presente 3D, estoque, e-mail? [Completeness, Spec §FR-028, §SC-006]
- [x] CHK027 O envio de e-mail está coberto pela regra de idempotência, ou reentrega pode gerar aviso repetido à família? [Gap, Spec §FR-035, §FR-039] — **resolvido**: FR-028 passou a incluir avisos; FR-028a/028b exigem registro consultado antes do envio e gravado na mesma transação (`UNIQUE(order_id, kind)`)
- [ ] CHK028 Está especificado o comportamento diante de avisos que chegam **fora de ordem**? [Coverage, Spec §Edge Cases]
- [ ] CHK029 Os requisitos definem que a resposta ao aviso deve ser de sucesso mesmo em duplicata, conflito ou pedido inexistente — e por quê? [Clarity, Contracts §2]
- [ ] CHK030 Está definido o que acontece se a efetivação falhar no meio (evento criado, presente não) — os requisitos exigem atomicidade explicitamente? [Gap, Spec §FR-029 a §FR-033]

## Registro financeiro segregado

- [ ] CHK031 Os requisitos enumeram **quais** painéis e cálculos precisam excluir o canal virtual, ou dizem apenas "os indicadores de eventos"? [Ambiguity, Spec §FR-054]
- [ ] CHK032 Está definido a quem pertence a venda virtual para efeito de comissão — ninguém, um responsável fixo, ou fora do cálculo? [Gap, Spec §FR-054]
- [ ] CHK033 Os requisitos dizem o que acontece no DRE quando uma venda é cancelada com devolução — a receita é estornada do período? [Gap, Spec §FR-053, §FR-042]
- [ ] CHK034 Está especificado como o valor da venda se decompõe entre interação e presente para efeito de relatório? [Gap, Spec §FR-052]
- [ ] CHK035 SC-014 é verificável com os requisitos como escritos, ou depende de saber quais agregadores existem? [Measurability, Spec §SC-014]

## Devolução

- [ ] CHK036 Os requisitos definem prazo ou expectativa para a equipe executar uma devolução aberta? [Gap, Spec §FR-043]
- [ ] CHK037 Está especificado o que a família é informada sobre prazo de devolução, dado que o sistema não controla isso? [Clarity, Spec §FR-043a]
- [ ] CHK038 Os requisitos cobrem devolução parcial ou pedido com presente 3D já injetado na fila antes do cancelamento? [Gap, Edge Case]
- [ ] CHK039 Está definido quem tem permissão para marcar uma devolução como concluída? [Gap, Spec §FR-043]

## Anti-abuso

- [ ] CHK040 "Origem" está definida de forma implementável e resistente a variação trivial? [Ambiguity, Spec §FR-020b]
- [ ] CHK041 Os requisitos especificam valores iniciais dos limites, ou apenas que são ajustáveis? [Completeness, Spec §FR-020b, §FR-020d]
- [ ] CHK042 Está definido quem pode ajustar os limites e se a mudança afeta reservas já criadas? [Gap, Spec §FR-020d]
- [ ] CHK043 Os requisitos tratam o falso positivo — família legítima bloqueada por compartilhar origem (mesma rede, mesmo telefone da família)? [Coverage, Spec §Edge Cases]

## Notes

- Marque `[x]` conforme resolver; anote a decisão na linha.
- Item não resolvido é lacuna de **requisito**, não de código: a correção é editar `spec.md` (Princípio VII — Living Spec), não abrir tarefa de implementação.
- CHK017 e CHK027 são os candidatos mais prováveis a conflito real entre requisitos já escritos.

# Checklist de requisitos — dinheiro, segurança e operação (310)

**Propósito**: testar a ESCRITA dos requisitos (completude, clareza, consistência, cobertura) antes do
`/speckit-tasks` — não testa código.
**Criado**: 2026-10-20 · **Feature**: [spec.md](../spec.md) · Profundidade: rigorosa · Leitor: autor +
revisão do dono antes do implement.

## Dinheiro e concorrência — completude

- [x] CHK001 - A regra única de "pagamento vira venda" lista TODAS as condições e a ordem em que são avaliadas (estado do pedido, valor, dono do horário, folga, vaga)? [Completeness, Spec §FR-001, research R1]
- [x] CHK002 - Está especificado o desfecho para cada combinação de estado do pedido × pagamento provado (reservado, aguardando, expirado, pago, cancelado)? [Coverage, data-model §Máquina]
- [x] CHK003 - O requisito de "venda confirmada nunca regride" cobre também a liberação manual e o cancelamento pela equipe (não só a varredura)? [Completeness, Spec §FR-003, FR-034]
- [x] CHK004 - Há requisito para pagamento de pedido já CANCELADO por conflito (família paga o link antigo de novo)? [Coverage, research R1.4]
- [x] CHK005 - O tratamento de valor pago MAIOR que o total (sobrepagamento) está definido — vira venda, devolução da diferença ou alerta? [Gap, Spec §FR-015]
- [x] CHK006 - Está definido o que acontece com um pagamento divergente (menor): devolução automática ou só alerta para a equipe? [Clarity, Spec §FR-015 × research R1.3]
- [x] CHK007 - O requisito de capacidade do vídeo gravado especifica se reservas ATIVAS (não pagas) ocupam vaga e por quanto tempo? [Clarity, Spec §FR-007]
- [x] CHK008 - O presente 3D tem requisito próprio nos desfechos de devolução e cancelamento (sai da fila de impressão)? [Gap, Spec §FR-034, research R15]
- [x] CHK009 - Está especificado que a ordem de travas (pedido → horário → campanha) vale para TODAS as rotinas que mexem em pedido/horário, inclusive o cancelamento pela equipe? [Consistency, data-model invariante 6]

## Dinheiro e concorrência — clareza e consistência

- [x] CHK010 - "Folga de 30 minutos no pagamento" e "antecedência de 2 h para reservar" estão descritas de forma consistente em spec, research e contrato (sem um lugar dizendo só "antecedência")? [Consistency, Spec §FR-001, FR-006, Cenário H1.5]
- [x] CHK011 - "Pagamento a conferir" tem definição única (quais origens entram, quais não) igual na spec (FR-012, FR-031) e no research R10? [Consistency]
- [x] CHK012 - A diferença entre "liberado por abandono" e "liberado sem prova (operadora fora)" está explícita nos requisitos, para não inundar a lista a conferir? [Clarity, Spec §FR-012 × research R4]
- [x] CHK013 - O SC-002 ("100% dos não provados aparecem em até 20 minutos") é coerente com a decisão de que pedido abandonado sem identificadores NÃO entra na lista? [Conflict, Spec §SC-002 × research R4]
- [x] CHK014 - O tempo máximo de reprocessamento de avisos (48 h) e a cadência estão nos requisitos, não só no research? [Gap, Spec §FR-013]
- [x] CHK015 - Os desfechos possíveis do aviso (finais × não finais) estão listados na spec ou num documento referenciado por ela? [Completeness, data-model §Constantes]

## Reconciliação e prova de pagamento

- [x] CHK016 - O requisito do retorno especifica o que acontece quando o retorno chega ANTES do aviso, DEPOIS do aviso e sem identificadores? [Coverage, Spec §FR-010, contrato]
- [x] CHK017 - Está documentado o fato real de que a reconsulta sem identificadores responde `success:false` e que isso não é "não pago"? [Completeness, Spec §Teste 0, FR-011]
- [x] CHK018 - Há requisito para o caso residual "pagou, aviso perdido, família não tocou Continuar" — e ele está declarado como risco aceito com mitigação (regra de deploy)? [Gap, Assumption]
- [x] CHK019 - O requisito de que identificadores só são gravados após prova cobre retorno E aviso de forma idêntica? [Consistency, Spec §FR-010, FR-017]
- [x] CHK020 - Está claro se a varredura usa identificadores vindos de avisos já registrados (mas não decididos) do mesmo pedido? [Clarity, research R2]

## Segurança do aviso e dados

- [x] CHK021 - O modelo de ameaça do aviso não assinado está escrito (quem pode chamar, o que conseguiria, por que a reconsulta é a prova)? [Traceability, Spec §Causa 8, FR-029]
- [x] CHK022 - O período em que o segredo anterior continua aceito (24 h) está nos requisitos e justificado frente ao risco de vazamento? [Gap, research R7]
- [x] CHK023 - O mascaramento do token cobre todos os lugares de log citados (gunicorn, proxy Node, logs de aplicação com order_nsu)? [Completeness, Spec §FR-029]
- [x] CHK024 - Os limites de requisição (aviso 60/min, retorno 20/min, corpo 64 KB) estão quantificados na spec, não só no contrato? [Clarity, Spec §FR-029, contrato]
- [x] CHK025 - O que vai para a operadora está enumerado campo a campo (e o que NÃO vai), incluindo a descrição do item? [Completeness, Spec §FR-028, research R13]
- [x] CHK026 - O requisito do IP do cliente declara a premissa (Node é o único caminho público) e o que acontece se ela deixar de valer? [Assumption, Spec §FR-027, research R8]

## Trava fora da produção

- [x] CHK027 - A trava especifica TODAS as saídas externas da loja (criar link, reconsulta, criar/apagar evento Google, e-mail) e qual chave governa cada uma? [Completeness, Spec §FR-020]
- [x] CHK028 - Está definido o comportamento visível ao usuário local quando travado (mensagem) e o que o verify precisa para destravar? [Clarity, Spec §H3 cenário 1]
- [x] CHK029 - O requisito trata o fato de que no local o endereço público aponta para produção (webhook_url) — mesmo com a trava? [Coverage, refutação A7]

## Operação: ligar, desligar, a conferir

- [x] CHK030 - O estado inicial do interruptor em produção depois do deploy está especificado, com o passo de quem liga e quando? [Completeness, Spec §FR-021, quickstart §2]
- [x] CHK031 - Está definido o que acontece com campanhas JÁ publicadas quando o interruptor é desligado (continuam visíveis? mensagem?)? [Gap, Spec §FR-021, FR-022]
- [x] CHK032 - O requisito do "Cancelar e abrir devolução" define o que acontece com o horário quando faltam menos de 2 h, e com o e-mail à família? [Clarity, Spec §FR-034, research R15]
- [x] CHK033 - Quem pode marcar "a conferir" como resolvido e se é reversível estão definidos? [Gap, Spec §FR-031]
- [x] CHK034 - A notificação no sino tem regra de deduplicação quantificada? [Clarity, Spec §FR-026, FR-032]
- [x] CHK035 - A regra de deploy durante a campanha está como requisito/operação (datas e horas), e não só no quickstart? [Gap, Spec §FR-043]
- [x] CHK036 - O procedimento de limpeza de venda de teste define o que sai e o que fica (auditoria, pedido cancelado, avisos)? [Completeness, Spec §FR-042]

## Critérios de aceite e dependências

- [x] CHK037 - Cada FR de dinheiro (FR-001–FR-017) aponta para ao menos um cenário do verify que o prova? [Traceability, Spec §Verificação]
- [x] CHK038 - O SC-001 ("20×") define o que é uma rodada e como a concorrência é produzida? [Measurability, Spec §SC-001]
- [x] CHK039 - A dependência de merge com 306/309 (cabeça da migration) e a do teste com a operadora real estão nas premissas? [Dependency, data-model, Spec §Premissas]
- [x] CHK040 - O que só a operadora real responde (segundo pagamento no mesmo link, reconsulta de Pix devolvido) está listado como risco com dono e momento de teste? [Assumption, research §Pontos]

## Resultado (20/10/2026)

Todos os 40 itens passaram depois da seção "Regras complementares" da spec (R-01 a R-22), que
fechou: sobrepagamento e divergente (CHK005–006), vaga do vídeo (007), presente 3D (008), ordem de
travas (009), conflito SC-002 × abandono (013), cadência e desfechos (014–015), retorno antes/depois
(016), risco aceito do aviso perdido (018), identificadores de avisos registrados (020), ameaça (021),
segredo anterior (022), logs e limites (023–024), pacote à operadora (025), premissa do IP (026),
travas por saída (027–029), interruptor e campanha publicada (030–031), cancelar pago (032), quem
resolve (033), sino (034), deploy na campanha (035), limpeza (036), SC-001 (038), dependências (039–040).

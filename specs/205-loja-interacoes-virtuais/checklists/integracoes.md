# Integrações Externas e Modos de Falha — Checklist de Requisitos: Loja de Interações Virtuais

**Purpose**: Auditar a **qualidade dos requisitos escritos** sobre os quatro serviços externos de
que a feature depende — InfinitePay, Google Calendar/Meet, Google Drive e e-mail. Não testa se a
integração funciona; testa se está escrito o que acontece quando ela falha, demora ou responde
diferente do esperado.
**Created**: 2026-07-30
**Feature**: [spec.md](../spec.md) · [research.md](../research.md)
**Profundidade**: portão formal — item não resolvido bloqueia `/speckit.tasks`

## Completude do inventário de dependências

- [ ] CHK044 Todas as dependências externas estão declaradas na spec, incluindo as que só apareceram no plano? [Completeness, Spec §Assumptions]
- [ ] CHK045 Para cada dependência, está declarado o que acontece com o negócio se ela ficar indisponível por horas? [Gap]
- [ ] CHK046 Os requisitos distinguem dependências **críticas de caminho** (sem elas não há venda) das **de entrega** (a venda existe, a entrega atrasa)? [Clarity, Gap]
- [ ] CHK047 Está especificado se alguma integração pode ser desligada por configuração para a campanha continuar vendendo? [Gap]

## InfinitePay

- [ ] CHK048 Os requisitos descrevem o comportamento esperado quando a operadora está indisponível **no momento da reserva** (criação do link)? [Coverage, Contracts §1]
- [ ] CHK049 Está especificado o que a família vê e o que acontece com o horário travado nesse caso? [Clarity, Gap]
- [ ] CHK050 Os requisitos definem tempo máximo de espera das chamadas à operadora antes de considerá-la indisponível? [Gap, Measurability]
- [ ] CHK051 Está declarado que o preço trafega em centavos e onde ocorre a conversão, para evitar divergência de valor na conferência? [Clarity, Data-model §1]
- [ ] CHK052 Os requisitos dizem o que fazer se a operadora responder com contrato diferente do documentado (campo ausente, formato novo)? [Gap, Research §R1]
- [ ] CHK053 Está especificado como o segredo do endereço de notificação é rotacionado e o que acontece com avisos em trânsito durante a troca? [Gap, Spec §FR-027a]
- [ ] CHK054 Os requisitos cobrem o cenário de o `redirect_url` ser acessado pela família antes de o aviso chegar? [Coverage, Gap]
- [ ] CHK055 Está definido o comportamento diante de aviso cujo `order_nsu` não existe no sistema? [Coverage, Spec §FR-034]
- [ ] CHK056 A limitação "sem API de estorno" está registrada como premissa validada com o fornecedor, ou apenas como leitura da documentação pública? [Assumption, Research §R1]

## Google Calendar / Meet

- [ ] CHK057 Os requisitos definem o que acontece quando a criação da sala volta pendente em vez de pronta? [Coverage, Spec §FR-037, Research §R2]
- [ ] CHK058 Está especificado até quando a sala precisa existir para a venda ser considerada entregável? [Gap, Measurability, Spec §SC-011]
- [ ] CHK059 Os requisitos dizem o que acontece se a conexão com o Google expirar entre a venda e o horário da chamada? [Gap, Edge Case]
- [ ] CHK060 Está definido quem consegue entrar na sala — apenas quem tem o link, ou há restrição de participantes? [Gap, Ambiguity]
- [ ] CHK061 Os requisitos cobrem o cancelamento ou a remoção manual do evento no Google e o efeito disso no pedido pago? [Gap, Edge Case]
- [x] CHK062 Está especificado se o evento virtual deve ou não ser sincronizado de volta pela rotina de sincronização existente? [Gap, Conflict] — **resolvido**: FR-029a exige exclusão em todos os caminhos (importação, atualização, remoção) e FR-029b transforma edição externa em sinalização, nunca em propagação
- [ ] CHK063 Os requisitos distinguem o link do evento no Calendar do link da sala, deixando claro qual chega à família? [Clarity, Research §R2]
- [ ] CHK064 Está definido o comportamento quando o talento pré-escalado muda depois da venda — a sala continua a mesma? [Gap]

## Google Drive

- [ ] CHK065 Os requisitos declaram a premissa de Drive compartilhado como condição de funcionamento, e não como detalhe de implementação? [Assumption, Research §R3]
- [ ] CHK066 Está especificado o limite de tamanho e os formatos aceitos de vídeo em valores concretos? [Ambiguity, Spec §FR-038d]
- [ ] CHK067 Os requisitos definem o que acontece quando a cota do Drive se esgota no meio de uma campanha? [Gap, Coverage]
- [ ] CHK068 Está definido o que "confirmar que o vídeo está acessível" significa de forma verificável? [Measurability, Spec §FR-038b]
- [ ] CHK069 Os requisitos cobrem o vídeo removido ou com acesso revogado **depois** de a família já ter sido avisada? [Coverage, Spec §Edge Cases]
- [x] CHK070 Está especificado se o vídeo publicado fica acessível a qualquer pessoa com o link, e se isso é aceitável para vídeo com nome de criança? [Gap, Conflict, Spec §Assumptions] — **resolvido**: hospedagem migrou do Drive para o storage da plataforma; FR-038e proíbe endereço de leitura direta e FR-044a a FR-044c exigem validação dupla (pedido + telefone) para qualquer conteúdo sensível
- [ ] CHK071 Os requisitos definem retenção e expurgo dos vídeos após o fim da campanha? [Gap, Spec §Assumptions]
- [ ] CHK072 Está definido o comportamento de reenvio de vídeo para uma entrega já finalizada (correção)? [Gap, Edge Case]

## E-mail

- [ ] CHK073 Os requisitos definem o que caracteriza falha de envio, dado que o envio é assíncrono? [Clarity, Measurability, Spec §FR-039c]
- [ ] CHK074 Está especificado o comportamento quando o e-mail informado pela família é inválido ou rejeitado? [Gap, Coverage]
- [ ] CHK075 Os requisitos definem se há reenvio automático e quantas vezes? [Gap, Spec §FR-039c]
- [ ] CHK076 Está definido o conteúdo mínimo obrigatório de cada um dos três avisos? [Completeness, Spec §FR-035, §FR-039, §FR-039a]
- [ ] CHK077 Os requisitos garantem que nenhum aviso exponha dado sensível de criança fora da página protegida por token? [Coverage, Spec §Assumptions]
- [ ] CHK078 Está especificado o que a equipe vê para saber que precisa reforçar manualmente pelo WhatsApp? [Clarity, Spec §FR-039b, §FR-039c]

## Endereço e mapas

- [ ] CHK079 Os requisitos declaram que o autocomplete precisa funcionar sem autenticação, dado que o checkout é anônimo? [Gap, Research §R5]
- [ ] CHK080 Está especificado o que acontece quando o serviço de endereço está indisponível — o checkout trava ou aceita endereço não validado? [Gap, Conflict, Spec §FR-015]
- [ ] CHK081 Os requisitos definem limite de uso para proteger a cota do serviço na superfície pública? [Gap, Coverage]

## Falhas atravessadas e recuperação

- [ ] CHK082 Existe requisito que defina o princípio geral: falha de entrega nunca invalida uma venda paga? [Completeness, Gap]
- [ ] CHK083 Os requisitos definem um caminho de recuperação manual para cada falha de integração citada? [Coverage, Spec §FR-037, §FR-038c, §FR-043]
- [ ] CHK084 Está especificado o que é registrado quando uma integração falha, para a equipe entender o motivo sem ler log? [Completeness, Spec §FR-038c]
- [ ] CHK085 Os requisitos definem se pendências de integração aparecem em algum lugar consolidado ou espalhadas por tela? [Gap, Ambiguity]
- [ ] CHK086 Está definido o que acontece com uma campanha inteira se uma integração ficar quebrada por dias — pausar automaticamente ou continuar vendendo? [Gap, Coverage]

## Notes

- Marque `[x]` conforme resolver; anote a decisão na linha.
- Lacuna aqui se corrige em `spec.md` primeiro (Princípio VII), nunca direto no código.
- CHK070 é o item de maior consequência: vídeo com nome de criança acessível por link público é uma decisão de privacidade que a spec hoje não toma explicitamente.
- CHK062 pode virar conflito real: a sincronização existente pode reimportar ou alterar eventos virtuais criados por esta feature.

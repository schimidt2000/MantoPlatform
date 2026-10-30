<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Checklist de integração, segurança e UX: 325 Conversas (WhatsApp)

**Propósito**: testar a qualidade dos requisitos (não a implementação) nas áreas que o dono apontou:
integração externa e segurança (webhook, travas, RBAC, idempotência, LGPD) e UX da tela no celular.
**Created**: 2026-10-30
**Feature**: [spec.md](../spec.md)

**Nota**: gerado pelo `/speckit-checklist` a partir da spec, do plano, da pesquisa e dos contratos.
Profundidade padrão, para revisão (PR). Os itens CHK012 em diante foram avaliados na geração: `[x]` =
o requisito está escrito e claro; os que faltavam foram corrigidos na spec e nos contratos na mesma
rodada (FR-019 a FR-021, limiter e troca de segredo).

## Portões da Manto (fixos — constituição, §Portões de Qualidade)

- [ ] CHK001 `cd frontend && npm run typecheck` limpo (três SPAs)
- [ ] CHK002 `ruff check` limpo nos arquivos Python tocados; `ruff format` só em arquivo novo
- [ ] CHK003 `verify_325.py` verde contra `manto_local`, escrita conferida por conexão separada, um cenário que falha
- [ ] CHK004 Tela aberta de verdade; Conversas conferida também em viewport mobile (375×812)
- [ ] CHK005 Migration manual criada e aplicada no `manto_local`
- [ ] CHK006 `scripts/validar_startcommand.py` — não se aplica (o `startCommand` não muda)
- [ ] CHK007 Gate de RBAC declarado em todo endpoint novo e linha em `docs/01` §4.3
- [ ] CHK008 Docs por fonte única: `docs/01`, `docs/02`, `docs/03`; `00` §3, `04` e `05`
- [ ] CHK009 Nível 1: `/speckit-converge` sem gaps
- [ ] CHK010 Texto novo revisado pelo Princípio XV (superfície interna), lido na tela aberta
- [ ] CHK011 Antes de "em produção": `git status` limpo, `git log -1` = cabeçalho do `docs/03`, sonda `/api/`

## Webhook e autenticação da Meta

- [x] CHK012 Os dois métodos do webhook têm o critério de aceite e de recusa escrito (token do GET, assinatura do POST)? [Completeness, Spec §FR-001, §FR-002]
- [x] CHK013 Está definido o que o webhook responde quando o módulo está desligado, e isso é consistente com o padrão 404 da casa? [Consistency, Spec §FR-015, Contrato]
- [x] CHK014 O tamanho máximo do corpo e o comportamento acima dele estão especificados? [Clarity, Contrato §POST]
- [x] CHK015 O limite de taxa está quantificado e justificado contra rajadas de avisos de status? [Clarity, Contrato §POST]
- [x] CHK016 O procedimento de troca do segredo de assinatura está documentado, incluindo o efeito durante a troca? [Gap → resolvido no Contrato]
- [x] CHK017 Está definido o que acontece com aviso de outro número (outro `phone_number_id`)? [Edge Case, Research §R4]

## Durabilidade e idempotência

- [x] CHK018 O requisito de gravar o aviso cru antes de processar e de reprocessar o que falhou está escrito, com o critério de abandono (48 h / 10 tentativas)? [Completeness, Spec §FR-003, Data model]
- [x] CHK019 A regra de não duplicar mensagem no reenvio da Meta tem a chave de unicidade definida? [Clarity, Spec §FR-006, Research §R5]
- [x] CHK020 A corrida "status chega antes da mensagem" tem um comportamento definido? [Edge Case, Spec §Casos de borda, Research §R5]
- [x] CHK021 A proteção contra clique duplo no envio está especificada como requisito, e não só como detalhe de tela? [Completeness, Spec §FR-018]
- [x] CHK022 A ordem das situações e a regra de "nunca regride" estão escritas, inclusive para "falhou" depois de "entregue"? [Clarity, Spec §FR-009, Data model]
- [x] CHK023 O comportamento da varredura com vários processos ao mesmo tempo está definido sem depender de sorte? [Coverage, Research §R5]

## Travas e configuração (Princípio XIV)

- [x] CHK024 Está especificado o estado "desligado" (sem token) para cada superfície: webhook, envio, menu e tela? [Completeness, Spec §FR-015, §FR-019]
- [x] CHK025 A trava do banco local e o escape explícito estão nomeados, e se aplicam também a "marcar como lida"? [Consistency, Spec §FR-016, Clarifications]
- [x] CHK026 Cada variável nova tem um default declarado (real ou vazio) e uma indicação de segredo × não segredo? [Completeness, Contrato §Configuração]
- [x] CHK027 A ausência de configuração em produção tem aviso no log e registro em `docs/05` previstos? [Completeness, Plan §XIV]

## RBAC e privacidade

- [x] CHK028 Cada endpoint interno tem os papéis declarados, e o arquivo de mídia responde 404 (e não 403) para quem não tem o papel? [Consistency, Spec §RBAC, §FR-008]
- [x] CHK029 O lugar de guarda da mídia está escolhido de modo que ela nunca vire URL pública (bucket público)? [Security, Research §R7]
- [x] CHK030 Está decidido quem fica de fora (Financeiro, Casting) e há um cenário que precisa falhar? [Coverage, Spec §Premissas, Verify 13/18]
- [x] CHK031 O prazo de guarda (LGPD) está explicitamente adiado, com a fase e o registro de dívida? [Assumption, Spec §Premissas]
- [x] CHK032 Está definido se contato desconhecido vira ficha de cliente, e por quê? [Clarity, Spec §Premissas]
- [ ] CHK033 O backup das mídias de conversa tem orçamento de espaço avaliado para o volume real? [Gap — adiado à Fase 4, Research §R7]

## Integração com a Meta (falhas)

- [x] CHK034 Estão separados "a Meta recusou" e "a Meta não respondeu", com o efeito de cada um na mensagem? [Clarity, Research §R8]
- [x] CHK035 Os códigos de erro mais comuns têm motivo legível definido, e há uma regra para os códigos não mapeados? [Completeness, Research §R10]
- [x] CHK036 O teto de tamanho da mídia guardada está quantificado, com o texto do que a equipe vê acima dele? [Clarity, Research §R6]
- [x] CHK037 O nono dígito brasileiro está tratado no vínculo com a ficha e no endereço de resposta? [Edge Case, Spec §FR-005, Research §R11]
- [ ] CHK038 A versão da Graph API e o formato do eco da coexistência estão confirmados contra a documentação vigente? [Dependency, Research §R13 — aguardando a pesquisa]

## UX da tela (celular e computador)

- [x] CHK039 Os estados de carregando, vazio, desligado, erro e mídia pendente ou falha estão definidos com o texto? [Completeness, Spec §FR-019]
- [x] CHK040 O layout no celular está especificado (uma coluna, voltar, caixa fixa, alvos ≥ 44 px, 320–430 px sem rolagem lateral)? [Clarity, Spec §FR-020]
- [x] CHK041 O comportamento do teclado e o feedback do botão de envio estão escritos, incluindo o texto que permanece no erro? [Completeness, Spec §FR-021]
- [x] CHK042 O aviso de "janela fechada" e a troca para "Enviar modelo" estão definidos? [Coverage, Spec §FR-010, §FR-014]
- [x] CHK043 O tempo de atualização da tela está quantificado (SC-001) e coerente com o intervalo de consulta do plano? [Measurability, Spec §SC-001, Plan]
- [x] CHK044 "Tão fácil quanto o WhatsApp Web" tem um critério verificável (piloto do dono)? [Measurability, Spec §SC-006]

## Notas

- CHK033: o volume real só existe na Fase 4. Fica registrado na pesquisa (R7) e vira dívida no
  `docs/05`.
- CHK038: fecha quando a pesquisa externa voltar; o resultado vai para `research.md` §Confirmações.

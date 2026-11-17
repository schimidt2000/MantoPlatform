# Checklist de requisitos: 349 — RBAC, dados e concorrência, UX 390 px e texto

**Purpose**: testar a escrita dos requisitos da 349 nos três pontos de maior risco (fluxo autônomo: foco escolhido
pelo risco, profundidade padrão, para quem revisa o PR).
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md) · [contracts/api.md](../contracts/api.md) · [data-model.md](../data-model.md)

## RBAC e segurança

- [x] CHK001 - O gate de cada rota nova está declarado com os papéis e a função (papel real, não "Ver como")? [Completeness, Spec §RBAC]
- [x] CHK002 - A spec diz o que acontece com o `conversa_id` em `POST /api/events` para quem tem o gate de criar evento — e que o gate não muda? [Clarity, Spec §RBAC, Contrato]
- [x] CHK003 - Existe cenário de recusa por papel para todas as escritas novas (perda, qualificação, lembrete) e para a leitura do painel? [Coverage, Spec §Verificação #17]
- [x] CHK004 - Está explícito que lembrete e régua nunca escrevem na conversa nem falam com a Meta? [Completeness, Spec §FR-021]
- [x] CHK005 - O destinatário de cada aviso está definido, inclusive quando quem marcou perdeu o acesso? [Coverage, Spec §Casos de borda, Data-model §Avisos]

## Dados e concorrência

- [x] CHK006 - "Resposta válida" está definida com a mesma régua da espera (328), incluindo reação, falha e apagada/editada pelo celular? [Clarity, Spec §FR-002]
- [x] CHK007 - A spec cobre a primeira mensagem processada fora de ordem e o recálculo da primeira resposta? [Edge Case, Spec §Casos de borda]
- [x] CHK008 - A corrida Plataforma × eco do celular tem regra (vale a mais antiga, gravação condicional)? [Coverage, Spec §Casos de borda]
- [x] CHK009 - A falha depois do aceite (`failed`) tem efeito definido sobre a primeira resposta? [Exception Flow, Spec §FR-003]
- [x] CHK010 - O envio da equipe antes da primeira mensagem da cliente está excluído explicitamente? [Edge Case, Spec §História 1 #4]
- [x] CHK011 - O preenchimento das conversas existentes está especificado (FR-005) com a mesma régua da gravação viva? [Consistency, Data-model §Preenchimento]
- [x] CHK012 - A idempotência da régua está definida por degrau e por orçamento, e o comportamento depois de dias parada (só o degrau atual) está escrito? [Clarity, Spec §FR-020, Casos de borda]
- [x] CHK013 - "Orçamento parado" tem uma definição única, usada igual pela lista e pela régua? [Consistency, Spec §FR-015]
- [x] CHK014 - A relação perda × criação de evento (reabre) e perda × lembrete (cancela) está escrita sem contradição? [Consistency, Spec §FR-008, §FR-018]
- [x] CHK015 - A edição simultânea de perda/qualificação tem regra declarada? [Coverage, Spec §Casos de borda]
- [x] CHK016 - Os relógios estão definidos (UTC nas colunas da conversa; "amanhã às 9h" e horário dos avisos em São Paulo)? [Clarity, Data-model, Spec §FR-019/§FR-020]
- [x] CHK017 - Os pontos e o corte da qualificação são números, com a origem de cada dado (orçamento × formulário, fato mais recente)? [Measurability, Spec §História 3, §FR-010]
- [x] CHK018 - O funil diz sobre qual base conta perdidas e qualificadas (a coorte) e o que é "até 15 min"? [Clarity, Clarifications, Contrato §funil]

## UX 390 px e texto (§XV)

- [x] CHK019 - A spec fixa a largura de referência (390 px) e "sem rolagem lateral" para lista, faixa da venda e filtros? [Completeness, Spec §Input, Quickstart §4]
- [x] CHK020 - Os estados de carregamento e de erro do painel da venda estão definidos sem esconder a conversa? [Gap → resolvido, Spec §Casos de borda]
- [x] CHK021 - Os estados vazios dos recortes estão escritos no padrão "Nenhum/Nenhuma … ."? [Completeness, Spec §Casos de borda]
- [x] CHK022 - O texto do caso sem autor ("pelo celular, sem autor") está definido para a conversa e para o funil? [Clarity, Spec §História 1, §FR-004]
- [x] CHK023 - Os rótulos dos motivos de perda e dos sinais vêm de uma fonte só (servidor), sem o frontend comparar texto? [Consistency, Data-model §Constantes, Plan §XV]
- [x] CHK024 - Os verbos seguem o glossário (Informar motivo, Selecionar, Cancelar; nada de "Status")? [Consistency, Plan §XV]
- [x] CHK025 - O caminho "Criar evento" sem ficha está definido (abre "Ligar à ficha")? [Alternate Flow, Spec §História 6]
- [x] CHK026 - O caminho de volta da calculadora define o que fica pronto (diálogo aberto e orçamento escolhido) e o limite de requisições? [Measurability, Spec §História 5, §FR-016]

## Dependências e premissas

- [x] CHK027 - A dependência da 348 (coluna `conversa_id`) está fora de escopo e com o ponto de encaixe nomeado? [Dependency, Spec §FR-018, Fora de escopo]
- [x] CHK028 - O efeito do CRM desligado (sem varredura, sem dado) está declarado? [Assumption, Spec §Premissas]
- [x] CHK029 - As decisões tomadas sem o dono estão listadas para ele trocar (motivos, pontos, régua, horário)? [Assumption, Spec §Premissas]

## Notes

- CHK020 e CHK021 eram lacunas; resolvidas na spec (Casos de borda) nesta mesma rodada.

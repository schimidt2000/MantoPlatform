# Checklist de requisitos: privacidade e medição (344)

**Purpose**: testar se os requisitos de contagem, LGPD e pixel estão escritos de forma completa e verificável
**Created**: 2026-11-16
**Feature**: [spec.md](../spec.md)

## Completude
- [x] CHK001 - A spec diz o que é uma "visita" e o que não conta (recarregar na mesma aba)? [Spec §FR-001, Premissas]
- [x] CHK002 - A lista de origens é fechada e diz o que acontece com valor desconhecido? [Spec §FR-002, Casos de borda]
- [x] CHK003 - Está dito o que o aviso de privacidade precisa conter (controlador, finalidade, compartilhamento, prazo, direitos, canal)? [Spec §FR-010]
- [x] CHK004 - Está dito o que acontece com quem comprou antes da 344? [Fora de escopo: sem aceite retroativo]
- [x] CHK005 - A retenção diz a data de referência para cada formato e para pedido não vendido? [Spec §FR-018]

## Clareza
- [x] CHK006 - O texto exato da caixinha está na spec e o estado inicial (desmarcada) é explícito? [Spec §FR-012]
- [x] CHK007 - "Conversão" tem fórmula? [contracts/api.md]
- [x] CHK008 - "Uma única compra por pedido" para a Meta está definido em relação a recarregar a página? [Spec §FR-023, Casos de borda]

## Consistência
- [x] CHK009 - Dados de quem recebe nunca aparecem como destino no CRM, nem na Meta? [Spec §FR-016, §FR-024]
- [x] CHK010 - O pixel desligado por padrão é coerente com a constituição XIV (efeito externo travado por padrão)? [Plan, Constitution Check]

## Cenários de exceção
- [x] CHK011 - Falha da contagem, da ficha do cliente e do Google na limpeza têm comportamento definido? [Spec §FR-007, §FR-017, Casos de borda]
- [x] CHK012 - Página antiga em cache (sem "Seu nome") está coberta? [Clarifications]

## Deploy
- [x] CHK013 - A migration é aditiva e encadeada no head da `main`? [data-model.md]
- [x] CHK014 - Há sonda de produção pós-deploy definida? [quickstart.md]

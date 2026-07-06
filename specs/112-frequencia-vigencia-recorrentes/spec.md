# Feature Specification: Frequência e Vigência dos Gastos Recorrentes

**Feature Branch**: `112-frequencia-vigencia-recorrentes`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "precisa dar para selecionar se é mensal, anual, semanal, ou quinzenal. Data de início e se tem data final ou é eterno."

## Contexto

Ajuste da feature 110/111: hoje toda conta recorrente é implicitamente mensal e vive para
sempre. Contas reais têm ritmo próprio (domínio anual, faxina semanal, serviço quinzenal) e
vigência (contrato do advogado começa/termina; assinatura cancelada). O financeiro precisa
escolher a frequência e o período de vigência de cada conta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Frequência da conta (Priority: P1)

Ao cadastrar/editar uma conta recorrente, o financeiro escolhe a frequência: **mensal**
(padrão, comportamento atual), **semanal**, **quinzenal** ou **anual**.

- Fixos (débito automático/assinatura): o lançamento automático do mês reflete a
  frequência — semanal registra o valor × nº de ocorrências no mês, quinzenal × ocorrências
  das quinzenas, anual só registra no mês de aniversário (mês da data de início).
- Variáveis: o ciclo de alerta segue a frequência — anual só alerta no mês de aniversário;
  semanal/quinzenal continuam com um alerta/lançamento por mês (o boleto do período).

**Acceptance Scenarios**:

1. **Given** assinatura semanal de R$ 100 iniciada antes do mês, **When** o mês é gerado,
   **Then** o lançamento "registrado" vale R$ 100 × nº de semanas (ocorrências do dia da
   semana da data de início) do mês.
2. **Given** débito automático quinzenal de R$ 500, **Then** o lançamento do mês cheio vale
   R$ 1.000.
3. **Given** conta anual (fixa ou variável) com início em março, **Then** só há lançamento/
   alerta em março de cada ano; nos demais meses a conta aparece como "fora do ciclo".
4. **Given** contas mensais existentes, **Then** nada muda (frequência padrão = mensal).

---

### User Story 2 - Vigência: início e fim opcional (Priority: P1)

Cada conta ganha **data de início** (padrão: dia do cadastro) e **data de fim opcional**
(vazia = eterna). Fora da vigência a conta não gera alerta nem lançamento — mas o histórico
dos meses em que esteve vigente permanece.

**Acceptance Scenarios**:

1. **Given** conta com início no mês que vem, **Then** nenhum alerta/lançamento neste mês.
2. **Given** conta com fim no mês passado, **Then** nenhum alerta/lançamento neste mês;
   histórico antigo preservado.
3. **Given** conta sem data de fim, **Then** é eterna (comportamento atual).
4. **Given** fim anterior ao início no formulário, **Then** o cadastro é recusado com
   mensagem clara.
5. **Given** conta semanal iniciada no meio do mês, **Then** o primeiro mês conta apenas as
   ocorrências a partir da data de início.

## Requirements *(mandatory)*

- **FR-001**: Conta recorrente DEVE ter frequência: mensal (padrão) | semanal | quinzenal |
  anual — selecionável no cadastro e na edição.
- **FR-002**: Lançamento automático dos fixos DEVE refletir a frequência (valor × nº de
  ocorrências no mês; anual só no mês de aniversário da data de início).
- **FR-003**: Alertas de conta variável DEVEM respeitar frequência (anual: só no mês de
  aniversário) e vigência.
- **FR-004**: Conta DEVE ter data de início (obrigatória, padrão hoje) e fim opcional
  (vazio = eterna); fora da vigência: sem alerta, sem lançamento novo, histórico intacto.
- **FR-005**: Fim < início DEVE ser rejeitado.
- **FR-006**: Contas existentes DEVEM continuar como mensais eternas (início retroativo à
  data de criação), sem mudança de comportamento.
- **FR-007**: A lista de contas DEVE mostrar frequência e vigência ("desde X", "até Y" ou
  "eterna"), e o mês exibido marca "fora do ciclo/vigência" quando aplicável.

## Success Criteria *(mandatory)*

- **SC-001**: 100% dos lançamentos automáticos de fixos semanais/quinzenais/anuais têm o
  valor correto para o mês (ocorrências × valor).
- **SC-002**: Zero alertas/lançamentos fora da vigência ou fora do mês de aniversário
  (anuais) nos testes.
- **SC-003**: Contas mensais pré-existentes idênticas antes/depois (regressão 110/111).

## Assumptions

- Semanal: âncora = dia da semana da data de início; ocorrências contadas dentro da
  interseção mês × vigência. Quinzenal: quinzenas = janelas dia 1–15 e 16–fim que intersectem
  a vigência no mês (mês cheio = 2).
- Variável semanal/quinzenal mantém UM alerta/lançamento por mês (o total do período) — o
  financeiro preenche o consolidado; granularidade por semana fica fora do escopo.
- Competência do anual: valor cheio no mês de aniversário (sem rateio mensal no DRE); a
  estimativa mensal da tela divide por 12 apenas como referência visual.

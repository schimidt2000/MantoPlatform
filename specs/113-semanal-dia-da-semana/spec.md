# Feature Specification: Conta Semanal — Dia da Semana Explícito

**Feature Branch**: `113-semanal-dia-da-semana`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "Quando seleciono semanal, deve sair o dia do mês para ser selecionado e eu poder selecionar qual o dia da semana."

## Contexto

Ajuste da feature 112: na frequência semanal, o dia da semana da cobrança era derivado
implicitamente da data de início — invisível e confuso. O financeiro deve escolher o dia da
semana explicitamente; o campo "Dia" (do mês) some quando a frequência é semanal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Selecionar o dia da semana (Priority: P1)

Ao escolher frequência "Semanal" no cadastro/edição, o campo "Dia" (1–31) desaparece e no
lugar aparece um seletor de dia da semana (segunda a domingo). As ocorrências do mês, o
vencimento exibido e os alertas passam a usar esse dia da semana.

**Acceptance Scenarios**:

1. **Given** frequência Semanal selecionada no formulário, **Then** o campo de dia do mês
   some e o seletor de dia da semana aparece (e vice-versa ao voltar para outra frequência).
2. **Given** assinatura semanal de R$ 100 na quarta-feira, **Then** o lançamento do mês vale
   R$ 100 × nº de quartas do mês (na vigência) e o vencimento exibido é a primeira quarta.
3. **Given** conta semanal salva sem dia da semana, **Then** o cadastro é recusado com
   mensagem clara.
4. **Given** conta variável semanal, **Then** o alerta da home começa na primeira ocorrência
   do dia da semana no mês e o texto mostra "toda semana (quarta)" em vez de "dia N".
5. **Given** contas semanais criadas na 112 (sem dia explícito), **Then** continuam usando o
   dia da semana da data de início (preenchido automaticamente na migração).
6. **Given** contas mensais/quinzenais/anuais, **Then** nada muda (campo Dia continua).

## Requirements *(mandatory)*

- **FR-001**: Frequência semanal DEVE exigir a escolha do dia da semana (segunda–domingo) e
  ocultar o dia do mês no formulário (cadastro e edição).
- **FR-002**: Ocorrências, valor do lançamento automático, vencimento exibido e início do
  alerta DEVEM usar o dia da semana escolhido.
- **FR-003**: Rótulos (lista e alerta) DEVEM mostrar o dia da semana ("toda semana (…)").
- **FR-004**: Contas semanais existentes DEVEM ser migradas para o dia da semana da sua data
  de início; demais frequências inalteradas.

## Success Criteria *(mandatory)*

- **SC-001**: 100% dos lançamentos semanais refletem o dia da semana escolhido (valor e
  vencimento corretos nos testes).
- **SC-002**: Zero regressão nas demais frequências (testes da 112 equivalentes passam).

## Assumptions

- O dia do mês (`due_day`) fica irrelevante para semanais (gravado como 1 por padrão, sem
  exibição); o alerta semanal dispara a partir da primeira ocorrência do dia da semana no
  mês dentro da vigência.

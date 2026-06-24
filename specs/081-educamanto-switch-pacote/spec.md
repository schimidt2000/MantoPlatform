# Feature Specification: Trocar de plano sem perder a configuração (valor da tela = PDF)

**Feature Branch**: `081-educamanto-switch-pacote`

**Created**: 2026-06-23

**Status**: Draft

**Input**: "No Aventura Animal Master: 1 dia/1 sessão, Campinas calculado, 1000 de acréscimo, e gero o
PDF para Master/Intermediário/Econômica — dá um valor para todos. Mas se eu, na página principal,
mudo para o plano Intermediário ou Básico, dá outro valor. Tem algo errado."

## Contexto

No EducaManto, o PDF calcula o valor de **cada** plano usando a configuração preenchida (dias,
ensemble, transporte, acréscimo). Porém, ao **trocar de plano** no seletor da página principal, a
página **recarregava** e **perdia** os dados preenchidos (dias, transporte, acréscimo) — então o
valor mostrado para o Intermediário/Econômica ficava **diferente** do que o PDF gerou. A causa é a
troca de plano recarregar a página em vez de recalcular com os mesmos dados.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trocar de plano mantém a configuração (Priority: P1) 🎯 MVP

Como vendedor, quero trocar de plano no seletor e ver o valor recalculado **com os mesmos dados** que
preenchi (dias, transporte, acréscimo), batendo com o valor que o PDF gera para aquele plano.

**Independent Test**: Com 1 dia/1 sessão, Campinas calculado e R$ 1.000 de acréscimo no Master,
trocar o seletor para Intermediário → o valor exibido é **igual** ao da página do Intermediário no
PDF (mesmos dados), e **não** zera/recarrega.

**Acceptance Scenarios**:

1. **Given** uma configuração preenchida no Master, **When** troco o seletor para Intermediário,
   **Then** os dias/transporte/acréscimo são **mantidos** e o valor recalcula para o Intermediário.
2. **Given** o mesmo cenário, **When** comparo o valor da tela com o do PDF para aquele plano,
   **Then** são **iguais**.
3. **Given** que troco de plano, **When** a página troca, **Then** **não há recarregamento** (a
   configuração não é perdida).

### Edge Cases

- O acréscimo continua limitado ao valor original **de cada plano** (cap por plano), de forma
  **igual** na tela e no PDF — sem reescrever o valor digitado ao trocar de plano.
- "Editar pacote" (super admin) passa a apontar para o plano atualmente selecionado.
- Atualizar a página manualmente mantém o plano selecionado (URL acompanha).

## Requirements *(mandatory)*

- **FR-001**: Trocar de plano no seletor MUST recalcular **sem recarregar** a página, **preservando**
  dias, ensemble, transporte e acréscimo.
- **FR-002**: O valor exibido para um plano MUST ser **igual** ao valor do mesmo plano no PDF, para a
  mesma configuração.
- **FR-003**: O cap do acréscimo (≤ valor original) MUST ser aplicado **por plano**, de forma
  idêntica na tela e na geração do PDF; o valor digitado **não** é reescrito ao trocar de plano.
- **FR-004**: O link "Editar pacote" (super admin) MUST refletir o plano selecionado.

## Success Criteria *(mandatory)*

- **SC-001**: Trocar de plano não recarrega a página e mantém os dados; o valor recalcula na hora.
- **SC-002**: Para a mesma configuração, o valor de cada plano na tela é idêntico ao do PDF.
- **SC-003**: O cap do acréscimo é consistente entre tela e PDF (por plano).

## Assumptions

- Os dados de todos os planos já estão disponíveis no cliente (não precisa ir ao servidor para
  trocar de plano).
- Apenas a calculadora do EducaManto; sem modelo, sem migration.

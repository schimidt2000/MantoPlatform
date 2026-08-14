# Feature Specification: Cachê sugerido pela duração real do evento

**Feature Branch**: `236-cache-por-duracao`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Cachê sugerido por duração real do evento: corrigir o bug do teto de cachê que cai no valor de 1 hora quando o evento tem duração fora de 1–4h (fallback do dur_idx na criação de evento a partir do orçamento), e estender a régua de cachês para qualquer duração — até 4h usa a tabela; acima de 4h o cachê-base do papel é (valor de 4h ÷ 4) × horas, com adicionais fixos somados por fora (R$ 20 de maquiagem, R$ 50 de adicional noturno, que é repasse ao artista); o evento criado do orçamento nasce com cache_value e cache_cap pré-preenchidos pela duração real (incluindo 5h/6h+), e a tela de casting mostra a referência e avisa quando o lançado fica abaixo ou acima do sugerido. O preço ao cliente não muda."

## Contexto

Quando um evento nasce de um orçamento, cada papel já recebe um cachê pré-preenchido e um teto
(`cache_cap`) vindos da tabela de cachês do orçamento — mas só existem valores para 1–4 horas, e a
criação usa um mapa `{"1","2","3","4"}` com **fallback no índice 0**: qualquer duração fora desse
conjunto (5h, 6h…) preenche os papéis com o cachê de **1 hora**. Foi exatamente o que espremeu o
casting no caso real do Baile do Addan (evento de 22h–4h = 6 horas, dia 15/08): o preço ao cliente
escala por hora (total de 4h ÷ 4 × horas), mas o valor das pessoas ficou travado no menor da
tabela. O dono definiu a régua que fecha a conta dos dois lados e pediu que ela passe a viajar
junto com o evento.

## Decisões já tomadas com o dono do produto

Registradas na conversa de 14/08/2026:

1. **Régua do cachê por duração**: até 4h vale a **tabela** da duração; acima de 4h o cachê-base
   do papel é **(valor-base de 4h ÷ 4) × horas**. Ex.: base 300 em 6h → 450.
2. **Adicionais fixos somam por fora e não escalam por hora**: diferença de maquiagem (hoje
   R$ 20) e adicional noturno (R$ 50, evento a partir das 19h) entram inteiros por cima do
   cachê-base. Ex.: base 300, 6h, com make → 450 + 20 = 470 (+50 se noturno).
3. **O adicional noturno é repasse ao artista**: os R$ 50 cobrados do cliente por pessoa
   pertencem ao cachê da pessoa e devem aparecer no valor sugerido.
4. **O evento nasce preenchido**: papéis criados a partir do orçamento já vêm com o cachê
   sugerido da duração REAL preenchido (editável) e com o teto correspondente — em qualquer
   duração, incluindo 5h/6h+.
5. **O preço ao cliente não muda** nesta feature (a regra `total de 4h ÷ 4 × horas` do orçamento
   permanece como está).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Evento longo nasce com cachês da duração real (Priority: P1)

O comercial fecha um evento de 6 horas a partir de um orçamento. Ao criar o evento, cada papel
nasce com o cachê sugerido calculado para 6 horas pela régua (base de 4h ÷ 4 × 6 + adicionais
fixos) — e não mais com o valor de 1 hora. O teto de cada papel acompanha o mesmo número.

**Why this priority**: é o bug que causou o caso real — o valor ao cliente sobe com as horas e o
lado das pessoas ficava no menor valor da tabela. Sem isso, todo evento longo nasce errado.

**Independent Test**: criar evento de 6h a partir de um orçamento com 1 ator (base 300, com make)
e conferir cachê e teto = 470 (+50 se ≥19h).

**Acceptance Scenarios**:

1. **Given** um orçamento com um ator cara limpa com maquiagem (base 4h = 300, make = 20),
   **When** o evento é criado com duração de 6 horas, **Then** o papel nasce com cachê sugerido e
   teto de 450 + 20 = 470 (mais o noturno, se aplicável).
2. **Given** o mesmo orçamento, **When** o evento é criado com duração de 2 horas, **Then** o
   papel nasce com o valor da tabela de 2h (comportamento atual preservado).
3. **Given** duração de 5 horas (o caso que hoje cai no fallback), **When** o evento é criado,
   **Then** nenhum papel recebe o valor de 1 hora — todos usam a régua de 5h.

---

### User Story 2 - Adicional noturno viaja com o cachê (Priority: P2)

Um evento começa às 22h. O orçamento cobra R$ 50 de adicional noturno por pessoa do cliente; como
esse valor é repasse, o cachê sugerido de cada pessoa no evento já nasce com os R$ 50 somados —
o casting não precisa lembrar de acrescentar na mão.

**Why this priority**: fecha o segundo furo dos casos reais (mascotes: o dono somou os 50 na mão
em cada cachê). Depende da mesma mecânica da US1.

**Independent Test**: criar evento às 22h e conferir que cada cachê sugerido = régua da duração
+ 50; criar às 15h e conferir que não soma.

**Acceptance Scenarios**:

1. **Given** um evento criado de orçamento com início 19h ou mais tarde, **When** os papéis são
   criados, **Then** cada cachê sugerido inclui + R$ 50 de noturno.
2. **Given** início antes das 19h, **When** os papéis são criados, **Then** nenhum noturno é
   somado.

---

### User Story 3 - Casting enxerga a referência e os desvios (Priority: P3)

Na tela do evento, o casting vê ao lado de cada cachê o valor de referência da duração real.
Quando lança um valor **acima** do teto, o aviso atual continua; quando lança **abaixo** da
referência, passa a ver um aviso de que a pessoa está recebendo menos que o sugerido — os dois
desvios ficam visíveis, nenhum é bloqueado.

**Why this priority**: transparência para o caso "seguraram o cachê porque parecia o limite";
depende das duas anteriores para a referência existir.

**Independent Test**: num evento com referência 470, lançar 460 e ver o aviso de "abaixo do
sugerido"; lançar 500 e ver o aviso de "acima do teto"; lançar 470 e não ver aviso.

**Acceptance Scenarios**:

1. **Given** um papel com referência 470, **When** o casting lança 460, **Then** aparece um aviso
   informativo de valor abaixo do sugerido (sem bloqueio).
2. **Given** o mesmo papel, **When** lança acima do teto, **Then** o aviso atual de "acima do
   teto" continua funcionando.
3. **Given** um papel de evento criado sem orçamento (sem referência), **When** o casting lança
   qualquer valor, **Then** nenhum aviso de referência aparece (comportamento atual).

---

### Edge Cases

- Duração fora do padrão já na criação (7h, 8h…): a régua vale para qualquer inteiro > 4.
- Papel adicionado manualmente depois da criação: sem referência (não veio do orçamento) — sem
  avisos de referência.
- Evento criado sem orçamento: nada muda (papéis nascem vazios como hoje).
- Orçamentos antigos: a referência é calculada na CRIAÇÃO do evento; eventos já criados não são
  recalculados retroativamente.
- Horário/duração editados depois da criação: a referência gravada não muda (assumption — ver
  Assumptions).
- Cantor (estrutura base + extras) e especiais (listas próprias): a régua usa o valor de 4h do
  papel como está na tabela do orçamento, qualquer que seja a composição interna.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O cachê sugerido de um papel DEVE ser: tabela da duração para 1–4h; para durações
  acima de 4h, (valor-base de 4h ÷ 4) × horas — onde valor-base é o valor do papel SEM os
  adicionais fixos.
- **FR-002**: Os adicionais fixos DEVEM somar inteiros por cima do cachê-base, sem escalar por
  hora: diferença de maquiagem (valor vigente da tabela, hoje R$ 20) quando o papel tem make, e
  adicional noturno (valor vigente, hoje R$ 50) quando o evento começa às 19h ou mais tarde.
- **FR-003**: A criação de evento a partir de orçamento DEVE preencher `cache_value` e
  `cache_cap` de cada papel com o cachê sugerido da duração REAL do evento, para QUALQUER
  duração — o fallback que hoje aplica o valor de 1 hora a durações fora de 1–4h DEVE ser
  eliminado.
- **FR-004**: O valor pré-preenchido DEVE continuar editável pelo casting (é sugestão com teto,
  não trava).
- **FR-005**: A tela de casting DEVE exibir a referência do papel (quando existir) e avisar,
  sem bloquear: valor lançado acima do teto (aviso atual) e valor lançado abaixo da referência
  (aviso novo).
- **FR-006**: Papéis sem origem em orçamento (evento manual, papel adicionado depois) DEVEM
  continuar sem referência e sem avisos de referência.
- **FR-007**: O preço ao cliente NÃO muda nesta feature — nenhuma alteração na fórmula de
  totais do orçamento (1–4h ou duração extra).
- **FR-008**: A regra do noturno DEVE usar o mesmo critério que o orçamento usa para cobrar o
  adicional do cliente (início às 19h ou mais tarde), para os dois lados ficarem espelhados.

### Key Entities

- **Papel do evento (EventRole)**: já tem `cache_value` (lançado) e `cache_cap` (teto do
  orçamento); passa a ser preenchido pela régua da duração real. Sem campos novos previstos —
  a referência exibida é o próprio `cache_cap`.
- **Cachês por papel do orçamento**: a lista por duração (1h–4h) que o orçamento entrega à
  criação do evento, estendida com o valor calculado da duração real quando > 4h.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Evento de 6h criado de orçamento com ator base 300 + make nasce com cachê e teto
  de exatamente 470 (+50 quando noturno) — hoje nasce com o valor de 1h.
- **SC-002**: Nenhuma duração de criação (1h a 12h) resulta em papel com cachê de uma duração
  diferente da escolhida — 100% dos casos de teste da régua batem.
- **SC-003**: Evento iniciando ≥19h nasce com +R$ 50 em cada cachê sugerido; antes das 19h,
  nenhum papel ganha o adicional.
- **SC-004**: No casting, lançar abaixo da referência mostra o aviso novo e lançar acima do teto
  mantém o aviso atual — verificável nas duas direções no app real.
- **SC-005**: Eventos criados sem orçamento seguem byte-a-byte o comportamento atual (sem
  referência, sem avisos).

## Assumptions

- A duração usada para a régua é a informada na criação do evento (o mesmo número que já escolhe
  o preço do cliente); se horário/duração forem editados depois, a referência gravada não é
  recalculada — recalcular retroativamente fica fora do escopo.
- A referência exibida ao casting é o próprio teto (`cache_cap`) — não se cria campo novo.
- Durações fracionadas não existem no fluxo de criação atual (horas inteiras); a régua opera
  sobre horas inteiras.
- Casos reais de validação: evento 1235 (Baile do Addan, 6h, 22h–4h) e 1205 (mascotes, 2h,
  19h) — os números lançados manualmente pelo dono são o gabarito da régua.
- Tabelas de cachês continuam editáveis nas Configurações de Preços; a régua sempre lê os
  valores vigentes (nada de constantes novas).

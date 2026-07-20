# Feature Specification: Salvar talento e cachê do casting de forma confiável

**Feature Branch**: `138-salvar-cache-talento-evento`

**Created**: 2026-07-20

**Status**: Draft

**Input**: User description: "no evento quando o casting vai colocar uma pessoa e o valor e clica em salvar, acaba salvando a pessoa e nao o valor e vice versa. Isso é muito ruim, não fica prático. Preciso que resolva isso reformulando a arquitetura, pois acredito que seja uma limitação de arquitetura."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escalar um talento com o cachê certo, de uma vez só (Priority: P1)

Alguém do Casting abre a página do evento, busca e escolhe um talento para um personagem,
digita o valor do cachê e clica em "Salvar". Hoje, às vezes só o talento é salvo (o cachê
some/zera) ou só o cachê é salvo (o talento não fica escalado) — mesmo os dois campos
tendo sido preenchidos na mesma ação. Isso obriga a pessoa a conferir e salvar de novo,
quebrando a confiança na tela.

**Why this priority**: É o fluxo mais usado do módulo de Casting (escalar elenco de todo
evento) e a falha relatada acontece nesse exato caminho — é o problema central relatado
pelo usuário.

**Independent Test**: Escalar um talento novo com um valor de cachê em um personagem vazio
e confirmar, após salvar uma única vez, que TANTO o talento quanto o valor do cachê
aparecem corretamente salvos — sem precisar salvar de novo.

**Acceptance Scenarios**:

1. **Given** um personagem sem talento nem cachê definidos, **When** o Casting busca e
   seleciona um talento, digita um valor de cachê e clica em "Salvar" uma única vez,
   **Then** tanto o talento quanto o valor do cachê ficam salvos corretamente.
2. **Given** um personagem que já tem talento e cachê salvos, **When** o Casting troca só
   o talento (sem mexer no campo de cachê) e salva, **Then** o cachê anterior continua
   salvo do jeito que estava (não é apagado por engano).
3. **Given** um personagem que já tem talento e cachê salvos, **When** o Casting troca só
   o valor do cachê (sem mexer no talento) e salva, **Then** o talento continua o mesmo
   (não é removido por engano).
4. **Given** o Casting digitou o nome de um talento na busca mas NÃO chegou a selecioná-lo
   na lista de sugestões (ex.: clicou fora, ou apertou "Salvar" direto), **When** ele
   clica em "Salvar", **Then** o sistema NÃO salva silenciosamente sem o talento — avisa
   claramente que é preciso selecionar um talento da lista antes de salvar, sem perder o
   que já foi digitado.

---

### Edge Cases

- Personagem que já tinha um cachê salvo e o Casting decide remover o talento (deixar sem
  ninguém escalado): comportamento continua sendo apagar a associação, mas o valor do
  cachê digitado nesse mesmo salvamento (se houver) ainda deve ser respeitado.
- Cachê acima do teto do orçamento (regra já existente do cap): continua funcionando igual
  a hoje — essa validação não é afetada por esta correção.
- Duplo clique rápido em "Salvar" (ação repetida antes da resposta do primeiro clique):
  não pode gerar um segundo salvamento com dados desatualizados por cima do primeiro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Ao clicar em "Salvar" num personagem/vaga do evento, o sistema MUST
  persistir a escolha de talento E o valor do cachê preenchidos naquele momento na tela,
  juntos, numa única ação — nunca aplicar só um dos dois quando ambos foram informados.
- **FR-002**: O sistema MUST impedir que um campo deixado sem alteração (não tocado pelo
  usuário naquele salvamento) seja apagado/zerado por engano — só muda o que o usuário
  efetivamente alterou na tela antes de clicar em "Salvar".
- **FR-003**: Se o usuário digitou um nome no campo de busca de talento mas não confirmou
  a seleção de ninguém da lista, o sistema MUST bloquear o salvamento e avisar de forma
  clara e visível que é preciso escolher um talento da lista — sem apagar o texto já
  digitado nem os outros campos preenchidos (mesmo padrão de validação já usado em outras
  telas do sistema: erro visível, sem perder o que foi digitado).
- **FR-004**: O resultado do salvamento (o que foi de fato gravado: talento e/ou cachê)
  MUST ficar visível na tela imediatamente após a ação, para o Casting confirmar de
  imediato que os dois valores pretendidos foram mesmo salvos.
- **FR-005**: Cliques repetidos em "Salvar" na mesma vaga MUST resultar sempre no último
  estado preenchido pelo usuário — nunca num resultado misto entre dois cliques diferentes
  nem numa duplicação de efeito colateral (ex.: convite enviado duas vezes).

### Key Entities

- **Escalação (papel/vaga do evento)**: já modelada hoje — associação entre um evento, um
  personagem/função e, opcionalmente, um talento e um valor de cachê. Esta feature não
  cria entidade nova; corrige a confiabilidade de como os dois campos (talento e cachê)
  chegam salvos juntos a partir de uma única ação de salvar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ao escalar um talento com cachê num único "Salvar", 100% das vezes tanto o
  talento quanto o valor do cachê ficam corretamente salvos (elimina o problema relatado
  de "salva um e não o outro").
- **SC-002**: Nenhum salvamento apaga um valor que o usuário não tocou naquele momento —
  zero casos de cachê ou talento "sumindo" sem o usuário ter mexido naquele campo.
- **SC-003**: O Casting nunca precisa salvar a mesma vaga duas vezes seguidas para garantir
  que os dois dados (pessoa e valor) ficaram registrados.

## Assumptions

- Investigação no código atual (antes de planejar a correção) mostrou que a causa raiz não
  é uma limitação estrutural do banco de dados ou da rota que salva (que já grava talento e
  cachê juntos, na mesma operação) — e sim dois comportamentos de interface que juntos
  produzem exatamente o sintoma relatado: (1) o campo de busca de talento só realmente
  "seleciona" alguém quando o usuário clica/confirma um nome da lista de sugestões —
  digitar o nome sem confirmar não atualiza a escolha por trás; e (2) o campo de cachê,
  se enviado vazio, hoje apaga silenciosamente qualquer valor que já existia, mesmo que o
  usuário só quisesse mexer no talento. A correção é focada em fechar essas duas brechas
  de interface (deixando claro quando uma seleção não foi confirmada, e não apagando o que
  não foi tocado) — não em redesenhar como o dado é guardado, que já é confiável.
- Fora de escopo: mudar a regra do teto de cachê (cap do orçamento), o fluxo de convite ao
  talento (e-mail/WhatsApp) ou o cadastro de personagens/vagas — nada disso foi apontado
  como problema.
- Este mesmo padrão de campo (busca de talento + valor ao lado, um botão "Salvar") também é
  usado na seção "Equipe de Apoio" do evento — a correção se aplica igualmente lá, por
  reaproveitar o mesmo componente.

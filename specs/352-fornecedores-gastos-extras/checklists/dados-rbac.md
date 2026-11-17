# Checklist de requisitos: dados, RBAC e importação — 352

**Purpose**: testar se a spec e o plano definem sem ambiguidade a regra de "mesmo fornecedor", o que o
gasto guarda × o que o cadastro guarda, quem pode o quê e a migration que reescreve nomes.
**Created**: 2026-11-17 · **Profundidade**: padrão · **Público**: revisor do PR
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

## Regra de "mesmo fornecedor"

- [x] CHK001 - A regra de igualdade de nomes diz exatamente o que se ignora (acento, maiúscula, espaço, pontuação), a ponto de decidir qualquer par de grafias? [Clarity, Spec §FR-002, Plan §1]
- [x] CHK002 - A igualdade é garantida pela base de dados, e não só pela tela? [Completeness, Spec §FR-002]
- [x] CHK003 - A spec diz qual nome o gasto passa a exibir quando liga a um fornecedor pelo nome digitado em outra grafia (o do cadastro, não o digitado)? [Clarity, Spec §FR-005] — corrigido na spec nesta rodada
- [x] CHK004 - Está definido o que acontece quando a pessoa escolhe uma sugestão e depois altera o texto do nome? [Gap, Spec §Casos de borda] — incluído nesta rodada
- [x] CHK005 - Está definido o que acontece quando o nome digitado é o de um fornecedor arquivado? [Edge Case, Spec §Casos de borda]
- [x] CHK006 - A corrida de duas pessoas cadastrando o mesmo fornecedor está coberta? [Coverage, Spec §Casos de borda]

## O que o gasto guarda × o que o cadastro guarda

- [x] CHK007 - Está escrito que o gasto guarda o nome e a chave PIX do lançamento e que é isso que a Planilha de Pagamentos lê? [Completeness, Spec §FR-007, Entidades]
- [x] CHK008 - O efeito de renomear sobre gastos já pagos está definido? [Clarity, Spec §FR-008, História 4]
- [x] CHK009 - O efeito de corrigir o PIX no cadastro sobre gastos lançados e ainda não pagos está decidido explicitamente? [Clarity, Spec §FR-007, Fora de escopo]
- [x] CHK010 - A regra "completa o que falta, nunca substitui" está definida para PIX e para categoria? [Consistency, Spec §FR-006, História 2]
- [x] CHK011 - A devolução à cliente (mesmos campos de nome/PIX) está excluída do vínculo, do cadastro automático e da importação? [Coverage, Spec §Casos de borda, História 3]
- [x] CHK012 - Está definido o que acontece com o vínculo quando o gasto deixa de ser "Pagamento a fornecedor"? [Edge Case, Spec §Casos de borda]
- [x] CHK013 - Está dito que renomear ou juntar não marca o gasto como "aprovado com edições"? [Gap, Plan §4]

## RBAC

- [x] CHK014 - Cada endpoint novo tem papel declarado, inclusive o que o não gestor recebe no `GET`? [Completeness, Spec §RBAC, FR-012]
- [x] CHK015 - A exposição da chave PIX a quem lança gasto está registrada como premissa aceita? [Assumption, Spec §Premissas]
- [x] CHK016 - O comportamento com "Ver como" (impersonação) está definido para os gates novos? [Gap, Spec §Premissas] — incluído nesta rodada
- [x] CHK017 - O caminho antigo (Jinja) de criar gasto está coberto pela mesma regra? [Coverage, Spec §Casos de borda]
- [x] CHK018 - Há um cenário de autorização que deve falhar? [Measurability, Spec §Verificação #9]

## Importação do histórico (migration)

- [x] CHK019 - As chaves de agrupamento (PIX normalizada e nome normalizado) estão definidas, inclusive como se normaliza CPF/CNPJ/telefone/e-mail? [Clarity, Spec §Premissas, Plan §2]
- [x] CHK020 - A regra do nome para grafias que surgirem depois de 17/11 (fora da tabela) está definida? [Coverage, Spec §Premissas]
- [x] CHK021 - Está decidido se gastos rejeitados entram na importação? [Gap, Spec §História 3] — incluído nesta rodada
- [x] CHK022 - A colisão de um nome arrumado com o de outro grupo está tratada? [Edge Case, Plan §7]
- [x] CHK023 - O resultado esperado é mensurável (fornecedores, zero gastos sem vínculo)? [Measurability, Spec §SC-002, Plan §7]
- [x] CHK024 - O downgrade e a perda das grafias originais estão documentados? [Recovery, Data-model §Downgrade]
- [x] CHK025 - A regra de não pôr chave PIX nem documento no repositório está explícita para a tabela de grafias? [Non-Functional, Spec §Premissas, Plan §Rastreamento]

## Consistência

- [x] CHK026 - O código de erro do nome duplicado é o mesmo na spec (verify #8) e no contrato (400 `fields.nome`)? [Consistency, Contracts]
- [x] CHK027 - "Juntar" (o duplicado deixa de existir) e "Arquivar" usam os verbos do glossário sem conflito com "Excluir"/"Remover"? [Consistency, Constituição XV]

## Notas

- **Risco aceito, sem requisito**: um gasto salvo exatamente no instante em que o seu fornecedor está
  sendo juntado a outro pode falhar no salvamento (a trava do juntar segura a linha que o gasto
  referencia). A pessoa salva de novo e o gasto liga pelo nome. Com a equipe atual (um Financeiro), o
  cruzamento é improvável; não vale uma trava a mais no caminho de todo gasto.
- Rodada única: 27 itens, 23 já atendidos, 4 corrigidos na spec (CHK003, CHK004, CHK016, CHK021).

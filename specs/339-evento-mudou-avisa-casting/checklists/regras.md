# Checklist de requisitos: regras de teto, título, Ciente, efeitos externos e texto

**Propósito**: testar se a spec da 339 está escrita de forma completa, clara e consistente nos cinco
focos pedidos (teto, contagem do título, RBAC do Ciente, Google/e-mail, texto pt-BR) — antes do
`/speckit-tasks`.
**Criado**: 2026-11-09 · **Profundidade**: padrão · **Público**: revisão antes do implement
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md)

Itens marcados `[x]` passaram; os que falharam foram corrigidos na spec no mesmo commit (nota em cada
um).

## Teto do cachê

- [x] CHK001 - O "teto efetivo" tem uma fórmula única que vale para a trava e para a tela, e a relação com o cachê já salvo da pessoa atual está explícita? [Clarity, Conflict, Spec §FR-002] — *falhou*: o FR-002 dizia "não depende do cachê da pessoa", e o plano mantém o cachê atual como piso (regra da 238). Corrigido: o FR-002 diz as duas coisas.
- [x] CHK002 - As condições que gravam e que limpam o teto autorizado cobrem salvar sem pessoa e com cachê vazio? [Completeness, Spec §FR-001, FR-003, FR-004] — *falhou*: só a troca de pessoa estava coberta. Corrigido no FR-003.
- [x] CHK003 - Está definido o que acontece quando o Superadmin salva um valor numa vaga sem teto de orçamento? [Edge Case, Gap] — *falhou*. Corrigido em "Casos de borda".
- [x] CHK004 - "Mesmo perfil" está definido para cada tipo de vaga do recálculo, inclusive as de som criadas pela troca? [Clarity, Spec §Premissas, FR-007] — *falhou* para o Técnico de Som (vaga criada pela troca, sem teto). Corrigido no FR-007.
- [x] CHK005 - Sair de SHOW é consistente com o piso do autorizado e com "cachê não muda sozinho"? [Consistency, Spec §FR-008, FR-009, FR-010]
- [x] CHK006 - A precedência entre recálculo pela tabela e orçamento vinculado está definida nos dois sentidos (vínculo antes ou depois da troca)? [Consistency, Spec §FR-007, FR-025]
- [x] CHK007 - Está dito como fica um cachê já salvo que passa a ficar acima do teto rebaixado (saída de SHOW)? [Edge Case, Gap] — *falhou*. Corrigido em "Casos de borda".

## Contagem do título

- [x] CHK008 - A normalização que compara nome de vaga e segmento do título está especificada (acento, caixa, espaços, prefixo de tipo, nomes reservados)? [Clarity, Spec §Premissas]
- [x] CHK009 - "O que saiu do título" vale para todas as portas que mudam o título (sync, Editar, Básico) e exclui a reescrita do próprio sistema? [Coverage, Spec §FR-018, FR-032]
- [x] CHK010 - As condições de reescrita do título na remoção e na inclusão de vaga são desigualdades testáveis? [Measurability, Spec §FR-027, FR-028]
- [x] CHK011 - Com várias vagas vazias elegíveis, a escolha de qual sai é determinística? [Clarity, Spec §FR-019]
- [x] CHK012 - O caso misto (o excedente é maior que o número de vagas vazias) está definido? [Edge Case, Spec §FR-019, FR-020] — *falhou*: o FR-020 falava só em "todas ocupadas". Corrigido.
- [x] CHK013 - Está claro se a marca vai em todas as vagas ocupadas do personagem ou só no excedente? [Clarity, Spec §FR-020]
- [x] CHK014 - A relação entre o "Editar" (título e elenco juntos) e a regra da vaga a mais está definida? [Consistency, Spec §FR-018, FR-028]
- [x] CHK015 - "Ensaio ainda não realizado" está definido (início no futuro, ensaio cancelado)? [Clarity, Spec §FR-030] — *falhou*: o cancelado não era citado. Corrigido.

## "Ciente" e RBAC

- [x] CHK016 - O "Ciente" por pessoa e a independência do "lida" do sino estão explícitos? [Clarity, Spec §FR-014, FR-015]
- [x] CHK017 - O 404 cobre aviso de outra pessoa e aviso de tipo sem "Ciente"? [Completeness, Spec §FR-016, contracts/api.md]
- [x] CHK018 - A visibilidade do cachê na faixa está definida por papel (o Ensaio não vê cachê hoje)? [Consistency, Spec §FR-012] — *falhou*: o FR-012 mandava o cachê a todos os destinatários. Corrigido: segue o corte de cachê que o elenco já tem.
- [x] CHK019 - O "Ver como" não troca a caixa nem a faixa? [Coverage, Spec §Premissas]
- [x] CHK020 - "Quem fez a mudança" está definido para mudança vinda do Google? [Clarity, Spec §FR-033]
- [x] CHK021 - Está definido o que acontece com os avisos pendentes quando o evento é cancelado? [Gap] — *falhou*. Corrigido em "Casos de borda".

## Google e e-mail

- [x] CHK022 - Os efeitos externos de cada ação (Google, e-mail) estão listados, com o comportamento na falha? [Completeness, Spec §FR-031] — *falhou*: o plano acrescentou o e-mail ao Ensaio na troca para SHOW (R3), que a spec não tinha. Corrigido com o FR-034 (Living Spec).
- [x] CHK023 - Está explícito que nenhuma remoção ou marca automática manda e-mail a artista? [Completeness, Spec §FR-020, FR-023, SC-004]
- [x] CHK024 - O evento marcado "Sumiu do Google Agenda" (303) tem regra para o ajuste do título? [Edge Case, Gap] — *falhou*. Corrigido em "Casos de borda".
- [x] CHK025 - As regras do evento cancelado (312) são consistentes com a remoção de vaga e o ajuste do título? [Consistency, Spec §Casos de borda]

## Texto (Princípio XV)

- [x] CHK026 - Os textos que a equipe lê (sino, faixa, marca no card, avisos da resposta) estão escritos na spec, no tom da superfície interna? [Clarity, Gap] — *falhou*: só havia frases soltas. Corrigido com a seção "Textos".
- [x] CHK027 - O verbo para tirar alguém da vaga segue o glossário ("Remover da escala"; "Dispensar" é outro termo de domínio, a tarefa de casting)? [Consistency] — *falhou* no card ("tire alguém"). Corrigido para "Remova alguém da escala" nos textos.
- [x] CHK028 - O Casting nunca lê o número do teto nem a palavra "teto" (decisão da 215; para ele é "limite")? [Consistency, Spec §FR-006]

## Rastreabilidade

- [x] CHK029 - Os critérios de sucesso são mensuráveis sem conhecer a implementação? [Measurability, Spec §SC-001..006]
- [x] CHK030 - Todo FR tem um cenário do verify que o prova? [Traceability] — *falhou* para FR-013 e FR-034. Corrigido na tabela (cenários 5 e 7).

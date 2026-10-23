# Checklist: vínculo, dinheiro e leitura — Feature 318

**Purpose**: testar a qualidade dos requisitos da regra de vínculo, da contagem de dinheiro (sem dobrar), do repasse
"Prime Dreams", da leitura da caixa, de RBAC e da operação.
**Created**: 2026-10-22 · **Público**: autor e revisor, antes do `/speckit-tasks`
**Fontes**: `spec.md`, `research.md` (R-01–R-10), `data-model.md`, `contracts/api-318.md`, `plan.md`

## Regra de vínculo

- [x] CHK001 O critério de "liga sozinho" é inequívoco (uma candidata, valor ao centavo, nome **ou** já pagou,
  autenticado)? [Clarity, Spec §FR-004, research R-05]
- [x] CHK002 Os quatro "valores fortes" (saldo, sinal, parcela não coberta, total sem nada recebido) estão definidos com
  a mesma régua da cobrança (`sinal_pendente` ignora venda com data combinada/parcelas)? [Consistency, research R-05,
  plan "Universo"]
- [x] CHK003 "Nome bate" tem definição testável (normalização, stopwords, ≥ 2 tokens ou semelhança ≥ 0,85, contra quais
  nomes)? [Measurability, research R-05, Premissas]
- [x] CHK004 "Já pagou antes" está definido sem tabela nova e com escopo (mesmo grupo ou mesmo cliente)? [Clarity,
  research R-05, data-model]
- [x] CHK005 A ordem das sugestões (top 3) está definida? [Completeness, research R-05]
- [x] CHK006 O universo de candidatas é o mesmo da cobrança (corte, fora de cancelada/cortesia/ensaio/loja, saldo >
  folga) e está dito que a candidata é a venda (líder), não o dia? [Consistency, plan "Universo", Spec "Casos de borda"]
- [x] CHK007 O comportamento do PIX que chega antes de a venda existir está definido (7 dias) e verificável? [Edge Case,
  Spec §FR-006, cenário 27b]

## Dinheiro sem dobrar

- [x] CHK008 Está garantido que todo pagamento passa pelo núcleo de comprovante (trava do grupo, recálculo da 306)?
  [Consistency, research R-06, plan]
- [x] CHK009 As duas direções da duplicata (PIX depois do comprovante; comprovante depois do PIX) estão especificadas,
  com o contrato do 409 `possivel_duplicata`? [Completeness, Spec §FR-010/FR-011, contracts]
- [x] CHK010 "Desfazer" está definido para os três casos (sem arquivo, com arquivo, conciliado) e para o repasse de
  várias vendas? [Gap → corrigido (repasse multi-venda desfaz todos os pagamentos de `pagamentos_extra`), contracts]
- [x] CHK011 A concorrência "usuário confirma enquanto a rodada reavalia o mesmo PIX" está tratada? [Gap → corrigido
  (confirmar/descartar/desfazer e a reavaliação travam a linha do PIX com `with_for_update`, molde 298), plan]
- [x] CHK012 O valor gravado no repasse da InfinitePay (valor cobrado, taxa anotada) é inequívoco? [Clarity, Spec
  História 5, research R-07]
- [x] CHK013 Está dito que a soma do recebido não muda de fórmula (pagamento de PIX é `event_payments`)? [Consistency,
  data-model]

## Repasse "Prime Dreams"

- [x] CHK014 O critério de "repasse da Prime" (mesmo valor ou soma de 2–3 PIX da Prime em 3 dias) é testável e limitado?
  [Measurability, research R-07, cenário 19]
- [x] CHK015 Está claro que o repasse da InfinitePay nunca liga sozinho e só Financeiro/Superadmin veem? [Clarity, Spec
  §FR-012, contracts, cenários 20–21]
- [x] CHK016 O que acontece antes de a Prime ter número de conta cadastrado (PIX da Prime sem conta → repasse no MEI não
  acha par)? [Gap → corrigido: o par é procurado pelo `numero_conta_lido` da Prime **ou** pela saudação do aviso; até
  o cadastro, o repasse cai em "para conferir" de repasse, nunca liga — documentado no quickstart §4]

## Leitura e operação

- [x] CHK017 Está especificado que a leitura não altera a caixa (só leitura) e não guarda o corpo do e-mail? [Spec
  §FR-001/FR-003/FR-019]
- [x] CHK018 Os dois interruptores (env com default real; tela nascendo desligada) e o "só entra o que chegou depois de
  ligar" estão definidos? [Completeness, research R-04, Spec §FR-015]
- [x] CHK019 A saúde e o alerta (parada > 1 h, erro, não entendidos, conta não cadastrada) são verificáveis? [Spec
  §FR-016, contracts `/saude`, cenários 18/24]
- [x] CHK020 O ensaio tem critério objetivo para ligar (zero auto errado) e não imprime dado pessoal? [Spec SC-001,
  research R-10]
- [x] CHK021 A ordem de migrations com 310/315 (mesmo head) está prevista? [Dependency, plan "Ordem de merge"]

## RBAC

- [x] CHK022 Cada endpoint tem papéis declarados, inclusive o repasse e o desfazer, com cenário que deve falhar?
  [Spec RBAC, contracts, cenários 12/21/26]
- [x] CHK023 Está dito que a escrita usa o papel **real** (não o "Ver como")? [Gap → corrigido: gates de escrita usam
  `current_user.roles` reais; leitura do dashboard segue `_effective_has_role`, plan]
- [x] CHK024 O sino tem destinatários e resolução definidos (marcar lido ao decidir)? [Spec §FR-017, data-model]

## Notes

- Gaps corrigidos nesta passada foram escritos em `plan.md` / `contracts/api-318.md` / `quickstart.md`.

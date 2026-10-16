# Contratos — Feature 306

**Formato de erro**: o envelope de `json_error` (`app/api_utils.py:16-42`) é `{"error": {"message": str, "fields"?: {campo: msg}, …extras}}`. Os extras são `codigo`, `max_devolucao`, `dias`, `event_id`, `piso`, `teto`, `pago` e `devolvido`.

**Códigos de recusa** (P18): todo `codigo` desta feature é o valor de uma constante `CODIGO_*` de `app/constants.py`, da tabela única de nomes (`data-model.md` §6.2): `cancelado` é `CODIGO_EVENTO_CANCELADO`, `ja_cancelado` é `CODIGO_JA_CANCELADO`, `valor_mudou` é `CODIGO_VALOR_MUDOU`, e assim por diante. São 18 códigos, todos de 409. Nenhuma view escreve o texto do código à mão. A tela lê pela união:

```ts
// lib/eventOps.ts, ao lado de CodigoDevolverAoGoogle (:190-199); lib/gastos.ts e lib/financeiro.ts importam
export type CodigoRecusaCancelamento =
  | "cancelado" | "ja_cancelado" | "ensaio" | "grupo_mudou" | "sem_outro_dia_vivo" | "cache_pago"
  | "devolucao_pendente" | "max_devolucao_mudou" | "tente_de_novo" | "nao_cancelado" | "regime_sem_retido"
  | "abaixo_do_piso" | "acima_do_teto" | "pago_abaixo_do_devolvido" | "bv_nao_esta_a_pagar" | "valor_mudou"
  | "devolucao_travada" | "estado_mudou";
```

**Tudo o que é novo** é **opcional no TypeScript** e neutro quando falta: bundle e backend sobem separados.

**Sem sessão → 401** (`api_login_required`, `app/api_utils.py:45-57`), em todas as rotas.

**`docs/01` §4.3**: cada porta deste documento ganha linha, as 2 novas e todas as alteradas, com a regra de papel nova (o 409 `cancelado` para quem passa no gate de hoje). A linha de `_can_delete()` ganha o `PATCH …/devolucao`.

**Regra única do cancelado** (FR-047): `cancel_ops.pode_editar_venda_do_cancelado(user)` = papel **real** SUPERADMIN, a régua de `_can_delete()` (`agenda_write.py:111-115`) e `_is_superadmin()` (`:63-65`). Quem passa no gate de hoje e não passa nela recebe:

```json
409 { "error": { "message": "Este evento está cancelado: só o Superadmin corrige os dados de venda.",
                 "codigo": "cancelado" } }
```

**Trava**: as portas de comprovante (§9) travam o grupo (T1, `travar_grupo`) depois do 404 e do 403, **também no evento vivo**, e decidem pelo estado relido; reembolsos, parcelas e notas (§10, §11) travam só o próprio evento (`travar_evento`, como a 305) e releem `is_cancelled`. No vivo, depois da trava, as respostas e a ordem das recusas são as de hoje; só sob concorrência aparecem `tente_de_novo` e, no comprovante, `grupo_mudou` (Living Spec do checklist; cenário 16-vivo). A ordem das travas está no `data-model.md` §8.10. Deadlock (`40P01`) nos endpoints da 306 vira rollback e `409 {codigo: "tente_de_novo"}`, "Outra gravação estava em curso neste evento: tente de novo."

**Valores**:
- dinheiro no corpo é número (ou texto decimal com ponto), arredondado ao centavo HALF_UP;
- na resposta é `float`;
- data é `AAAA-MM-DD`;
- timestamp é ISO sem fuso (horário de São Paulo).

**Living Spec**: o que vem marcado "(Living Spec)" entra na spec antes do `/speckit-tasks`. A lista está na §23.

---

## 0. Tipo comum: o resumo do cancelado

`cancel_ops.serializar_resumo_cancelado(resumo, flags)`. Vai em `event.cancelamento` do detalhe, em `resumo` das respostas e em cada item de `/events/cancelamentos`.

```ts
// lib/agenda.ts
export type RegimeCancelamento = "venda" | "satelite" | "dia" | "virtual" | "legado";
export type ModoDevolucao = "tudo" | "parte" | "nada";
export type EstadoPagamento = "nao_pago" | "no_banco" | "pago";

export interface DevolucaoDoCancelado {
  id: number;                 // SpecialExpense.id
  valor: number;
  nome: string | null;
  pix?: string | null;        // só com show_financeiro
  estado: EstadoPagamento;
  data: string;               // expense_date
  evento_id: number;          // o dia a que está ligada (no grupo)
  observacao: string | null;
}

export interface ResumoCancelado {
  regime: RegimeCancelamento;
  modo: ModoDevolucao | null;          // escolhido no ato (refund_mode); null em satelite/virtual/legado
  modo_corrente: ModoDevolucao;        // de pago × devolvido
  venda: number | null;                // congelada (venda) | null
  pago: number;                        // grupo inteiro (ids por consulta), ao vivo
  devolvido: number;                   // grupo inteiro, aprovadas, ao vivo
  devolucoes: DevolucaoDoCancelado[];  // TODAS (FR-025); no dia, as do dia
  retido: number;                      // 0 em satelite/dia/virtual
  com_nota: boolean;
  cancelado_em: string;
  principal?: { id: number; titulo: string; data: string | null } | null;          // satelite/dia
  venda_passou_para?: { id: number; titulo: string; data: string | null } | null;  // antigo 1º dia (sale_handed_over)
  corte?: { venda_antes: number; venda_depois: number;
            cheio_antes: number | null; cheio_depois: number | null } | null;     // dia
  // ── só com show_financeiro ──
  imposto?: number | null;             // retained_tax (null = não se aplica)
  taxa?: number | null;                // commission_rate congelada
  comissao?: {
    cheia: number; retido: number;     // comissão cheia e do retido
    beneficiario: { id: number; nome: string } | null;
    liquidada: number;                 // pago + no banco
    linhas: { id: number; seller_id: number; seller_nome: string; valor: number;
              status: "a_pagar" | "no_banco" | "pago" | "cancelado";
              tipo: "comissao" | "ajuste" | "estorno"; ciclo: string /* AAAA-MM */;
              motivo: string | null }[];   // o link para Comissões sai daqui (ciclo + seller_id)
  } | null;
  bvs?: { acrescimo_id: number; recebedor: string | null; pix?: string | null;
          cheio: number; conta: number | null;   // bv_da_planilha (null = some da Planilha)
          estado: EstadoPagamento; pago_no_ato: boolean }[];
  // ── só com flags.can_edit_venda_cancelado ──
  limites_devolucao?: { piso: number; teto: number } | null;   // para o "Alterar devolução" (data-model §7.2)
  elenco?: { elenco_id: number; talent_id: number; artista: string; vaga: string;   // uma por escalação (vaga × dia)
             dia: { id: number; data: string | null }; cache_referencia: number | null;
             na_vaga: boolean; talent_pix_informado: boolean;
             multa: { gasto_id: number; valor: number } | null }[];
}
```

O PIX e o valor de comissão nunca saem sem `show_financeiro`. O Casting não recebe o bloco, porque `event.cancelamento` só sai com `show_comercial`.

---

## 1. `POST /api/events/<id>/cancelar` — alterado

- **RBAC**: `_can_delete()` (Superadmin real), depois do 404. Os demais recebem 403.
- **Jinja**: não há gêmeo.
- **Núcleo**: `cancel_ops.cancelar_evento`. Saem a recusa do marcado (`cancel_ops.py:282-283`), a do líder (`:289-292`) e o `except EventoMarcadoError` da view (`agenda_write.py:607-608`).

**Corpo**

```ts
// lib/eventOps.ts
export interface CancelarEventoInput {
  motivo: string;
  devolucao?: {                       // obrigatória em venda e dia; ignorada em virtual
    modo: ModoDevolucao;              // dia: só "parte" | "nada"
    valor?: number;                   // parte: o valor; tudo: o max_devolucao que a tela recebeu (só leitura)
    nome?: string; pix?: string;      // obrigatórios em tudo/parte
    observacao?: string;
  };
  imposto_retido?: number;            // obrigatório (≥ 0) com nota no venda; enviado sem nota ou no corte → 400
  bvs?: { acrescimo_id: number; recebedor: string; pix: string }[];  // completa BV a pagar sem recebedor/PIX
  multas?: { role_id: number; valor: number }[];  // uma por escalação (vaga × dia); vazio ou 0 = sem multa (ignorado)
  alcance?: "todos" | "so_este_dia";  // obrigatório no principal com outro dia vivo; ausente fora dele
  novo_principal_id?: number;         // com so_este_dia: o dia que o diálogo mostrou
  venda_nova?: number;                // obrigatório no corte (dia e so_este_dia): > 0 e ≤ venda atual
}
```

O que sai do corpo: `bv_negociado`. O corpo antigo `{motivo, devolucao:{valor,…}}`, sem `modo`, recebe 400 `devolucao_modo` sem ramo de compatibilidade. O bundle antigo mostra `e.message`.

**Ordem das recusas** (nada é gravado em nenhuma delas)

1. **401**, depois **404** (evento), depois **403**.
2. **T1–T6** (`data-model.md` §8.10). T1 trava o grupo inteiro pelos ids por consulta (`cancel_ops.ids_do_grupo`, `data-model.md` §6.4; avulso = uma linha), relendo todas as colunas e a composição.
3. **409 `ja_cancelado`**: "Este evento já está cancelado." A tela recarrega o evento. No HEAD, o já cancelado responde **400** `fields.motivo` (`agenda_write.py:609-610`); passa a 409.
4. **409 `ensaio`**: o evento é do tipo ENSAIO (FR-064).
5. **400 `fields.alcance`**, nos dois casos da FR-055.
6. **409 `sem_outro_dia_vivo`**: `so_este_dia` num principal sem outro dia vivo. A tela trata como `grupo_mudou`.
7. **409 `grupo_mudou`**, em dois casos:
   - `novo_principal_id` já não é o dia vivo mais cedo;
   - a composição do grupo relida em T1 difere da lida antes da trava.

   A tela refaz o impacto.
8. **409 `cache_pago`**, com o extra `dias: [{id, titulo, data}]` no grupo. Mensagem: "Este evento tem cachê pago ao elenco e não pode ser cancelado. Para devolver dinheiro à cliente, lance uma Devolução em Gastos Extras." Vale para qualquer dia alcançado.
9. **409 `devolucao_pendente`**: "Há uma devolução à cliente pendente ligada a este evento: aprove ou rejeite antes de cancelar." Num grupo, conta a pendente de **qualquer dia** do grupo (no "todos" e no corte, sob a T5), com o extra `dias` dizendo qual, como no `cache_pago`.
10. **400 com todos os `fields` de uma vez** ("Corrija os campos destacados."):
    - `motivo`, `devolucao_modo` (ausente; ou "tudo" no corte; ou diferente de "nada" com pago zero);
    - `devolucao_valor` (parte ≤ 0, acima do máximo, acima do teto no corte, **abaixo do mínimo do corte**; tudo sem `valor`). O mínimo do corte é (pago do grupo − já devolvido − venda nova) − máx(0, pago do grupo − já devolvido − venda atual), se positivo: "A cliente pagou R$ X: devolva pelo menos R$ Y ou aumente o novo valor da venda." No "nada" com mínimo > 0, o campo é `devolucao_modo`, com a mesma frase;
    - `devolucao_nome`, `devolucao_pix`;
    - `imposto_retido`: faltando com nota; negativo; **enviado sem nota** (é recusado, não ignorado); enviado no corte;
    - `venda_nova` (faltando no corte; ≤ 0; acima da venda atual; enviada fora do corte);
    - `bv_pix_<acrescimo_id>` ("Informe quem recebe e o PIX do BV — ele vai à Planilha de Pagamentos", pelos limites de `erros_do_bv`, `orcamento_evento_ops.py:406-417`);
    - `multa_<role_id>`: valor negativo ou inválido; vaga fora dos dias alcançados; vaga sem talento ou fora da lista do ato (recusou o convite, vaga de presença). Vazio e 0 não são erro: são "sem multa".
11. **409 `max_devolucao_mudou`**, com o extra `max_devolucao`: em "tudo", o `valor` difere do máximo recalculado sob a trava.
12. Grava, na ordem única do ato (`data-model.md` §7.1): `cancelled_at` → `ao_cancelar` → ensaios (banco), sinos e multas → `EventLog` → commit. Se o UNIQUE de `event_id` estourar (`IntegrityError`), vira rollback e **409 `ja_cancelado`**. Deadlock vira **409 `tente_de_novo`**.

**Resposta 200**

```ts
export interface CancelarEventoResult {
  ok: true;
  resumo?: ResumoCancelado;           // do evento da URL (no so_este_dia, do antigo 1º dia)
  aviso?: string | null;              // Google (falha ou trava de ambiente), sem o texto cru do erro — mantida
  google_removido?: boolean;          // mantida um ciclo
  gasto_id?: number | null;           // mantida um ciclo (a devolução, se nasceu)
  dias_cancelados?: number[];
  ensaios_cancelados?: { id: number; data: string | null; local: string | null }[];
  avisados?: { email: number; ensaio: number; casting: number };
  venda_passou_para?: { id: number; titulo: string; data: string | null } | null;
}
```

Depois do commit, usando os ids guardados antes dele:
- remove do Google o show e os ensaios, respeitando `CALENDAR_SUPPRESS_EVENT_WRITES` lido a cada chamada (chave ausente = travado) e pulando o marcado e o `virtual-local-…`;
- manda os e-mails ao elenco por `send_async`, um por talento.

O sino é emitido dentro da transação, com a chave do ato (`data-model.md` §6.3): `evento.cancelado:<id da URL>` e `evento.cancelado_escala:<id da URL>:<dia_id>`.

---

## 2. `GET /api/events/<id>/impacto-exclusao` — alterado

**RBAC**: `_can_delete()`. **Ordem**: 401 → 404 → 403 → (com prévia) 400 → 200. **Sem trava.**

**Chaves novas** (as de hoje ficam: `devolucao_sugerida` e `is_group_leader` por um ciclo; `acao` passa a `"cancelar"` em todo marcado):

```ts
export interface ImpactoExclusao {
  // … as de hoje (lib/eventOps.ts:102-115)
  regime?: "venda" | "satelite" | "dia" | "virtual";   // o que o ato daria (no principal: o do "todos"). Ausente = backend antigo → diálogo trava o envio
  sumiu_do_google?: boolean;
  ja_devolvido?: number;            // Σ devoluções aprovadas do grupo
  max_devolucao?: number;           // pago − já devolvido (no dia: o teto do corte)
  com_nota?: boolean;
  imposto_aliquota?: number;        // tax_rate de Configurações (_get_tax_rate, financeiro/routes.py:129-132), só referência
  bvs?: { acrescimo_id: number; recebedor: string | null; cheio: number; pago: boolean;
          falta_recebedor: boolean; falta_pix: boolean }[];
  comissao?: { beneficiario: { id: number; nome: string } | null; cheia: number;
               paga: number /* pago + no banco */; a_pagar: number };
  grupo?: { principal_id: number;
            dias: { id: number; data: string | null; titulo: string; cancelado: boolean;
                    cache_pago: boolean; faltam_dias: number | null }[];
            proximo_principal?: { id: number; data: string | null; titulo: string } | null } | null;
  ensaios?: { id: number; data: string | null; local: string | null; day_event_id: number }[];
  faltam_dias?: number | null;      // fuso de SP; negativo = "o evento foi há N dias"
  comprovantes_sem_valor?: number;
  cache_pago?: number;              // total; > 0 → o diálogo explica e não oferece cancelar
}
export interface ImpactoElenco {    // uma por escalação (vaga × dia); sem quem recusou o convite e sem a vaga de presença
  // … as de hoje
  role_id?: number; day_event_id?: number; talent_pix_informado?: boolean;
  talent_pix?: string | null;       // só com show_financeiro
}
```

**Prévia**: `GET …/impacto-exclusao?devolucao=<decimal com ponto>[&venda_nova=<decimal>]`.
- Usa a mesma conta da execução, com `simular=True`: sem `FOR UPDATE` e sem mutar o ORM. `primeiro_repasse_aberto(…, excluir_event_id=…)` deixa a prévia igual à execução apesar do autoflush.
- `venda_nova` presente indica corte (dia, ou principal com `so_este_dia`).
- Responde **só** `{efeito}`.

```ts
export interface EfeitoCancelamento {
  devolucao: number;
  retido: number | null;            // null no corte
  comissao_cheia: number;           // no corte: a cheia nova do principal vivo
  comissao_retido: number | null;   // null no corte
  bv_retido: number;                // soma; no corte: o BV a pagar do principal depois do acompanhamento
  bvs?: { acrescimo_id: number; bv_retido: number }[];   // por acréscimo (FR-011)
  ja_liquidada: number;             // pago + no banco do beneficiário nas linhas do evento
  ajuste: number | null;            // a linha (±) no primeiro repasse aberto; null = só a a_pagar muda
  ciclo: string | null;             // AAAA-MM
  repasse_em: string | null;        // AAAA-MM-05
  devolucao_minima?: number;        // só no corte: o mínimo da FR-056 para a venda nova enviada (0 quando não há excedente)
  imposto_referencia: number | null;// aliquota × retido ao centavo (ROUND_HALF_UP), só com nota; o rótulo da tela mostra imposto_aliquota, nunca o literal 16
}
```

Erros da prévia:
- **400** `fields.devolucao` para valor inválido, negativo ou acima do máximo;
- **400** `fields.venda_nova` para valor inválido, ≤ 0 ou acima da venda;
- evento já cancelado recebe **409 `ja_cancelado`**.

**Prova de que prévia = execução (FR-011; Living Spec).** O verify faz, numa variante do 2 e do 8, com `hoje` no dia 2 e no dia 10 do mês: GET `?devolucao=` antes e POST depois, e confere `retido`, `comissao_retido`, `ajuste`, `ciclo`, `repasse_em` e `bv_retido` contra o que ficou gravado, lido por conexão separada. A mutação "simular escreve" (o GET grava) tem de ser pega pela mesma conexão.

---

## 3. `PATCH /api/events/<id>/devolucao` — **novo**

- **RBAC**: `pode_editar_venda_do_cancelado` (= `_can_delete()`). Comentário `RBAC:` na view e linha nova em `docs/01` §4.3.
- **Núcleo**: `cancel_ops.alterar_devolucao`.

```ts
export interface AlterarDevolucaoInput {
  devolucao_total: number;          // venda: o NOVO TOTAL devolvido do grupo; dia: o total daquele dia
  nome?: string; pix?: string;      // obrigatórios se nascer complemento e não houver nome/PIX a herdar
  observacao?: string;
  imposto_retido?: number;          // só venda com nota
}
// 200 → { ok: true; resumo: ResumoCancelado }
```

**Ordem das recusas.** É a única ordem desta porta; a research (R12) segue esta. O regime só se lê depois de T1, então antes da trava só cabe a forma do corpo.

1. **401**, depois **404**, depois **403**.
2. **400 `fields.devolucao_total`** quando o campo falta ou não é número. É a única recusa antes da trava.
3. **Travas**, nesta ordem: T1 (grupo) → T2 → T4 (só no `venda`, e no `dia` cujo principal já foi cancelado em `venda`) → T5 (devoluções do grupo `FOR UPDATE populate_existing`, por id). É a ordem numerada do `data-model.md` §8.10: os beneficiários se conhecem depois de T2, então T4 vem antes de T5.
4. **409 `nao_cancelado`**: "Este evento não está cancelado."
5. **409 `regime_sem_retido`**: `satelite`, `virtual`.
6. **400 `fields`**, todos de uma vez:
   - `devolucao_total`: negativo; no `venda`/`legado`, acima do pago do grupo (aqui o teto é 400, como no RBAC da spec);
   - `devolucao_nome`, `devolucao_pix`: faltando quando nasce complemento sem nome/PIX a herdar, ou acima de 200/120 caracteres;
   - `imposto_retido`: no `dia`, no `legado`, sem nota (o `with_invoice` congelado) ou negativo.
7. **409 `abaixo_do_piso`**, com o extra `piso`: abaixo do piso do `data-model.md` §7.2 (no `venda`, as devoluções pagas ou no banco de todos os dias mais as aprovadas dos dias cortados, `dia`; no `dia`, as do dia pagas ou no banco). No `venda`, a aberta do principal absorve primeiro e depois as abertas dos dias `satelite`, por id.
8. **409 `acima_do_teto`**, com o extra `teto`: **só no `dia`**, quando passa do pago do grupo menos as devoluções aprovadas dos outros dias.
9. Grava (`data-model.md` §7.2), com `audit` por devolução, `EventLog` (UTC) e `updated_at/by`. Deadlock vira 409 `tente_de_novo`.
   - **`venda`**: regrava o imposto se vier; `reaplicar_cancelado` (comissão; BV ao vivo).
   - **`dia` com o principal vivo**: nada se refaz (clarify de 15/10 = A: "não mexe em comissão").
   - **`dia` cujo principal foi cancelado inteiro depois** (`venda`): a devolução do dia é devolvido daquela venda (FR-004), então a mesma gravação roda também `reaplicar_cancelado(principal)` e refaz o retido e a comissão do principal. Isso **deriva da D28** ("Acompanham"), não do clarify, que vale para o grupo vivo. É o 6º ponto da Living Spec, com variante no cenário 39.

Bundle novo × backend antigo: 404/405 → "O sistema está atualizando — tente em um minuto".

---

## 4. `POST /api/events/<id>/multas` — **novo**

- **RBAC**: `pode_editar_venda_do_cancelado`. Comentário `RBAC:` e linha em `docs/01` §4.3.
- **Núcleo**: `cancel_ops.lancar_multas_do_cancelado`, a mesma função das `multas` do cancelar, com a **mesma regra de valor** (FR-072): vazio e 0 são ignorados; por linha, 400 só para negativo ou inválido. A diferença é a lista: no cancelar, nenhuma multa é o normal; aqui, se nada sobrar com valor > 0, a resposta é 400 `fields.multas`, porque o endpoint existe para lançar.

```ts
export interface LancarMultasInput { multas: { elenco_id: number; valor: number }[] }  // elenco_id = uma escalação
// 200 → { ok: true; resumo: ResumoCancelado; gastos: number[] }
```

**Ordem das recusas**:
1. **401**, depois **404**, depois **403**.
2. T1, T2 (elenco).
3. **409 `nao_cancelado`**, em evento vivo.
4. **400**:
   - `fields.multas`: lista ausente ou malformada; ou sem nenhum valor > 0 depois de ignorar vazio e 0, com a mensagem "Informe a multa de ao menos um artista" (a spec, no RBAC do `POST …/multas`);
   - `fields.multa_<elenco_id>`: valor negativo ou inválido (não numérico); linha de outro evento ou fora da lista do ato; multa já lançada na linha ("Corrija em Gastos Extras").
5. Grava um gasto por linha com valor > 0 (`data-model.md` §7.5), com `expense_date` = hoje (data do lançamento, P-34). Commit.

A linha vale quando `elenco.cancellation.event_id == <id>`, ou quando `elenco.day_event_id == <id>` (satélite). Cada linha é uma escalação: o artista em 2 dias ou em 2 vagas tem 2 `elenco_id` (Living Spec).

Não há T3 nem T4: a multa não mexe em comissão nem em BV (Q10 = A).

---

## 5. `GET /api/events/<id>` — alterado (gate sem mudança)

`serialize_event_detail` (`agenda_read.py:711`):

```ts
// EventoDetalhe.event
cancelamento?: ResumoCancelado | null;   // só em evento cancelado e com show_comercial; legado → regime "legado"
// EventoDetalhe.flags (Record<string, boolean>; o tsc não acusa chave ausente)
//   can_edit_venda_cancelado — cancelado && is_superadmin (segue a impersonação, como can_group; o servidor confere o papel real)
//   can_edit_pagamentos     — vivo: can_edit_event; cancelado: can_edit_venda_cancelado
//                              a tela gata o que JÁ existe com `!== false` (janela de deploy), e o que é só do cancelado com truthy
```

Ficam fora de `_role_flags` (`agenda_read.py:155-204`): ele é reusado pela agenda, que não tem evento.

No cancelado:
- **`kpi` ausente** (`:1105-1110`): ele contaria a devolução como custo e o BV cheio. A aba Comercial abre por `data.venda`.
- **`venda.pode_mudar_taxa` e `venda.pode_trocar_vendedor`** (`:998-999`) passam a ser `… && can_edit_venda_cancelado`.
- **Item de `acrescimos`** (`:544-563`): `bv_pix = null` sem `can_edit_venda_cancelado`. O editor da 305 trata o PIX vazio como "mantém" (`comercial_ops.py:332-333`).

**`gastos`** (`_serialize_gastos`, `agenda_read.py:507`, chamado em `:1110` com os ids do grupo; só com `show_financeiro`):
- no principal **vivo**, só os dias vivos (`group_ops.dias_vivos`): a devolução e a multa de um dia cortado não entram;
- no **cancelado**, a lista traz o próprio dia;
- no regime `venda`, traz os dias do ato: o principal e os `satelite` que apontam para ele. É onde aparecem a devolução e as multas.

---

## 6. `PATCH /api/events/<id>/comercial` — alterado

**Ordem**
1. 401, depois 404.
2. **403** por `_can_create_event()`: o Financeiro e os outros papéis.
3. **409 satélite** (`agenda_write.py:1224-1229`, com `leader_id`). Pega também `satelite` e `dia`, que seguem no grupo.
4. **409 `cancelado`** para quem não é Superadmin real: é a Comercial.
5. 400 de data (`:1234-1251`).
6. **403 da 215b** (`:1256-1259`). Para o Superadmin, devolve `{}`.
7. 400 de valor (`erros_do_valor_na_aba_comercial`).
8. Grava.

**No cancelado (Superadmin)**:
- `update_event_comercial` (`event_ops.py:1169`) relê `cancelled_at` depois de `estado_da_venda` (`:1204`). Se o estado mudou entre a view e a trava, responde **409 `estado_mudou`** ("O evento mudou enquanto você editava: recarregue.").
- O gancho `sincronizar_comissao` vira um despachante: cancelado → `reaplicar_cancelado(event, motivo=…)`; vivo → `_sync_commission_payment`. É a mesma transação, porque o gancho roda antes do commit interno (`:1230-1231`, `:1240`).

O que recongela por campo (FR-049):

| Campo | Efeito |
|---|---|
| `sale_value` | Motivo "Cancelamento: correção da venda" |
| `commission_rate` | Taxa congelada = a nova. Motivo "Cancelamento: taxa corrigida", para mais e para menos |
| `is_cortesia_permuta` | Cheia 0 ou restaurada (por `_beneficiario_comissionado`) |
| `seller_id` | FR-051: o antigo com alvo 0, motivo "vendedor trocado — devolve o já recebido"; o novo com o alvo inteiro, "vendedor trocado — comissão do retido" |
| `sale_date` | Nada até a 1e |
| Demais da FR-048 (d) | Não mexem no congelado |

Venda abaixo do retido **não** é recusada. `acompanhar_bv_da_venda` já não roda em cancelado (`comercial_ops.py:531-532`).

**Resposta**: o detalhe, com `event.cancelamento` dentro (a tela grava o detalhe no cache) e `aviso_bv: null` no cancelado.

---

## 7. `PATCH /api/events/<id>` (edição completa) — alterado (Living Spec)

Ordem: 401 → 404 → 403 (`_can_create_event`) → 400 (`_validate_event_core`) → **409 `cancelado` para todos os papéis** → 215b → núcleo.

O 409 vale quando o evento está cancelado e chega `sale_value`, `sale_value_gross`, `commission_rate`, `seller_id`, `is_cortesia_permuta` ou `with_invoice` **diferente** do gravado, conferido por `_mesmo_valor` (`event_ops.py:740`), `_mesma_taxa` e `_mesmo_vendedor` (`:1105-1122`). A mensagem: "Evento cancelado: corrija os dados de venda pela aba Comercial."

`_gravar_venda_da_edicao` (`event_ops.py:846-879`) relê `is_cancelled` depois da trava, como cinto. A tela esconde "Editar tudo" no cancelado. A porta não está no RBAC da spec e entra pela Living Spec.

---

## 8. `PUT /api/events/<id>/acrescimos` — alterado

**Ordem**
1. 401, depois 404.
2. **403** por `_can_manage_sale()`: Casting e Figurino.
3. **409 satélite** (`agenda_write.py:1612-1617`, com `leader_id`).
4. **409 `cancelado`** para quem não é Superadmin real: Comercial e Financeiro.
5. 400 `items` (forma).
6. Ramo do cancelado (Superadmin), na ordem T1 → T2 → T3:
   - **400 `items`** no BV pago ou no banco ausente do corpo (leitura 6, `comercial_ops.py:283-294`);
   - **400 `items`** quando o evento tem acréscimos e nenhum item traz `id` (página anterior à 305): "Recarregue a página antes de salvar";
   - **400 `items.<i>.<campo>`** pela montagem da 305 extraída de `:216-404` (`_montar_acrescimos`, fatiada em cinco funções de ~30 linhas, a mesma lista do plan H4 e da R20): `id` repetido, valor, `valor_visto` contra o `amount_brl` cheio, `erros_do_bv`;
   - BV **novo** em % → **400** `items.<i>.value` "No evento cancelado, lance o BV em reais";
   - BV pago ou no banco com valor ou unidade diferente: **mantém o gravado**, como no vivo (`comercial_ops.py:337-338`), sem recusa;
   - **400** se o tipo do BV pago mudar, como na 305.
7. Grava no lugar pelo `id` (`alterar_acrescimos_do_cancelado`; `data-model.md` §7.4), sem o `delete`/`add` de `:407-413`. Depois `expire(event, ["acrescimos"])`, T4 e `reaplicar_cancelado(motivo="Cancelamento: correção da venda")`.

**O que fica livre e o que fica preso**
- Recebedor e PIX do BV pago trocam com rastro (`trocas` → `audit`, `agenda_write.py:1632-1636`), só no acréscimo.
- No BV não pago, regravam o acréscimo **e** a linha congelada.

**Fora do ramo**
- **Vivo**: inalterado e **sem T1**: a decisão vivo × cancelado lê o evento sem trava, e a 305 já trava o evento dentro de `substituir_acrescimos`. Só o ramo do cancelado toma T1 → T2 → T3. O `_sync_commission_payment` de `:1637` vira no-op no cancelado, pela guarda.
- **Corrida**: se `substituir_acrescimos` reler o evento já cancelado depois do `travar_evento` e devolver `[]`, a view faz rollback e responde **409 `estado_mudou`** ("O evento mudou enquanto você editava: recarregue."), nunca 200 sem ter gravado.
- `substituir_acrescimos` devolve `[]` sem gravar quando relê o evento cancelado depois de `travar_evento` (`comercial_ops.py:208`, `:218`). É cinto, porque a view já decidiu.

**Resposta**: o detalhe com `event.cancelamento`.

---

## 9. Comprovantes — alterados (decisão (c))

| Rota | Gate de hoje | No cancelado |
|---|---|---|
| `POST /api/events/<id>/payments` (`agenda_write.py:1747`) | `_can_edit_event()` | Quem não é Superadmin real → **409 `cancelado`**, **antes** de `_add_payment_record`, que salva o arquivo (`calendar/routes.py:1132-1155`) |
| `PATCH /api/payments/<id>` (`:1778`) | `_is_superadmin()` → 403 | Superadmin grava |
| `DELETE /api/payments/<id>` (`:1803`) | `_is_superadmin()` → 403 | Superadmin grava |

**Ordem**
1. 401, depois 404 (evento ou comprovante), depois 403.
2. **T1** `travar_grupo` do dia do comprovante, depois relê `is_cancelled`.
3. 409 `cancelado`, só no POST.
4. Grava e dá `flush`. O 400 de hoje vem aqui: no POST, de dentro de `_add_payment_record` (valor ou arquivo faltando); no PATCH, de `_edit_payment_amount` (`calendar/routes.py:1159-1164`).
5. `cancel_ops.reaplicar_por_dinheiro(event)`:
   - **409 `pago_abaixo_do_devolvido`** (extras `pago`, `devolvido`; rollback; só ao editar ou excluir): "O pago do grupo ficaria em R$ X, abaixo dos R$ Y já devolvidos." A guarda vale em todo cancelado e no grupo com algum dia cancelado; não vale no dia vivo (fora, `docs/05`);
   - principal cancelado em `venda` → `reaplicar_cancelado(principal, motivo="Cancelamento: comissão do retido")` (T2, T4) e `EventLog` (UTC) no dia e no principal.
6. Commit.

**Arquivo órfão (P16): a limpeza é do POST.** Se o POST levar 409 **depois** de `_add_payment_record` ter salvo o arquivo (`tente_de_novo` por deadlock em T4, ou `grupo_mudou`), a view faz rollback e remove do disco o arquivo novo. O PATCH só troca `amount` e o DELETE só apaga a linha (`_delete_payment_record`): nenhum dos dois recebe arquivo, então não há o que limpar.

A regra vale para comprovante em qualquer dia do grupo: o pago é do grupo (FR-004). Principal vivo (`dia`), `legado` e `virtual` → só a guarda.

**Resposta**: o detalhe do dia, com `event.cancelamento`; o POST responde 201. A tela invalida `["event"]` (o principal também mudou) e as chaves do financeiro (§22).

Erro na tela: `PagamentosPanel` e `PagamentoItem` passam a mostrar `error.message` (`FinanceiroSection.tsx:379-381`, `:158`, `:195`).

---

## 10. Reembolsos — alterados

| Rota | Gate de hoje | No cancelado |
|---|---|---|
| `POST /api/events/<id>/reimbursements` (`:1823`) | `_can_edit_event()` | Não Superadmin real → **409 `cancelado`** depois do 403 |
| `POST /api/reimbursements/<id>/collect` (`:1859`) | `_can_edit_event()` | Idem. O 409 vem antes do 400 "já cobrado" |
| `DELETE /api/reimbursements/<id>` (`:1899`) | `_is_superadmin()` | Sem mudança (os demais seguem com 403) |

Trava: `travar_evento` do próprio evento depois do 403, e então relê `is_cancelled` (no vivo, o caminho de hoje). Nada muda no congelado, e a resposta é a de hoje (o detalhe).

---

## 11. Parcelas e notas fiscais — alteradas

`PUT /api/events/<id>/parcelas` (`:1644`), `POST/PATCH/DELETE /api/events/<id>/invoices[/<id>]` (`:1489`, `:1524`, `:1562`).

Ordem: 401 → 404 → 403 (`_can_manage_sale`: Casting e Figurino) → 409 satélite (onde já existe) → `travar_evento` do próprio evento e releitura de `is_cancelled` → **409 `cancelado`** para quem não é Superadmin real → o de hoje. Sem mexer no congelado. No vivo, depois da trava, o caminho de hoje.

---

## 12. `PATCH /api/events/<id>/orcamento` — alterado

Gate de hoje: `_can_manage_sale()` (Comercial, Financeiro e Superadmin passam; Casting e Figurino → 403).

Ordem: 401 → 404 → 403 → 409 satélite → **409 `cancelado` para todos os papéis que passam no gate**, inclusive o Superadmin e o Financeiro: "O orçamento de um evento cancelado não se aplica nem se troca." Depois vêm a autoria da 301 e a B8.

Cinto: `set_event_orcamento` (`orcamento_evento_ops.py:935`) relê depois da trava e recusa antes de aplicar a venda, nos três verbos.

---

## 13. `DELETE /api/events/<id>` — alterado

Ordem: 401 → 404 → 403 → **409 `cancelado`** **antes** da condição de `:555`: "Evento cancelado não se exclui: o cancelamento não tem volta. Se foi por engano, recrie o evento." Depois, o de hoje: `sumiu_do_google`, "use o cancelamento", líder.

Núcleo: `_delete_event_flow` (`calendar/routes.py:4348`):
- trava o evento e relê;
- levanta `EventoCanceladoError` (irmã de `EventoMarcadoError`) antes da checagem do líder (`:4372`);
- `_apagar_vazio` do sync (`sumico_ops.py:341-356`) trava, relê `cancelled_at` e pula.

Estorno da exclusão (FR-036):
- comissão paga **ou no banco** → `event_id = NULL` e estorno órfão negativo no primeiro repasse aberto, com `original_id` e o motivo "Exclusão do evento";
- `a_pagar` → `cancelado`.

---

## 14. Grupo — alterado

| Rota | Mudança |
|---|---|
| `POST /api/events/<id>/grupo` (`:2365`) | `validar_agrupamento` (`group_ops.py:116-139`) recusa participante cancelado, principal ou satélite → **409 `cancelado`** com a frase do núcleo, depois de travar os participantes por id |
| `DELETE /api/events/<id>/grupo` (`:2431`) | `desagrupar` (`group_ops.py:204-231`) trava o satélite e o principal; dia cancelado → **409 `cancelado`** |
| `DELETE /api/events/<leader>/grupo/satelites/<sat>` (`:2455`) (Living Spec) | Mesma tradução (hoje viraria 500). A docstring de `:2456-2461` sai. A porta não está no RBAC da spec |
| `GET …/grupo/candidatos` | Sem mudança (`blocked_reason` é da 1c) |

---

## 15. `GET /api/events/cancelamentos` — alterado

Gate sem mudança: só Superadmin (leitura 1). Cada item de `cancelados[]` ganha `resumo?: ResumoCancelado`, montado em lote (`resumos_cancelados`), com `no_banco` e todas as devoluções; o PIX só com `show_financeiro`.

O campo `devolucao` fica por um ciclo, agora lido por `filtro_devolucao` (a primeira por id) em vez de `disbursement_type="cliente"` com `.first()` (`cancel_ops.py:361-372`).

```ts
export interface EventoCancelado { /* … */ resumo?: ResumoCancelado; }
```

---

## 16. Gastos Extras — alterados (FR-019, FR-020)

As seis portas mantêm o gate de hoje. A ordem **não** é a mesma nas seis; esta é a de cada uma no HEAD e onde a 306 entra (P19):

| Rota | Ordem no HEAD | Com a 306 |
|---|---|---|
| `POST /api/gastos` (`gastos_write.py:47`) | 401 → **sem gate de papel e sem 404**: o comprovante é salvo (`:53-57`), `event_id` inexistente vira `None` (`:72`) → 400 (`create_expense`) | 401 → 400 (validação; `disbursement_type: "cliente"` → `fields.disbursement_type`) → trava `travar_evento` quando a categoria normalizada é devolução e há evento → **409 `devolucao_travada`** (`fields.event_id`) se o evento está cancelado. O comprovante já salvo fica no disco, como no 400 de hoje |
| `POST …/aprovar` (`:80`) | 401 → 403 → 404 → 409 de estado ("já não está pendente") | 401 → 403 → 404 → trava → **409 `devolucao_travada`** (`fields.status`) → 409 de estado |
| `POST …/rejeitar` (`:97`) | 401 → 403 → 404 → 409 de estado | 401 → 403 → 404 → trava → **409 `devolucao_travada`** (`fields.status`) → 409 de estado |
| `PATCH /api/gastos/<id>` (`:115`) | 401 → 403 → 404 → 409 de estado (rejeitado sem `aprovar`, **antes** da validação, `gastos_ops.py:402-405`) → 400 (`:407`) | 401 → 403 → 404 → 409 de estado de hoje → 400 (validação; `cliente` só se já era) → trava (com `event_id` trocado, os dois eventos por id) → **409 `devolucao_travada`** (campo diferente do gravado; `aprovar: true` também; e o caminho inverso: o gasto que **passaria a ser** devolução de cancelado, pela categoria → `fields.category`, ou pelo `event_id` → `fields.event_id`) → grava. A trava vem antes das atribuições (`:420-428`) |
| `DELETE /api/gastos/<id>` (`:151`) | 401 → **404 (`:158-160`) antes do 403 (`:161-165`)** → 204, sem `try` | 401 → 404 → 403 → trava → **409 `devolucao_travada`** (`fields.id`) → 204 |
| `POST …/vincular-evento` (`:170`) | 401 → 403 → 404 → 400 (`event_id` inválido) | 401 → 403 → 404 → 400 → trava (os dois eventos, por id) → **409 `devolucao_travada`** (`fields.event_id`) |

**Trava**: `travar_evento` do evento da devolução (no vincular, os dois eventos em ordem de id), depois o gasto `with_for_update().populate_existing()`. Só então se decide.

```json
409 { "error": { "message": "Esta é a devolução de um evento cancelado: valor, data, categoria e vínculo só mudam pelo \"Alterar devolução\" na tela do evento.",
                 "fields": { "amount": "…" }, "event_id": 812, "codigo": "devolucao_travada" } }
```

O campo em `fields` é o que chegou **diferente** do gravado:
- `amount` (quantizado), `expense_date`, `category`, `event_id`;
- no excluir, `id`;
- no aprovar e no rejeitar, `status`.

Nome, PIX e descrição ficam livres.

**Regras do destinatário**
- Criar com `disbursement_type: "cliente"`, ou converter para ele, → **400** `fields.disbursement_type` "Devolução à cliente nasce pelo cancelamento do evento".
- Na devolução existente, o tipo `cliente` se mantém com corpo `""` ou `"fornecedor"` (bundle antigo).
- Nome e PIX só trocam com valor não vazio.
- `approved_with_edits` nunca acende.
- Criar uma devolução ligada a evento cancelado → 409 `devolucao_travada` (`fields.event_id`).
- A view faz `db.session.rollback()` explícito em todo 409, inclusive no DELETE, que ganha o `try`.

**Leitura**: `GET /api/gastos` (`_expense_dict`, `gastos_read.py:31-57`).

```ts
// lib/gastos.ts
export type DisbursementType = "reembolso" | "fornecedor" | "cliente" | null;
export interface GastoExtra { /* … */ locked?: boolean; event_cancelled?: boolean; }
// UpdateGastoInput.disbursement_type aceita "cliente"; CreateGastoInput nunca.
```

A lista de categorias (`gastos_read.py:72`) passa a trazer "Multa de cancelamento" (`SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`). Ela é aceita também na criação manual: é texto, sem trava, e só a multa do cancelamento marca a linha do elenco.

---

## 17. Planilha — `POST /api/financeiro/pagamentos/set-status` — alterado (Living Spec)

Gate sem mudança (`_require_financeiro`, `financeiro_write.py:48-51`). Ordem: 401 → 403 → 400 status → 400 "Item não encontrado". A porta não está no RBAC da spec; os 409 novos entram pela Living Spec.

**`item_type: "bv"`**: as duas portas chamam `cancel_ops.marcar_status_do_bv(acr_id, status, valor_esperado, actor_name)` (decisão (a)). As portas são a API (`:163-194`) e o Jinja (`financeiro/routes.py:1190-1197`, sem `valor_esperado`).

Passos:
0. `valor_esperado` presente e não numérico → **400** "Valor esperado inválido.", como hoje (`financeiro_write.py:170-175`), antes de travar.
1. Lê o acréscimo sem trava.
2. `travar_evento(acr.event)`.
3. Relê o acréscimo com `FOR UPDATE populate_existing`.
4. Relê o cancelamento e as linhas congeladas.
5. `atual = bv_da_planilha(acr)`.

Ao marcar `pago` ou `no_banco`:
- `atual is None` → **409 `bv_nao_esta_a_pagar`**: "Este BV não está a pagar: recarregue a Planilha."
- `valor_esperado` presente e ≠ `atual` → **409 `valor_mudou`**: "O BV mudou para R$ X desde que a Planilha abriu: recarregue e confira antes de marcar." (X = `atual`). É o 409 da 305 (`financeiro_write.py:170-183`), que ganha o `codigo` e passa a comparar com `atual`, não com `amount_brl`.

Depois grava `paid_amount` conforme o `data-model.md` §7.4 e o `audit` com o valor. A resposta continua `{status}`.

**`item_type: "expense"`**, para devolução de evento cancelado (`gastos_ops.devolucao_de_cancelado`). **Adotado** (P6), ponto firme da Living Spec:
- trava o evento (`travar_evento`) e relê o gasto com `FOR UPDATE populate_existing`;
- ao marcar `pago` ou `no_banco`, `valor_esperado` presente e ≠ `amount` → **409 `valor_mudou`**: "A devolução mudou para R$ X desde que a Planilha abriu: recarregue e confira antes de marcar.";
- **o bundle passa a mandar `valor_esperado: item.amount` para `bv` e para `expense`**. Hoje `PagamentoItemViews.tsx:112-116` só o manda quando `item.type === "bv"`;
- nos outros gastos, e sem o campo (bundle antigo), o comportamento é o de hoje (`:147-161`).

**`item_type: "commission"`**: o contrato não muda. Por dentro:
- `order_by(CommissionPayment.id)` em `liquidar_periodo` e `pay_seller_month`;
- o desfazer trava os eventos das linhas antes delas.

**Lote** (`POST …/bulk-action`, `:244`; Jinja `bulk_payment_action`, `financeiro/routes.py:1335`): sem conferência de valor. O "pago" em lote sobre uma devolução recém-alterada é resíduo aceito, registrado no `docs/05`.

**`GET /api/financeiro/pagamentos`**:
- o item `bv` sai com `amount = bv_da_planilha` e some quando é `None`;
- o item `commission` (aberto `S:AAAA-MM` e pago `S:AAAA-MM:pago`) ganha:

```ts
// lib/financeiro.ts — PagamentoItem
commission_lines?: { id: number; tipo: "comissao" | "ajuste" | "estorno"; event_id: number | null;
                     event_title: string; amount: number; ciclo: string; status: CommissionStatus }[];
```

O "soma zero com linha de valor não some" vale só no grupo aberto (`financeiro/routes.py:951-953`).

---

## 18. `GET /api/financeiro/comissoes` — alterado (gate sem mudança)

```ts
export type CommissionStatus = "a_pagar" | "no_banco" | "pago" | "cancelado";
export interface CommissionEntry { /* … */ tipo?: "comissao" | "ajuste" | "estorno"; original_id?: number | null;
                                   evento_cancelado?: boolean; ciclo?: string; motivo?: string | null; }
export interface CommissionKpis { /* … */ total_no_banco?: number; }   // total_month = pago + no banco + a pagar
```

- `status_label` ganha "No banco" (`STATUS_LABELS`, `comissoes_ops.py:31-35`).
- `evento_cancelado` sai por **uma** consulta em lote por mês.
- `motivo` é o código da 1e lido do prefixo da nota (`MOTIVOS_AJUSTE_COMISSAO`, `data-model.md` §6.1).
- `by_seller[]`:
  - `sale_count` conta só `original_id IS NULL`;
  - `month_status` = "pendente" se houver `a_pagar` com valor ≠ 0, órfão incluído;
  - quem só tem `no_banco` aparece.
- O resgate do mês corrente pega só o estorno **órfão**, por `filtro_estorno_orfao()`.
- `POST /api/financeiro/comissoes/pagar-mes`: contrato igual, filtro novo e trava ordenada.

---

## 19. Relatórios — alterados (gates sem mudança)

| Rota | Chaves novas (todas opcionais no TS) |
|---|---|
| `GET /api/financeiro/dashboard` | `dre.{realizado,projetado,total}.retido_cancelamentos` e `.n_cancelados`, sempre enviados. `paineis.cancelamentos?` sempre: `{quantidade, pago, devolvido, devolucao_a_pagar, retido, comissao_retido, bv_retido, imposto, efeito_resultado, itens: [{event_id, titulo, cancelado_em, retido}]}`. `receita_por_tipo["Retido de cancelamentos"]` (`dre_ops.ROTULO_RETIDO`). `monthly_trend[].retido?`. `top_sellers[].retido?`. `notas_fiscais[].cancelado?` e `retido?` |
| `GET /api/vendas/pipeline` | `kpis.retido_cancelamentos?`, `kpis.n_cancelados?`, `kpis.comissao_retido?` (as duas últimas fecham a sublinha "de N cancelamento(s)" e a da comissão prevista; `n_cancelados` é o nome da DRE). O retido entra em `total_vendido` do vendedor congelado e a comissão do retido em `comissao_prevista` do beneficiário congelado |
| `GET /api/admin/desempenho` | Filtra o cancelado do mês do evento. `vendas[].retido?`, `vendas[].cancelados?`, `totals.retido?` (por **nome**, mapeado do vendedor congelado) |
| `GET /api/clientes/<id>`, `/api/clientes/`, `/api/clientes/metricas` | Sem chave nova: `total_sales` inclui o retido; contagens e "Com evento"/"Recorrentes" sem cancelado |
| `GET /api/dashboard` | Performance ignora o cancelado. A cobrança da Home desconta as devoluções dos dias do recebido (FR-061) |

```ts
// lib/financeiro.ts
DreView += retido_cancelamentos?: number; n_cancelados?: number;
TopSeller += retido?: number;   MonthlyTrendItem += retido?: number;
NotaFiscalPendente += cancelado?: boolean; retido?: number;
FinanceiroPaineis += cancelamentos?: { quantidade: number; pago: number; devolvido: number; devolucao_a_pagar: number;
  retido: number; comissao_retido: number; bv_retido: number; imposto: number; efeito_resultado: number;
  itens: { event_id: number; titulo: string; cancelado_em: string; retido: number }[] };
// lib/vendas.ts   VendasKpis += retido_cancelamentos?: number; n_cancelados?: number; comissao_retido?: number;
// lib/adminConfig.ts DesempenhoItem += retido?: number; cancelados?: number; AdminDesempenho.totals += retido?: number;
```

A tela mostra a linha do retido por `n_cancelados > 0`, nunca pelo valor. Com chave ausente, `?? 0`.

---

## 20. Outras rotas

| Rota | Mudança |
|---|---|
| `POST /api/roles/<id>/assign` (`agenda_write.py:159`) e a escala Jinja | Contrato igual. Em evento cancelado, `assign_role` não manda o e-mail de remoção (`casting_ops.py:153-161` + `and not event.is_cancelled`) |
| `GET /api/notificacoes` | Kinds `evento.cancelado` (Ensaio; um por pessoa **por ato**; link para o evento; `dedupe_key evento.cancelado:<id da URL>`) e `evento.cancelado_escala` (Casting; um por dia com escalados; `urgent` a ≤ 7 dias; link para a aba de produção; `dedupe_key evento.cancelado_escala:<id da URL>:<dia_id>`). Ícones em `NotificacaoItem.tsx:7-13`; sem eles, cai no `Bell` |
| `DELETE /api/admin/users/<id>` | Bloqueio novo "cancelamentos" (vendedor ou beneficiário congelado) em `UserDeletionBlockedError` (`user_ops.py:422-432`). Mesmo status e formato: `400 {error:{message, blockers}}` (`admin_users_write.py:269-270`) |
| `POST /api/events/<id>/devolver-ao-google` | Sem mudança (já recusa cancelado, `codigo: "cancelado"` de `sumico_ops.CODIGO_CANCELADO`, outro fluxo) |
| `POST /api/events/<id>/sync`, `PUT …/clients`, `PATCH …/basico` | Sem mudança (trava geral da 1c) |

---

## 21. Jinja gêmeo

| Porta Jinja | Mudança |
|---|---|
| `event_detail` POST (`calendar/routes.py:1636-1671`; tabela `_EVENT_ACTIONS` `:1608-1633`) | Para `update_comercial`, `update_sale`, `add_payment`, `edit_payment`, `delete_payment`, `add_reembolso`, `collect_reembolso` e `delete_reembolso`: depois de `travar_evento(event)` e de reler, se o evento está cancelado → `flash` "Evento cancelado: os dados de venda se corrigem pela tela nova, só pelo Superadmin." e redirect, **para todo papel, inclusive o Superadmin**, antes de qualquer handler. O Jinja não tem `reaplicar_cancelado`. Confirma a P-27, e a recusa vem antes de `estado_da_venda` (`:837`). **Living Spec**: a recusa de `update_sale` e dos três de reembolso para todos vai além da FR-047 |
| `group_events` / `ungroup_event` (`_handle_group_events` `:1536`, `_handle_ungroup_event` `:1580`) | A recusa vem do núcleo (`validar_agrupamento`, `desagrupar`) → `flash` |
| `delete_calendar_event` (`:4450-4479`) | Captura `EventoCanceladoError` de `_delete_event_flow` → `flash` |
| Financeiro `set_payment_status` (`financeiro/routes.py:1109`) | **BV** (`:1190-1197`) → `marcar_status_do_bv(valor_esperado=None)`, com `flash` em `bv_nao_esta_a_pagar`. **Gasto** (`:1182-1189`) → quando é devolução de cancelado, `travar_evento` do evento antes de mudar o estado (o formulário Jinja não manda `valor_esperado`). **Comissão** (`:1139-1146`) → `liquidar_item_de_comissao`, com trava ordenada |
| `set_commission_status` (`financeiro/routes.py:1561-1582`) | **Guarda de uma linha** (P12): `cp.event` cancelado → `flash` "Comissão de evento cancelado: o valor se acerta pelo cancelamento e o pagamento pela Planilha de Pagamentos." e redirect, sem mudar nada. Vem depois da recusa da 267c (linha paga) e vale para qualquer status pedido. Não vai ao `docs/05` |
| `pagamentos()` (`:1020-1103`) | Herda `_build_bv_items` (BV por `bv_da_planilha`) e `_build_commission_items` (linhas por item), que são compartilhados |
| `dashboard()` + `dashboard.html` (`:263-575`; linha nova depois de `:123`) | Mesma DRE da API, ao centavo (FR-041 a FR-043), com `dre_ops` compartilhado |
| `/vendas/` (`:1447-1475`) | `cancelled_at IS NULL` em `events_q` (`:1454`) |
| `comissoes()` (`:1487-1541`) | Fora (dívida no `docs/05`). `comissao_exibida_do_evento` fica 0 na tela Jinja do evento (P-28, `docs/05`) |

---

## 22. Bundle × backend e cache

**Bundle novo × backend antigo**
- `regime` ausente no impacto → envio travado com "O sistema está atualizando — tente em um minuto".
- `cancelamento` ausente → `KpiGrid` antigo.
- 404/405 nos dois endpoints novos → mesma frase.
- Gate de coisa que já existe (Adicionar pagamento) usa `flags.can_edit_pagamentos !== false`.
- `valor_esperado` em `expense` com backend antigo: ignorado (o ramo de hoje não lê o campo).

**Bundle antigo × backend novo**
- Cancelar sem `modo` → 400 legível.
- `kpi` ausente → `null` no `KpiGrid`.
- `is_group_leader` e `devolucao_sugerida` mantidas por um ciclo.
- A Planilha aberta antes manda o BV cheio e recebe o 409 `valor_mudou` "O BV mudou para R$ X", que é a mensagem certa.
- A Planilha antiga não manda `valor_esperado` em `expense`: comportamento de hoje, sem conferência.

**Formato das respostas.** `PUT …/acrescimos`, `PATCH …/comercial` e os comprovantes continuam devolvendo o **detalhe**, porque a tela o grava no cache: o resumo vai em `event.cancelamento`. `PATCH …/devolucao` e `POST …/multas` devolvem `{ok, resumo}`.

**Invalidação** (`invalidarFinanceiro` passa a ser exportada de `lib/financeiro.ts:300`):

| Mutação | Chaves invalidadas |
|---|---|
| `useCancelarEvento` | `["event"]` (todos os dias e o novo principal), `["evento-impacto-exclusao", id]`, `agenda`, `agenda-dia`, `cancelamentos`, `dashboard`, `financeiro-*`, `vendas-dashboard`, `admin-desempenho`, `gastos-extras`, `invalidarSumidosGoogle()`, `invalidarNotificacoes()` |
| `useAlterarDevolucao` | `["event"]` (dia e principal), `dashboard`, `gastos-extras`, `financeiro-*`, `cancelamentos` |
| `useLancarMultas` | `["event", id]`, `gastos-extras`, `financeiro-pagamentos`, `financeiro-dashboard` |
| Comprovante no cancelado (`useEventMutation`, `lib/eventAttachments.ts:47-61`) | Além de `dashboard`: `["event"]`, `financeiro-*`, `vendas-dashboard`, `cancelamentos` |
| `useUpdateEventComercial`, `useSetAcrescimos`, parcelas e notas, reembolso no cancelado | Mais `financeiro-dashboard`, `vendas-dashboard`, `cancelamentos` |
| `useDeleteEvent` | Mais `invalidarSumidosGoogle()` |
| set-status da Planilha (`PagamentoItemViews`) com 409 `valor_mudou` ou `bv_nao_esta_a_pagar` | `financeiro-pagamentos` (recarrega a Planilha) |

---

## 23. O que estes contratos levam à spec (Living Spec)

Entram na spec antes do `/speckit-tasks`, junto com os pontos de modelo (`data-model.md` §11):

1. **RBAC da spec ganha três portas**: `PATCH /api/events/<id>` (§7, 409 `cancelado` para todos), `DELETE /api/events/<leader>/grupo/satelites/<sat>` (§14) e `POST /api/financeiro/pagamentos/set-status` (§17, 409 `bv_nao_esta_a_pagar` e `valor_mudou`).
2. **O Jinja recusa também `update_sale` e os três de reembolso** no cancelado, para todos os papéis, inclusive o Superadmin (§21). Vai além da FR-047.
3. **Os 18 códigos de recusa** (todos 409, com `valor_mudou`) da tabela do `data-model.md` §6.2, com a união TS.
4. **`valor_esperado` no item `expense`** da devolução de cancelado (§17): a tela manda, o servidor confere. Ponto firme, não recomendação.
5. **Multa por escalação** (§1, §4): um campo e um gasto por vaga × dia; vazio e 0 ignorados nos dois caminhos; por linha, 400 só para negativo ou inválido; no `POST …/multas`, 400 `fields.multas` "Informe a multa de ao menos um artista" quando nada sobra com valor > 0.
6. **"Alterar devolução" do dia cortado com o principal cancelado depois** (§3): refaz retido e comissão do principal (D28), com variante no 39.
7. **Prévia = execução provada** (§2, FR-011): variante do 2 e do 8 com `hoje` no dia 2 e no dia 10.

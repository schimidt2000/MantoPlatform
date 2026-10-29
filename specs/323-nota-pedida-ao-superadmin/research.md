# Pesquisa — 323

## R1. Onde a nota "a emitir" nasce hoje

- **Criação** (`_create_event_row`, `app/calendar/routes.py`): com `with_invoice`, cria uma
  `EventInvoice` com `amount = sale_value`, `status = a_emitir` (ou `emitida` se o Jinja mandou
  arquivo). Vale para a API e para o Jinja (`_create_event_core` é o mesmo).
- **"Editar tudo"** (`event_ops._gravar_venda_da_edicao`) e **card Comercial**
  (`event_ops.update_event_comercial`): só gravam `event.with_invoice`. **Nenhuma nota nasce** — é o
  furo. Desligar o chip também não mexe nas notas.
- **Jinja** (`_handle_update_comercial`, `routes.py`): `comercial_ops.sincronizar_notas` com a lista
  do formulário antigo; desligar apaga todas. Inalcançável em produção (fora de `BACKEND_PREFIXES`)
  e com a remoção pausada — **não se toca**.

**Decisão**: uma função de núcleo, `pedido_de_nota_ops.acompanhar_pedido(event, pedida_por_id)`,
chamada nas duas portas de edição logo depois de gravar `with_invoice`, e um carimbo do pedido na
criação (`carimbar_pedido_da_criacao`). As duas portas de edição já travam o evento antes de
escrever (`comercial_ops.estado_da_venda` → `travar_evento`), então "não tem nota → cria" roda com a
linha do evento travada: o clique duplo espera e encontra a nota do primeiro.

**Alternativas**: `UNIQUE(event_id)` em `event_invoices` — impossível, a 069 permite várias notas;
reaproveitar `sincronizar_notas` — exige a lista inteira de notas no corpo, que as telas novas não
mandam, e apaga a emitida ao desligar.

## R2. Desligar o chip

Hoje (portas novas) nada acontece: nota a emitir de venda "sem nota" ficaria como tarefa para
sempre. **Decisão**: desligar exclui só as notas `a_emitir`; `emitida` é documento contábil e fica
(o Jinja apagava tudo — divergência registrada, o Jinja não muda). Cancelado e satélite: nenhuma
mudança nas notas (o cancelado tem regra própria da 306; o satélite não tem venda).

## R3. Onde guardar os dados da nota

Os dados (CNPJ/CPF do tomador, ISS retido, município, referência, observações) são da **venda**: o
cliente pede uma vez, e a 069 já divide a venda em várias notas com valor e data próprios.
**Decisão**: cinco colunas em `calendar_events` (prefixo `nota_`). Em `event_invoices`, só o que é
do pedido de cada nota: `pedida_por_id`, `pedida_em`, `aviso_enviado_em`.

**Alternativa rejeitada**: colunas em `event_invoices` — a vendedora teria de repetir os dados em
cada nota, e o chip (que é da venda) não tem uma nota para editar quando ainda não existe nenhuma.

## R4. CNPJ "vem do cliente"

O formulário de criação escolhe o cliente na mesma tela; preencher o campo a partir do cliente
escolhido exigiria buscar o cadastro no meio do formulário. **Decisão**: o campo é "CNPJ ou CPF do
tomador", com a ajuda "Em branco, vale o do cadastro do cliente."; o painel, o e-mail e a
discriminação usam `nota_tomador_doc` **ou**, vazio, o CNPJ (senão o CPF) do cliente contratante.
O detalhe do evento manda o documento do cadastro para a tela mostrar como sugestão. Documento
digitado completa o cadastro do cliente se o campo correspondente estiver vazio (regra 119).

## R5. O aviso por e-mail

- Modelo: `send_new_expense_alert_email` (319) — assunto com o que importa, prévia com o resto,
  enchimento invisível, caixa de dados e botão.
- Destinatários: usuários ativos com papel SUPERADMIN (como `_financeiro_and_superadmin_users`, só o
  Superadmin).
- **Uma vez por nota**: `UPDATE event_invoices SET aviso_enviado_em = :agora WHERE event_id = :id
  AND status = 'a_emitir' AND pedida_por_id IS NOT NULL AND aviso_enviado_em IS NULL RETURNING id`,
  commitado, e só então `send_async`. A reivindicação atômica é a barreira (constituição: idempotência
  por banco); nota do legado (sem `pedida_por_id`) nunca dispara.
- Depois do commit da venda, dentro dos três núcleos (`_create_event_core`, `update_event_core`,
  `update_event_comercial`), como `gastos_ops.create_expense` já faz. Falha no envio só loga.
- Trava local: `_send` já respeita `_emails_enabled()` e `_bloqueia_link_local` (hotfix 269b) — o
  `manto_local` não manda e-mail a ninguém. O verify troca `_send` por coletor.

## R6. A discriminação

Das cinco notas do dono:

```
AF 618/2026                                  ← referência (se houver)
Personagens para evento 17/10                ← o que é + data (EDU: "Apresentações Educamanto — 17/10")
Vencimento: 16/10                            ← se a venda tiver data de recebimento
Esses são os dados da minha conta no Inter:  ← bloco fixo (config)
INTER - 077
PRIME DREAMS EVENTOS LTDA
CNPJ: 60.708.296/0001-21 (PIX)
Agência: 0001
Conta: 44689668-3
<observações>                                ← se houver
```

- "O que é": o título do Google traz "(TIPO)" e os personagens separados por "+", que o dono não
  põe na nota. **Decisão**: texto fixo por tipo — evento EducaManto (`EDUCAMANTO_TITLE_PREFIX`) →
  "Apresentações Educamanto — dd/mm"; os demais → "Personagens para evento dd/mm". O Superadmin
  ajusta no site da prefeitura quando quiser.
- Vencimento: `payment_due_date` (faturado); senão a primeira `EventInstallment.due_date` a partir
  de hoje; senão nada.
- Bloco bancário: `NOTA_DADOS_BANCARIOS` em `app/config.py` com o texto acima como default real;
  env `NOTA_DADOS_BANCARIOS` só sobrepõe (Princípio XIV).

## R7. A tarefa na tela inicial

`build_dashboard_summary` (`app/api/dashboard_service.py`) já monta um bloco por painel, cada um
protegido por `_bloco` (falha vira `null`, a Home não cai). **Decisão**: bloco `notas_a_emitir`
só com `is_superadmin` (real e sem "Ver como"), lista de `pedido_de_nota_ops.painel()`. No React,
cartão no resumo do topo (`stats`, com `urgent = total`) e um `SectorPanel` com as linhas.

"Inserir nota" reusa `PATCH /api/events/<id>/invoices/<id>` (gate `_can_manage_sale`). Esse PATCH
grava `amount` e `issue_date` do corpo — **mandar sem eles apagaria o valor**. A tela manda o valor
atual e a data de emissão (a da nota ou hoje, horário de SP), como o editor da aba Financeiro.

## R8. Relógio

`pedida_em` e `aviso_enviado_em` em `now_sp()` (o "agora" do negócio, naive SP), como
`notifications` (272). Nunca comparar com `event_invoices.created_at` (UTC).

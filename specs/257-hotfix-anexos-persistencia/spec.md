# Hotfix 257 — anexos do evento não persistiam (comprovante sumia no refresh)

**Branch**: `257-hotfix-anexos-persistencia` · **Created**: 2026-08-21 · **Status**: corrigido
**Migration**: nenhuma

> Hotfix de produção registrado fora da esteira SDD completa (mesmo padrão dos hotfixes
> "vincular-na-criacao" e "cadastro-raiz"): defeito relatado pelo dono, reproduzido, corrigido e
> travado por verificação no mesmo dia.

## Problema (relatado em 21/08/2026)

"Ao anexar comprovantes na página do evento, na parte comercial, quando dá refresh o comprovante
some."

## Diagnóstico

Reproduzido contra o `manto_local` por HTTP real:

```
POST /api/events/<id>/payments   → 201; resposta traz pagamentos.items = 1 (a tela desenha)
banco (conexão separada)         → 0 registros
GET  /api/events/<id> (refresh)  → pagamentos.items = 0  → some
```

**Causa raiz**: `api_add_payment` (e mais quatro endpoints da mesma família, feature 153) chamava
o helper `_add_payment_record`, que só faz `db.session.add(...)`, e **não chamava
`db.session.commit()`**. Quem commitava era o dispatcher do Jinja (`_handle_add_payment`); ao
extrair a lógica para a API, o commit ficou para trás. O `PATCH`/`DELETE` dos mesmos recursos
sempre commitaram — por isso editar e excluir funcionavam.

A resposta parecia correta porque o serializador consulta `EventPayment` na **mesma sessão**: o
autoflush do SQLAlchemy grava o INSERT pendente antes da consulta, então o comprovante aparece
no JSON. No fim do request a sessão é descartada e o INSERT é desfeito — daí "aparece e some".

**Escopo confirmado** (todos respondiam 2xx e não gravavam nada):

| Endpoint | Ação na tela |
|---|---|
| `POST /api/events/<id>/payments` | comprovante de pagamento |
| `POST /api/events/<id>/contracts` | contrato |
| `POST /api/events/<id>/reimbursements` | reembolso a cobrar |
| `POST /api/events/<id>/invoices` | nota fiscal |
| `POST /api/reimbursements/<id>/collect` | marcar reembolso como cobrado |

Não afetados (têm commit próprio): editar valor e excluir comprovante, marcar cachê como pago,
e todo o resto do detalhe do evento.

**Desde quando**: o endpoint nasceu assim na feature 153 (21/07/2026). Enquanto a tela Jinja era
usada, o caminho que commitava mascarava o defeito. Nenhum commit posterior tocou o arquivo até
este hotfix.

**Dano colateral**: o arquivo físico é salvo **antes** do INSERT, então os anexos enviados no
período ficaram órfãos no volume (`instance/uploads/{payments,contracts,invoices}`) — sem linha
no banco, mas com os bytes intactos e o carimbo de data/hora no nome. Ver
`specs/257-hotfix-anexos-persistencia/recuperar_anexos_orfaos.py` e o endpoint de listagem abaixo.

## Correção

`db.session.commit()` nos cinco endpoints (`app/api/agenda_write.py`), no mesmo padrão que o
`PATCH`/`DELETE` já usavam.

## Recuperação dos órfãos

`GET /api/audit-agent/<token>/orphan-attachments` (novo, somente leitura, mesmo token do auditor
financeiro): lista os arquivos das pastas de anexo que **não** têm linha correspondente no banco,
com tamanho, data de envio (do nome do arquivo) e eventos candidatos por proximidade de data. O
script `specs/257-hotfix-anexos-persistencia/recuperar_anexos_orfaos.py` consome esse endpoint e gera o relatório para
conferência humana — **não escreve nada**.

## Resultado da recuperação (produção, 21/08/2026)

23 arquivos sem linha no banco, dos quais **4 têm o carimbo do fluxo novo** (`YYYYMMDDHHMMSS_hex_`)
e são as vítimas confirmadas do bug: 10/08 12:43, 20/08 e duas tentativas em 21/08 12:31 e 12:32
(a mesma pessoa tentando de novo — foi o relato que abriu este hotfix). Os outros 19 não têm
carimbo: são anteriores ao prefixo único, incluindo 4 `adv_*` de adiantamentos cujo registro foi
apagado. Todos os 4 confirmados têm evento candidato sugerido no relatório.

Rodar de novo: `python specs/257-hotfix-anexos-persistencia/recuperar_anexos_orfaos.py`
(o `.md` gerado fica fora do git — tem nome de cliente).

## Verificação

`specs/257-hotfix-anexos-persistencia/verify_257.py` contra o `manto_local`: cada upload é feito
pela API e conferido por **conexão psycopg independente** (uma checagem feita na mesma sessão do
Flask passaria mesmo com o bug, por causa do autoflush — foi o que quase escondeu o defeito no
diagnóstico).

## Pendência conhecida (não incluída neste hotfix)

O handler Jinja gravava um `EventLog` a cada anexo ("Adicionou pagamento recebido de R$ X"); a
API não grava. O histórico do evento perde esse rastro. Corrigir junto exigiria decidir o texto
de cada log — fica como item separado.

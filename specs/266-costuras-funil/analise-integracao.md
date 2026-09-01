# Análise de integração do funil — 31/08/2026

> Levantamento que originou as features **266** (costuras) e **267** (integridade), e o plano de
> ondas que vem depois delas. Feito por 9 agentes de leitura sobre 6 domínios
> (formulários, orçamento, eventos, clientes, financeiro, feedback/automações), com cada achado
> ancorado em arquivo:linha sobre a branch `265-nfc-revisao-videos`.
>
> **Este documento é evidência, não plano.** O que vira código está em `spec.md` (266) e na spec da
> 267. O que ainda não virou feature está na seção "Ondas seguintes", para não se perder.

---

## 1. O diagnóstico

O sistema tem todos os órgãos e faltam os nervos: cada módulo funciona bem por dentro e conversa mal
com o vizinho, então a continuidade do funil vive na memória de quem opera.

O achado que muda o custo de tudo: **a maior parte dos alicerces da integração já existe** — no
banco, na API, ou como padrão pronto em outro módulo. Quatro provas:

| Peça | Estado |
|---|---|
| `EventInstallment.received` (baixa de parcela) | coluna existe, lida em 5 lugares, **escrita em nenhum** |
| `GET /api/clientes/avaliacoes?client_id=` | filtro existe e é parseado, **nenhuma tela envia** |
| "Criar evento com os dados desta resposta" | botão **existe**, mas o prefill carrega só data e cliente |
| Lembrete por data com anti-spam e janela de horário | **roda em produção** no lembrete de convites |

## 2. O funil, transição por transição

O meio é sólido; as duas pontas sangram.

| Transição | Estado | O que acontece hoje |
|---|---|---|
| Formulário → equipe | **quebrada** | ninguém é avisado; o único aviso é o WhatsApp que a cliente dispara |
| Resposta → cliente | **quebrada** | `client_id` nasce NULL mesmo com telefone batendo em 1 ficha |
| Resposta → orçamento | **quebrada** | não existe; redigitação total na calculadora |
| Orçamento → evento | atrito | herda valor/cachê/transporte, mas perde fim, pagamento e vendedor; sem selo de convertido |
| Evento → execução | **fluida** | sync 600s, convite automático, lembrete de confirmação, teto de cachê |
| Evento → recebimento | **quebrada** | `received` não é escrito; nenhuma rotina cobra vencimento |
| Evento → comissão | atrito | automática no caminho certo; 3 defeitos nos caminhos vizinhos |
| Pós-evento → avaliação | **quebrada** | 100% manual e sem rastro de envio |
| Histórico → recompra | **quebrada** | aniversário da criança não gera nada |

## 3. As cinco quebras

### 3.1 O funil não flui para frente
Resposta nova invisível · resposta não vira orçamento · prefill resposta→evento raso (só data e
cliente, `EventCreatePage.tsx:129-151`) · orçamento sem FK de cliente (`OrcamentoHistory.client_name`
é texto livre, `models.py:1431-1447`) · orçamento sem status ganho/perdido · evento importado do
Google entra mudo e não aceita vincular orçamento depois.

### 3.2 O rastro para trás não existe
Do `EventDetail` não se navega para cliente (`ComercialSection.tsx:408-416`), talento
(`CastingSection.tsx:387`), conteúdo do pré-contrato (`agenda_read.py:924-926` traz só id/nome/tipo)
nem financeiro. `/formularios` não aceita deep-link. A ficha da cliente esconde avaliações,
orçamentos, tags NFC, metadados de campanha e `notes`. Nome e telefone da cliente não são editáveis
(`clientes_write.py:79-84` só aceita cpf/cnpj/address). Mesclagem de duplicatas não existe.

### 3.3 O financeiro do evento não fecha o ciclo
`EventInstallment.received` nunca escrito · `substituir_parcelas` apaga e recria as linhas
(`comercial_ops.py:237`), destruindo qualquer baixa · `_compute_cobranca` ignora comprovantes quando
há parcelas (`agenda_read.py:399-403`) → saldo em aberto eterno · parcela vencida some do painel na
virada do mês (`financeiro_read.py:426-433`) · nenhuma das **7** threads toca cobrança de cliente ·
a Planilha de Pagamentos tem 6 fontes de saída e **zero** de entrada.

### 3.4 O pós-evento é memória
Pedido de avaliação manual e sem registro de envio (`feedback_link_pendente` só muda quando a
resposta chega, `agenda_read.py:958`) · feedback recebido não notifica ninguém, nem nota 1 ·
aniversário da criança não gera reativação, embora a Fila 3D já leia idade e nº de aniversariantes
da resposta (`impressoes3d_ops.py:564-589`).

### 3.5 Defeitos confirmados de passagem
Todos com prescrição já registrada em `docs/05_DIVIDA_TECNICA.md` — **vão para a feature 267**:

| # | Prio | Sintoma | Onde |
|---|---|---|---|
| 1 | P0 | marcar comissão EducaManto como paga não faz nada | `financeiro/routes.py:1245` + `financeiro_write.py:213` |
| 2 | P0 | Comissões/Gastos/Dashboard com número velho após pagar | `lib/financeiro.ts:386` e `:285` |
| 5 | P1 | comissão exibida no evento ≠ a que o Financeiro paga | `agenda_read.py:245` + `calendar/routes.py:1752` |
| 6 | P1 | venda preenchida depois não gera linha de comissão | `event_ops.py` (`update_event_core`) |

Fora da dívida, confirmados nesta análise: desvincular formulário pela tela do evento é desfeito pelo
sync seguinte (o caminho da agenda não marca `event_link_locked`, `event_ops.py:894-920`) · excluir
evento deixa a resposta com `event_link_source` obsoleto e religável · `futuros_sem_evento` usa
`date.today()` (`formularios_ops.py:145`) e o KPI "novos este mês" usa relógio do navegador
(`ClientsListPage.tsx:72`) — os dois erram depois das ~21h de Brasília.

## 4. O plano de ondas

| Onda | Entrega | Feature |
|---|---|---|
| 1a | o lead aparece + tudo leva a tudo | **266** (esta) |
| 1b | integridade de vínculo + dívida P0/P1 de comissão | **267** |
| 2 | fundação do funil: FK+status no orçamento, lead com desfecho, prefills ricos, EducaManto→evento, vincular orçamento a evento existente | a planejar |
| 3 | o financeiro que avisa: baixa de parcela, aba Entradas, rotina de lembretes D-3/D0/D+3 | a planejar |
| 4 | o ciclo se fecha: avaliação D+1, follow-up de orçamento, reativação por aniversário, merge de duplicatas, busca global ⌘K | a planejar |

## 5. O que já existe pronto para reusar

Nenhuma onda exige infraestrutura nova.

| Peça necessária | Já existe como | Onde |
|---|---|---|
| Botão que carrega dados adiante | prefill orçamento→evento | `GET /api/events/new/prefill` |
| Vincular registro a evento já criado | endpoint estreito da feature 215 | `PATCH /events/<id>/form-response` |
| Lembrete por data com anti-spam | lembrete de convite | `app/calendar/invite_reminders.py` |
| Aviso que nunca duplica | avisos da Loja Virtual | `UNIQUE(order_id, kind)`, `models.py:3027` |
| E-mail com layout e envio seguro | serviço único | `app/email_service.py` (`send_async`, `_html_wrap`) |
| Identidade única da cliente | telefone normalizado | `Client.phone` UNIQUE, `models.py:1812` |
| Dinheiro entrando sem mãos | webhook da Loja Virtual | `virtuais_ops.py:1257-1266` |
| Rotina de fundo sem duplicar entre workers | claim atômico | calendar-sync · virtual-sweep · invite-reminders |

## 6. Correções de documentação encontradas

A serem aplicadas ao fim do ciclo (`docs/00`, `docs/04`):

1. O auto-vínculo é apontado em `docs/00:68` e `docs/04:396` para `app/formularios/routes.py:246` —
   **arquivo removido** na fase 3 da remoção do Jinja. O código vive em `formularios_ops.py:582`.
2. `docs/00` §2 e `docs/04` §7 falam em **4 threads de background**; existem **7** (faltam
   email-bounce/219, invite-reminders/231 e backup-drive/264).
3. `docs/04` §1 lista como armadilhas três coisas já resolvidas: agrupar/desagrupar ganhou API+UI na
   feature 246, e acréscimos/notas/parcelas ganharam escrita na API na feature 253.

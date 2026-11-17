# Modelo de dados — 349

Migration à mão `a349c0e1f2a3_comercial_mede_e_fecha.py`, `down_revision = "d334b2c4e6f8"`. Aditiva: só colunas
anuláveis em `conversas`, FKs `ON DELETE SET NULL`, um índice, e o preenchimento da primeira mensagem e da primeira
resposta das conversas que já existem. `downgrade` apaga as colunas.

## `conversas` (feature 325) — colunas novas

Todas as datas em **UTC naive**, como o resto da tabela (saem com `+00:00` na API).

| Coluna | Tipo | Regra |
|---|---|---|
| `primeira_recebida_em` | DateTime, null | a mensagem da cliente mais antiga que não é reação; só anda para trás |
| `primeira_resposta_em` | DateTime, null | a primeira resposta válida da equipe com `momento >= primeira_recebida_em` |
| `primeira_resposta_por_id` | FK `users.id` SET NULL, null | autor da resposta; nulo no eco (celular/outro app) |
| `primeira_resposta_origem` | String(12), null | `plataforma` · `celular` · `outro` (valor de `conversa_mensagens.origem`) |
| `perdida_em` | DateTime, null | define "perdida"; nulo = viva |
| `perdida_motivo` | String(30), null | chave de `MOTIVOS_DE_PERDA` |
| `perdida_nota` | String(300), null | frase; obrigatória no motivo `outro` |
| `perdida_por_id` | FK `users.id` SET NULL, null | quem marcou |
| `qualificacao` | String(20), null | `qualificada` · `nao_qualificada`; nulo = segue a regra |
| `qualificacao_em` | DateTime, null | quando decidiu |
| `qualificacao_por_id` | FK `users.id` SET NULL, null | quem decidiu |
| `lembrar_em` | DateTime, null, **índice** | quando o lembrete vence (9h de São Paulo convertida para UTC) |
| `lembrar_para_id` | FK `users.id` SET NULL, null | quem recebe o aviso (quem tocou) |

Relações no model (só leitura): `primeira_resposta_por`, `perdida_por`, `qualificacao_por`, `lembrar_para`
(`foreign_keys` explícito — há várias FKs para `users`).

### Invariantes

- `perdida_motivo`, `perdida_em` e `perdida_por_id` andam juntos; reabrir apaga os quatro campos da perda.
- `perdida_motivo = 'outro'` ⇒ `perdida_nota` não vazia.
- Marcar perdida apaga o lembrete (`lembrar_em`, `lembrar_para_id`).
- `ligar_evento_a_conversa` apaga a perda.
- `primeira_resposta_*` só existe com `primeira_recebida_em` e nunca antes dela.

### Preenchimento (migration)

1. `primeira_recebida_em = MIN(momento)` das recebidas que não são reação, por conversa.
2. `primeira_resposta_*` = a primeira enviada (`DISTINCT ON (conversa_id) … ORDER BY momento, id`) com situação
   `enviada/entregue/lida`, tipo ≠ reação, sem os textos "apagada/editada pelo celular", e `momento >=
   primeira_recebida_em`.

## Constantes (`app/conversas/constantes.py`)

- `MOTIVOS_DE_PERDA` (ordem da tela) e `ROTULO_DO_MOTIVO`: `preco` "Achou caro" · `outra_empresa` "Fechou com outra
  empresa" · `sem_data` "Sem data ou elenco na data" · `desistiu` "Desistiu ou adiou a festa" · `sem_resposta` "Parou de
  responder" · `fora_da_area` "Fora da área atendida" · `outro` "Outro" (pede frase). `PERDA_NOTA_MAXIMA = 300`.
- `QUALIFICACAO_QUALIFICADA = "qualificada"`, `QUALIFICACAO_NAO = "nao_qualificada"`.
- `PONTOS_DA_REGRA = {formulario: 3, data_proxima: 2, data_distante: 1, orcamento: 1, recompra: 2}`,
  `DIAS_DA_DATA_PROXIMA = 90`, `CORTE_DA_QUALIFICADA = 3`, `ROTULO_DO_SINAL`.
- `RECORTES_DA_LISTA = ("esperando", "orcamento_parado", "anuncio")`, `DEGRAUS_DA_REGUA = (2, 5, 9)`,
  `FIM_DA_REGUA_DIAS = 10`, `HORA_DO_LEMBRETE = 9`.
- `RESPOSTA_RAPIDA_MINUTOS = 15` (o "até 15 min" do funil, igual a `ESPERA_PARA_ALERTA`).

## Avisos do sino (`notifications`, feature 272)

| `kind` | Destinatários padrão | `dedupe_key` | Link |
|---|---|---|---|
| `conversa.lembrete` | (explícito) quem marcou; sem acesso → responsável ativo ou equipe | `conversa.lembrete:{id}:{epoch(lembrar_em)}` | `/conversas?c={id}` |
| `conversa.orcamento_parado` | COMERCIAL, SUPERADMIN (com responsável ativo, só ele) | `conversa.orcamento_parado:{id}:{epoch(orcamento)}:{degrau}` | `/conversas?c={id}` |

`entity_type = "conversa"`, `entity_id = conversa.id`. Sem tabela nova.

## Valores derivados (não gravados)

- **Etapa** (régua do funil 335): `chegou → orcamento → formulario → evento → pagou → avaliou`.
- **Sinais e pontos**: `formulario` (formulário da ficha depois do primeiro contato), `data_proxima`/`data_distante`
  (data do evento do fato mais recente entre orçamento e formulário, contada de hoje em São Paulo; data passada não
  soma), `orcamento` (etapa ≥ orçamento), `recompra` (evento vivo da ficha criado antes do primeiro contato).
- **Qualificada** = `qualificacao` se houver; senão `pontos >= CORTE_DA_QUALIFICADA`.
- **Parada** (R6) e o **degrau** da régua (maior de 2/5/9 alcançado, até o 10º dia).

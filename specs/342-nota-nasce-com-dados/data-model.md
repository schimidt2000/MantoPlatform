# Data model — 342

Migration `d342a7c1e9f3` (`down_revision = d323b5a1c0e7`), aditiva.

## Colunas novas

| Tabela | Coluna | Tipo | Sentido |
|---|---|---|---|
| `calendar_events` | `nota_email` | `String(200)`, nulo | e-mail para onde a nota é enviada; vazio = o do cadastro |
| `form_field_definitions` | `show_if_key` | `String(60)`, nulo | chave do campo que controla a exibição |
| `form_field_definitions` | `show_if_value` | `String(200)`, nulo | valor que faz o campo aparecer |

## Colunas que mudam de sentido (sem DDL)

| Coluna | Antes | Depois |
|---|---|---|
| `calendar_events.nota_municipio` | só com ISS retido (apagado sem ele) | município do evento, com ou sem ISS retido |
| `calendar_events.nota_iss_retido` | nulo ≡ falso | nulo = ninguém informou (o formulário pode preencher); falso/verdadeiro = informado |

## Campos semeados (nos dois `form_type`, seção "Nota fiscal", `is_system = true`)

| `field_key` | `field_type` | Obrig. | `show_if` | Rótulo |
|---|---|---|---|---|
| `precisa_nota` | `sim_nao` | não | — | Preciso de nota fiscal |
| `nota_doc` | `cpf_cnpj` | sim | `precisa_nota` = `Sim` | CNPJ ou CPF de quem vai receber a nota |
| `nota_email` | `email` | sim | `precisa_nota` = `Sim` | E-mail para receber a nota |
| `nota_iss` | `selecao` (Não / Sim / Não sei) | sim | `precisa_nota` = `Sim` (+ regra fixa: `nota_doc` é CNPJ) | A empresa retém o ISS da nota? |
| `nota_referencia` | `texto_curto` | não | `precisa_nota` = `Sim` | Precisa que algo apareça na nota? |

## Regras

- Campo com `show_if_key` só é validado e só entra com valor na resposta quando a condição vale.
- `show_if_key` aponta para campo `selecao` ou `sim_nao` do mesmo `form_type`, diferente do próprio.
- Formulário → venda (só em evento principal vivo, só em campo vazio):
  `nota_doc` → `nota_tomador_doc` (dígitos); `nota_email` → `nota_email`; `nota_referencia` →
  `nota_referencia`; `nota_iss` Sim/Não → `nota_iss_retido` quando nulo; "Não sei" não grava.
- `with_invoice`, `event_invoices` e o cadastro do cliente não são escritos por esse caminho.

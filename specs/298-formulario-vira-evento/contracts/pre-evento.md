# Contrato — dados do formulário para o cadastro de evento (feature 298)

Endpoint: `GET /api/formularios/respostas/<id>/para-evento`, com gate `_can_create_event` e só
leitura. Extrator puro: `app/formularios/pre_evento_ops.extrair_para_evento(response)`.

## Resposta

```json
{
  "form_response": { "id": 3994, "form_type": "comum", "form_type_label": "Pré-contrato", "contact_name": "..." },
  "valores": {
    "date": "2026-09-12", "start": "15:00", "end": "18:00",
    "location": "Rua X, 123 - Bairro, Cidade - SP, 01234-567",
    "event_type": "R&I",
    "payment_method": "pix_parcelado", "payment_installments": 2,
    "clients": [ { "client_id": 812, "relation": "Contratante" } ],
    "quick_create_client": null,
    "characters": ["Mickey", "Minnie"]
  },
  "origem": ["date", "start", "end", "location", "event_type", "payment_method", "clients", "characters"],
  "observacoes": [
    { "label": "Tema", "text": "Fundo do mar" },
    { "label": "Aniversariante", "text": "Ana, 5 anos" },
    { "label": "Espaço", "text": "Salão de festas do prédio" },
    { "label": "Personagens pedidos (texto da cliente)", "text": "Mickey e Minnie" },
    { "label": "Observações contratuais", "text": "..." }
  ],
  "alertas": [
    { "campo": "end", "motivo": "periodo_ambiguo", "texto_da_cliente": "3h ou 4h" },
    { "campo": "payment_method", "motivo": "sem_correspondente", "texto_da_cliente": "Boleto" },
    { "campo": "date", "motivo": "data_suspeita", "texto_da_cliente": "04/04/2049" },
    { "campo": "location", "motivo": "endereco_incompleto" }
  ],
  "eventos_da_cliente": [ { "event_id": 1236, "titulo": "...", "data": "2026-07-13" } ]
}
```

- Campo sem valor confiável fica **ausente** de `valores`, com um alerta que traz o texto da cliente.
- `quick_create_client` só existe quando não há ficha nem cliente sugerida pelo telefone:
  `{ name, phone, email, cpf | cnpj }`, para abrir o cadastro rápido já preenchido.
- `eventos_da_cliente` alimenta a FR-013: eventos desde o corte, não cancelados, fora de ensaio e
  satélite, sem formulário ligado, cuja cliente tem o telefone do formulário.
- Valor de venda, vendedor e título **não vêm** do formulário.
- **Data suspeita**: o cadastro não desabilita o Salvar. Ao salvar sem confirmar nem trocar a data,
  marca o campo `date` com a explicação (`setError`) e o efeito de foco existente leva até ele.
- **Todos os campos novos são opcionais no tipo TS**, lidos com fallback.
- **Ao aplicar os `valores`**: `setValue` campo a campo, ou `reset({...getValues(), ...valores})`.
  Nunca um `reset` que zere `sale_date` (hotfix 267b) nem `seller_id`. O efeito é chaveado pelo id do
  formulário.

## Mapa campo → evento (dois vocabulários de chave)

| Evento | Chaves do formulário (nativo · WhatsForm) | Transformação | Alerta |
|---|---|---|---|
| `date` | coluna `event_date` | ISO direto | antes do dia de chegada, ou mais de 2 anos depois → `data_suspeita` |
| `start` | `hora_evento` · hora dentro de `data_do_evento` ("AAAA-MM-DD HH:MM") | "HH:MM". A hora escrita é forte. A de dentro da data (WhatsForm) é a do seletor de data-hora: só vale entre 7h e 23h e com minuto múltiplo de 5 (a produção tem 15:03, 12:04, 04:00), e cede ao início do intervalo escrito no período (corrigido na implementação, 11/09) | ausente ou descartada → `hora_ausente`, com o texto da data |
| `end` | `periodo_contratacao` · `periodo_de_contratacao` | só formas inequívocas: "das X às Y", "X-Y", "Xh-Yh", "N horas" / "Nh" (início + N) | ambíguo ou contradiz a hora → `periodo_ambiguo`, com o texto |
| `location` | comum: `logradouro, numero, complemento, bairro, cidade, estado, cep` · corporativo: `endereco_evento` / `endereco_completo_do_evento` | compõe uma linha; **nunca** `endereco_contratante` nem `endereco_empresa` | sem número ou sem CEP → `endereco_incompleto` |
| `event_type` | `tipo_contratacao` · `tipo_de_contratacao`; corporativo → `CORP` | "Receptivo e Interativo" → `R&I`; texto com "Show" → `SHOW`; demais → vazio | não reconhecido → `tipo_sem_correspondente` |
| `payment_method` (+ `payment_installments`) | `forma_pagamento` · `forma_de_pagamento` (+ `descreva_outros`) | tabela abaixo | sem correspondente → `sem_correspondente`, com o texto |
| `clients` | `client_id` do formulário; senão, a ficha com o mesmo telefone | Contratante | sugerida pelo telefone → `cliente_sugerida` |
| `characters` | `quais_personagens` (+ `qtd_personagens`) | divide por ",", " e ", "+" e "/"; tira vazios | sempre marcado como "confira" |
| observação "Tema" | `tema_evento` · `tema_do_evento` | texto | — |
| observação "Aniversariante" | `nome_aniversariante` + `idade_aniversariante` · slugs | "Nome, N anos" | — |
| observação "Espaço" | `espaco_evento` · `espaco_escolhido_para_o_evento` | texto | — |
| observação "Briefing" (corporativo) | `briefing` · `briefing_do_evento` | texto | — |
| observação "Observações contratuais" | `observacoes` · `observacoes_contratuais` | texto | — |
| observação "Assessoria" | `assessoria` / telefone de assessoria | texto | — |

As chaves exatas de cada vocabulário ficam numa constante de sinônimos no `pre_evento_ops`. O seed
nativo está em `migrations/versions/a51ce3dc4f3c_form_field_definitions.py:32-76`; os slugs WhatsForm,
em `research.md`. Chave desconhecida é ignorada sem erro.

## Forma de pagamento

| Texto do formulário | Evento |
|---|---|
| "À vista" · corporativo "À vista antecipado" | `avista` |
| "Em 2x no PIX (50% no ato + 50%…)" | `pix_parcelado`, `payment_installments = 2` |
| corporativo "Faturado" | `faturado`, com a data a preencher pela comercial |
| "Cartão de Crédito (em até 3x com acréscimo de 15%)" | **sem correspondente**: fica em branco, com o texto |
| corporativo "Em 2x", "Boleto", "Outros" (+ `descreva_outros`) | **sem correspondente**: fica em branco, com o texto |

A comparação usa o texto normalizado: sem acento e minúsculo (`strip_accents_lower`, de
`app/utils.py:15`), com espaços únicos (`" ".join(s.split())`, porque aquela função não junta
espaços). Opção nova, criada pelo
editor de campos, cai em "sem correspondente".

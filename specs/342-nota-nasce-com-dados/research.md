# Research — 342

## R1. O editor suporta campo condicional?

**Não.** `FormFieldDefinition` não tem coluna de condição; `descreva_outros` aparece por regra fixa
em `DynamicForm.tsx` (filtro por `forma_pagamento === "Outros"`) e em `_validate_dynamic`.

- **Decisão**: duas colunas, `show_if_key` e `show_if_value`. O campo aparece (e vale) quando o valor
  enviado do campo `show_if_key` é igual a `show_if_value`. Um nível só: a condição não encadeia.
- **Alternativas**: JSON de regras (linguagem demais para um uso); chaves fixas no código como
  `descreva_outros` (o editor não conseguiria criar outro campo assim, e o pedido dizia que essa era
  a parte nova).
- `descreva_outros` segue com a regra fixa: migrá-lo muda um formulário em produção sem pedido.

## R2. A pergunta-mãe: caixa de marcar ou Sim/Não obrigatório?

- **Decisão**: `sim_nao` (caixa "Preciso de nota fiscal"), opcional. Um toque para quem precisa, zero
  para quem não. O bundle antigo, que não conhece o campo, envia sem ele e passa.
- **Alternativa**: seleção obrigatória Sim/Não. Daria um "não" explícito, mas custa um toque a todas
  as clientes e quebraria o envio do bundle em cache nos minutos do deploy.

## R3. "ISS só para CNPJ"

Depende do tamanho do documento digitado. **Decisão**: regra fixa por chave (`nota_iss`), no motor
(`campo_visivel`) e na tela: visível quando a condição declarada vale **e** `nota_doc` tem 14 dígitos.
O schema público manda `only_for_cnpj_of: "nota_doc"` no campo para a tela não repetir a chave.

## R4. Tipo de campo "CNPJ ou CPF"

Tipo novo `cpf_cnpj` em `FIELD_TYPES`: máscara pelo tamanho, 11 ou 14 dígitos, dígitos verificadores.
Os tipos `cpf` e `cnpj` existentes continuam validando só o tamanho (não é o pedido, e apertar agora
recusaria clientes num campo que hoje passa).

Validação em `app/documentos.py` (módulo novo, sem dependência). CNPJ alfanumérico (julho/2026 em
diante, IN RFB 2.229): a coluna `nota_tomador_doc` guarda só dígitos e a 323 já normaliza com `\D`;
fica fora de escopo e anotado em `docs/05`.

## R5. Onde as respostas entram na venda

`apply_event_link` é o núcleo único do vínculo (298): envio público com casamento por telefone+data,
reprocessamento do sync, associação manual, confirmação de sugestão, edição do evento e criação a
partir do formulário (`_link_form_response`). **Decisão**: chamar a ponte ali, depois de
`_levar_cliente`.

- Na criação a ordem é `_link_form_response` → `gravar_dados_da_nota(body)`: o corpo da tela (que veio
  sugerido pelo formulário e foi conferido pela vendedora) grava por último e vence. Correto: é o
  humano. Sem a chave `nota` no corpo (chip desligado), ficam os dados do formulário.
- Satélite e cancelado: a ponte não escreve (a venda mora no principal; o cancelado já é recusado).

## R6. "Só campo vazio" e a retenção de ISS

`nota_iss_retido` é `Boolean` nulo. Hoje `gravar_dados_da_nota` grava sempre `True/False`. **Decisão**:
nulo = ninguém informou; o formulário só escreve quando está nulo; "Não sei" não escreve. Depois que
a vendedora salva o bloco, o valor é dela. A tela mostra a resposta da cliente ao lado, então a
divergência (cliente "Sim", venda "não retido") fica à vista.

## R7. Documento exigido sem travar o legado

12 das 16 notas pendentes não têm documento. "Editar tudo" é usado por papéis que não vendem.
**Decisão**: recusar só quando (a) o pedido nasce nesta gravação (`with_invoice` de falso para
verdadeiro, ou criação) ou (b) a gravação apagaria um documento que a venda tinha; e só quando não
há documento na venda nem no cadastro da contratante **desta gravação** (criação e "Editar tudo"
trocam os clientes no mesmo corpo). Função pura `erro_de_documento`, chamada pelas três views antes de
qualquer escrita.

## R8. Município

- A 329 decide a incidência por `is_outside_sp`; `nota_municipio` é texto para quem emite no portal.
  Nada muda para ela.
- **Decisão**: `nota_municipio` passa a ser gravado com ou sem ISS retido. A sugestão é calculada na
  leitura, nunca gravada sozinha: (1) `cidade`/`estado` do formulário comum ligado; (2) expressão
  regular sobre `event.location` ("…, Cidade - UF, CEP", "Cidade/UF", "Cidade, UF"), com a lista das
  27 UFs para não casar "Bloco - AB". Sem chamada externa (ViaCEP/Google) no servidor.
- Compatibilidade: a tela antiga manda `municipio: ""` sem ISS retido, o que apagaria um município
  confirmado. Aceito: dura os minutos do deploy e a sugestão volta na próxima abertura.

## R9. E-mail da nota

Coluna nova `calendar_events.nota_email` (String 200). `tomador()["email"]` passa a ser
`nota_email or cliente.email`. Chave nova e opcional no corpo `nota`: `email` ausente = não mexe
(tela antiga); presente = grava (vazio apaga).

## R10. O que a vendedora vê do formulário

`venda.nota.do_formulario` (opcional): `{response_id, pediu_nota, doc, email, iss, referencia}` do
formulário ligado mais recente que pediu nota, lido na hora de `event.form_responses`. Não se copia
para coluna: é a resposta original, e continua lá mesmo depois de a vendedora corrigir a venda.
`venda.nota.municipio_sugerido` idem.

## R11. Migration e as cadeias abertas

Head da `main`: `d323b5a1c0e7`. O CRM (325…335) e a 329 também descem dela, em worktrees sem merge.
Esta migration aponta para a head da `main`; no merge, a segunda a entrar reaponta o
`down_revision` (regra de head único). O `manto_local` está em `d334b2c4e6f8` (CRM): a verificação
usa espelho próprio `manto_342`, criado do dump noturno.

As dez linhas de campo entram na migration (os campos originais também nasceram em migration,
`a51ce3dc4f3c`), com `order` = último + 1…5 de cada formulário e `INSERT … WHERE NOT EXISTS` pela
chave, para o `upgrade` poder rodar duas vezes.

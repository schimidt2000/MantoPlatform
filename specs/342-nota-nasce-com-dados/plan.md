# Plano de implementação: 342 — O pedido de nota já nasce com os dados que a emissão exige

**Branch**: `342-nota-nasce-com-dados` | **Data**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: `/specs/342-nota-nasce-com-dados/spec.md`

## Resumo

Cinco perguntas novas nos dois formulários públicos, quatro delas condicionais; uma condição de
exibição genérica no motor dos formulários (`show_if_key`/`show_if_value`); um núcleo novo que leva
as respostas para os `nota_*` do evento no núcleo único do vínculo (`apply_event_link`), só em campo
vazio; e, na venda, a recusa do pedido de nota sem documento, o e-mail da nota, o município livre do
ISS retido e a sugestão de município. Nenhum endpoint novo.

## Contexto técnico

**Linguagem/Versão**: Python 3.11+ (Flask + SQLAlchemy); TypeScript + React 18 (Vite)

**Dependências principais**: as de sempre; nenhuma nova

**Armazenamento**: PostgreSQL; migration `d342a7c1e9f3` (aditiva)

**Verificação**: `verify_342.py` contra espelho próprio `manto_342` (o `manto_local` está numa
migration da cadeia do CRM, à frente da `main`); `npm run typecheck`; `ruff check`; telas no
Browser pane, as públicas em 375×812

**Plataforma-alvo**: web; formulário no celular da cliente, venda no desktop da equipe

**Tipo de projeto**: SPA desacoplada (API JSON + React)

**Metas de desempenho**: N/A (o detalhe do evento ganha uma leitura de `form_responses` por
`event_id`, coluna indexada)

**Restrições**: `/f/*` é URL gravada em mensagens (não muda); 320–430 px sem rolagem lateral; campo
novo do payload é opcional no React (armadilha 21); servidor novo aceita bundle antigo (a pergunta-mãe
é opcional); nada do que a 329 lê muda de lugar ou de sentido

**Escala/escopo**: 3 colunas, 10 linhas semeadas, 0 endpoints novos, 6 alterados, 4 telas tocadas

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | motor dinâmico da 123 (`_validate_dynamic`, `_build_sections_dynamic`), núcleo único do vínculo (298), `pedido_de_nota_ops` e `DadosDaNotaCampos` (323), `_field_value_by_key` (119) |
| II. Padrões de código | type hints, docstrings, constantes no topo; `ruff check` nos tocados |
| III. Camadas / API First | regra nova em `app/formularios/nota_do_formulario_ops.py` e `app/calendar/pedido_de_nota_ops.py` (puros); as views só chamam |
| IV. Não quebrar o que funciona | migration aditiva; chave `nota` ausente continua "não mexe"; regra do documento não é retroativa; `iss_retido` segue booleano no contrato |
| V. UI/UX com feedback | erro no campo (`fields`), foco no documento, o que a pessoa digitou fica |
| VI. Esteira (Nível 1) | esteira completa |
| VII. Living Spec | spec antes do código |
| VIII. Verify antes do núcleo | `verify_342.py` escrito na fase Foundational |
| IX. Dinheiro BRL | não toca dinheiro; `with_invoice` (que muda preço) nunca é ligado pelo formulário |
| X. Mobile-first público | bloco da nota conferido em 375×812 |
| XI. Framer Motion | abertura do bloco com `AnimatePresence` se o formulário já usa; senão sem animação (não há hoje) |
| XII. Combobox / Maps | município é texto livre com sugestão; sem lista |
| XIII. RBAC declarado | nenhum gate muda; `docs/01` §4.3 sem linha nova |
| XIV. Config / efeito externo | sem env nova; o caminho do formulário não manda e-mail nem escreve no Google |
| XV. Texto por superfície | público: lúdico e claro; interno: imperativo curto; termos "Informe", "a cliente" |
| Stack | migration à mão, `down_revision = d323b5a1c0e7` (head da `main`) |
| Operação e Deploy | não toca `startCommand`; migration aditiva; **três cadeias abertas** (CRM, 329, esta) descem da mesma head: quem mergear depois reaponta o `down_revision` |

## Estrutura do projeto

```text
migrations/versions/d342a7c1e9f3_nota_nasce_com_dados.py
app/models.py                                  # CalendarEvent.nota_email; FormFieldDefinition.show_if_*
app/documentos.py                              # NOVO: cpf_valido / cnpj_valido / doc_valido (dígitos verificadores)
app/formularios/formularios_ops.py             # campo_visivel; validação e seções respeitam a condição; tipo cpf_cnpj; editor grava show_if
app/formularios/nota_do_formulario_ops.py      # NOVO: ler as respostas da nota, levar ao evento, sugerir município
app/formularios/pre_evento_ops.py              # sugestão do chip e dos dados da nota na criação
app/calendar/pedido_de_nota_ops.py             # e-mail, município sem ISS, documento exigido, DV, serialização
app/calendar/event_ops.py, routes.py           # sem mudança de fluxo (gravar_dados_da_nota já é chamado)
app/api/agenda_write.py                        # as três portas chamam a recusa do documento
app/api/formularios_write.py                   # schema com show_if; envio descarta escondidos
app/api/formularios_admin_{read,write}.py      # show_if no dicionário do campo
frontend/apps/public/src/lib/formularios.ts, lib/documento.ts (NOVO)
frontend/apps/public/src/components/formularios/{DynamicForm,DynamicField}.tsx
frontend/apps/internal/src/lib/{notaFiscal,eventFormSchema,formulariosAdmin}.ts
frontend/apps/internal/src/components/EventFormBlocks/{DadosDaNotaCampos,ValoresBlock}.tsx
frontend/apps/internal/src/components/EventDetail/ComercialSection.tsx
frontend/apps/internal/src/components/home/PainelNotasAEmitir.tsx
frontend/apps/internal/src/components/FormFieldEditor.tsx
frontend/apps/internal/src/pages/EventCreatePage.tsx
```

**Decisão de estrutura**: a ponte formulário → nota mora em `app/formularios/` (lê o JSON da
resposta) e chama `pedido_de_nota_ops` para escrever: quem conhece os `nota_*` continua sendo um
módulo só. A validação de CPF/CNPJ vai para `app/documentos.py` porque os dois domínios a usam e
`formularios_ops` é folha (não pode importar `calendar`).

## Rastreamento de complexidade

| Violação | Por que é necessária | Alternativa mais simples rejeitada porque |
|---|---|---|
| Regra fixa "ISS só para CNPJ" no motor (chave `nota_iss`) | a condição depende do **tamanho** de outro campo, não de um valor | generalizar para operadores no editor é uma linguagem de condições para um único uso; fica registrada como dívida ao lado de `descreva_outros` |
| Import tardio de `nota_do_formulario_ops` dentro de `apply_event_link` | `formularios_ops` é folha; a ponte importa `pedido_de_nota_ops` | mover a ponte para `formularios_ops` criaria o ciclo com `calendar` |

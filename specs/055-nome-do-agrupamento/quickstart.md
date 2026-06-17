# Quickstart — Verificação manual da feature 055

Validar o nome do agrupamento e a exibição como entrada única, no app real
(`python run.py`), logado como COMERCIAL, FINANCEIRO ou SUPERADMIN.

> Pré-requisito: feature 053/054 aplicadas; alguns eventos não-ENSAIO; ao menos um com
> valor de venda (será o principal) e outros para virarem satélites.

## Passo 1 — Nomear ao agrupar (FR-001, FR-002)

1. Abra um evento, vá em **Comercial → Agrupar eventos**.
2. Marque 2+ eventos, escolha o principal, **informe um nome** (ex.: "Campanha Mensageiros —
   Empresa X") e confirme.
   - ✅ Grupo criado; o nome fica salvo no principal.
3. Abra o evento principal.
   - ✅ A seção de grupo mostra o **nome do grupo**.
4. Abra um satélite.
   - ✅ O banner azul mostra o nome do grupo.

## Passo 2 — Editar/limpar o nome (FR-002, edge case)

1. No evento principal, edite o nome do grupo e salve.
   - ✅ Botão desabilita ao enviar (anti-duplo-envio); novo nome persiste.
2. Limpe o campo e salve.
   - ✅ Volta a exibir o título do principal (fallback).
3. Tente renomear a partir de um satélite.
   - ✅ Não é permitido (apenas o principal renomeia).

## Passo 3 — Home comercial: uma entrada nomeada (FR-004, FR-005, SC-001)

1. Garanta cobrança pendente no principal e satélites sem valor.
2. Abra a home como comercial.
   - ✅ Aparece **uma** linha de cobrança, identificada pelo **nome do grupo**.
   - ✅ Os satélites **não** aparecem em "eventos sem valor de venda".
3. Um grupo sem nome:
   - ✅ Aparece pelo título do principal (fallback), ainda como uma entrada só.

## Passo 4 — Balanço financeiro: uma entrada nomeada (FR-006, FR-007, SC-003/SC-004)

1. Abra o **Painel Financeiro** (`/financeiro/`) no período do grupo.
   - ✅ A tabela de eventos mostra **uma** linha com o **nome do grupo**.
   - ✅ Os satélites **não** aparecem como linhas próprias.
2. Confira os indicadores consolidados (venda, custo, comissão, lucro).
   - ✅ Idênticos aos de antes (grupo = 1 venda; custos dos satélites somados no principal).

## Passo 5 — Não-regressão (FR-010)

1. Eventos **não agrupados** continuam aparecendo pelo próprio título na home e no balanço.
2. Desagrupe um satélite.
   - ✅ Ele volta às listas pelo seu próprio título; o nome do grupo segue no principal.

## Checklist de qualidade (Portões da constituição)

- [ ] Migration aplicada (`flask db upgrade`) e coluna `group_name` presente.
- [ ] `ruff check` sem erros novos nos arquivos tocados.
- [ ] Comportamento conferido no app real (Princípio IV) — passos 1 a 5.

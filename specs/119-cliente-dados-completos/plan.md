# Implementation Plan: Cadastro de Cliente Mais Completo (119)

**Branch**: `119-cliente-dados-completos` | **Date**: 2026-07-08 | **Spec**: [spec.md](./spec.md)

## Summary

`Client` ganha três colunas de texto livre: `cpf`, `cnpj`, `address`. Em
`app/formularios/routes.py::associar()` (feature 118), depois de resolver o cliente (seja
criado a partir da resposta, seja um já existente selecionado na busca), uma função pura
`_fill_client_from_response(client, response)` extrai CPF/endereço (formulário comum) ou
CNPJ/endereço (corporativo) das seções JSON da resposta e escreve **só nos campos que
estiverem vazios** no cliente — nunca sobrescreve. Ficha do cliente (`clientes/detail.html`)
passa a exibir esses campos e ganha um formulário de edição simples (COMERCIAL/FINANCEIRO/
SUPERADMIN), rota nova `POST /clientes/<id>/update`.

## Technical Context

**Stack**: o existente. **Storage**: 1 migration manual — 3 colunas nullable em `clients`.
`down_revision = "e1f2a3b4c5d6"` (head atual da feature 118), conferir unicidade do
revision novo.

**Arquivos**: `app/models.py` (3 colunas em `Client`), migration nova,
`app/formularios/routes.py` (extração + preenchimento condicional em `associar()`),
`app/clientes/routes.py` (rota `update` nova), `app/templates/clientes/detail.html`
(exibição + formulário de edição).

**Testing**: associar resposta comum a cliente novo → CPF/endereço vêm da resposta;
associar resposta corporativa → CNPJ/endereço da empresa; cliente com CPF já preenchido +
nova associação com CPF diferente → mantém o original; resposta sem CPF (campo condicional
não aplicável) → nada muda; edição manual salva; RBAC da edição.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Reaproveita `associar()` e `data_sections` da feature 118; nenhuma rota pública nova. |
| II. Padrões Python | ✅ Função pura de extração, type hints, docstring. |
| III. Camadas | ✅ Extração/preenchimento em função isolada, chamada pela rota; template só exibe/edita. |
| IV. Não quebrar | ✅ 3 colunas nullable; `associar()` só ganha uma chamada extra no fim, sem mudar o fluxo existente. |
| V. UI/UX | ✅ Preenchimento automático é transparente (sem passo extra pro comercial); edição manual com feedback de sucesso. |
| VI. Planejar | ✅ Este plano. |
| VII. Moeda BR | N/A. |

**Gate: PASS.**

## Decisões

1. **Preencher só campos vazios, nunca sobrescrever** (FR-003): mesma cautela do padrão
   "só liga, nunca desliga" da feature 115 — automação nunca é surpresa negativa; dado que
   a equipe já corrigiu manualmente fica intocado.
2. **Endereço como texto único, não decomposto**: o próprio formulário captura o endereço
   da contratante/empresa como um campo de texto corrido (diferente do endereço do evento,
   que é decomposto) — replicar essa granularidade evita inventar uma estrutura que a fonte
   de dados não tem.
3. **Formulário comum → CPF; corporativo → CNPJ**: cada tipo preenche o campo que faz
   sentido para aquele tipo de cliente (pessoa física vs. jurídica); nenhum formulário
   preenche os dois.
4. **Preenchimento acontece dentro de `associar()`**, não como rota/botão separado: menos
   um passo manual — associar já é a ação que faz sentido completar os dados (FR-002).
5. **Edição manual como rota nova simples** (`POST /clientes/<id>/update`, sem página
   dedicada — formulário inline na própria ficha), coerente com o padrão de
   `quick-create` já existente no módulo.

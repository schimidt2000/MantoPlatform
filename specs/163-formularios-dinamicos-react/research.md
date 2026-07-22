# Research: Formulários Dinâmicos Públicos em React

## §1 — Sem schema de validação client-side estático (diferente da 162)

**Decisão**: `DynamicForm` não valida nada client-side além das máscaras de digitação (cpf,
cnpj, cep, telefone) — toda validação de obrigatoriedade/formato acontece só no servidor
(`_validate_dynamic`), com os erros voltando por campo na resposta 400 e sendo exibidos ao lado
de cada campo (mesmo padrão do banner + destaque por campo do Jinja hoje).

**Razão**: a versão Jinja atual (`_form_scripts.html`) também não faz nenhuma validação
client-side de obrigatoriedade/formato — só máscara de dígitos enquanto digita; a validação real
sempre foi 100% server-side, com o HTML sendo re-renderizado com `errors` quando inválido.
Reproduzir esse mesmo comportamento (sem inventar uma camada de validação client-side nova que
não existia) evita duplicar as regras de formato (CPF/CNPJ/CEP/e-mail/data) que já vivem em
`_validate_dynamic` — e essas regras dependem da definição de campos vigente (não são estáticas
como no cadastro da 162, que tem uma lista fixa de campos conhecida em tempo de compilação).

**Alternativas consideradas**: gerar um schema `zod` dinâmico a partir do schema JSON retornado
pela API — tecnicamente possível (`z.object` construído em runtime), mas adiciona uma camada de
validação client-side que a versão atual nunca teve, sem ganho real (o servidor já valida tudo, e
o Jinja de hoje prova que isso é aceitável para esta superfície); complexidade desproporcional ao
valor entregue nesta fatia.

## §2 — Reaproveitar as funções do motor dinâmico por import direto (sem extrair `_ops`)

**Decisão**: `app/api/formularios_write.py` importa diretamente `FORM_META`, `_load_fields`,
`_grouped_sections`, `_validate_dynamic`, `_build_sections_dynamic`, `_save_response`,
`_attempt_auto_link`, `_build_message`, `_whatsapp_link`, `_build_phone_display`,
`_parse_event_date` de `app/formularios/routes.py` — sem copiar nem mover nada.

**Razão**: diferente da 161 (queries com `render_template` inline, sem função extraível) e da 162
(lógica pura, mas misturada com a orquestração HTTP no mesmo corpo de função, então extraída para
`cadastro_ops.py`), aqui `app/formularios/routes.py` **já** separa 100% da regra de negócio em
funções `_`-prefixadas puras (recebem `request.form`/objetos de modelo, devolvem valor) — só as
funções de rota (`_render_public_form`, `_submit_public_form`, `form_comum`, `submit_comum`,
`form_corporativo`, `submit_corporativo`) misturam HTTP, e essas **não** são reaproveitadas (o
endpoint API escreve sua própria orquestração, retornando JSON em vez de `render_template`).
Extrair essas funções `_`-prefixadas para um módulo `_ops` novo não traria benefício nenhum —
elas já são a "fonte única" que o Princípio I pede, só moradoras do módulo `formularios`
(mesmo precedente de importar função privada entre módulos: `app/cadastro/cadastro_ops.py`
importa `_parse_passport_status` de `app/talents/importer.py`).

**Alternativas consideradas**: mover essas funções para um `formularios_ops.py` novo, espelhando
o padrão da 162 — rejeitado por não resolver problema nenhum (não há duplicação a evitar: as
funções já são únicas e puras) e por inflar o escopo da fatia sem necessidade (YAGNI).

## §3 — Componente de formulário genérico (`DynamicForm`/`DynamicField`)

**Decisão**: `DynamicField` despacha o widget certo por `field_type` (mesmo switch da macro
Jinja `field()` em `_field_macros.html`): `texto_curto`/`email` → `Input`; `texto_longo` →
`textarea`; `selecao` → `select` nativo com as opções do schema; `telefone` → select de DDI +
input mascarado; `data`/`hora` → `input[type=date|time]`; `cpf`/`cnpj`/`cep` → input mascarado
(mesmas máscaras de dígitos da 162/Jinja); `sim_nao` → checkbox (valor `"Sim"` quando marcado,
omitido do envio quando não). `DynamicForm` busca o schema (`useFormSchema(formType)`), mantém
`values: Record<string, string>` (todos os campos, inclusive sufixos `_ddi`/`_national` do
telefone) e `errors: Record<string, string>` (populado pela resposta 400 da API), monta
`FormData` na submissão.

**Razão**: os campos são editáveis pelo painel administrativo (feature 123) e podem mudar sem
deploy — um formulário com campos hardcoded no componente React reintroduziria exatamente o
problema que a feature 123 resolveu no Jinja (formulário fixo no código). Um único componente
genérico, dirigido pelo schema JSON, é a única forma de manter a mesma flexibilidade na versão
React.

**Alternativas consideradas**: gerar 2 componentes React fixos (um por `form_type`) com os campos
de hoje hardcoded — rejeitado porque reintroduziria a rigidez que a 123 eliminou (qualquer campo
novo/removido no painel exigiria deploy de novo, quebrando a FR-001/SC-003 desta spec).

## §4 — CEP: mesma lógica de autopreenchimento (ViaCEP client-side)

**Decisão**: `DynamicForm` chama `https://viacep.com.br/ws/{cep}/json/` diretamente do
navegador (fetch client-side, sem passar pelo backend) quando um campo `cep` perde o foco com 8
dígitos — mesmo comportamento do `<script>` inline em `public_form.html` hoje. Preenche
`logradouro`/`bairro`/`cidade`/`estado` só se esses campos existirem no schema atual E ainda
estiverem vazios; falha silenciosa (sem bloquear o envio) se a consulta falhar ou o CEP não
existir.

**Razão**: é uma chamada de terceiro read-only, sem necessidade de proxy pelo backend (o Jinja
já faz isso direto do navegador hoje); manter client-side evita adicionar uma dependência nova no
backend (requests para ViaCEP) só para repassar uma resposta pública.

**Alternativas consideradas**: proxiar a consulta de CEP por um endpoint novo no Flask —
rejeitado por não ter nenhum ganho (a API do ViaCEP já é pública/CORS-friendly, é isso que o
Jinja já demonstra funcionando direto do navegador) e por adicionar uma dependência HTTP nova ao
backend sem necessidade.

## §5 — "Descreva outros": condicional genérica, não hardcoded por nome de tela

**Decisão**: `DynamicForm` verifica, de forma genérica (não específica de `form_type`), se o
schema atual contém um campo com `key === "descreva_outros"` — se sim, sua visibilidade segue o
valor do campo `key === "forma_pagamento"` (visível e obrigatório só quando esse valor for
`"Outros"`); mesma regra do backend em `_validate_dynamic`.

**Razão**: a regra já é acoplada a essas duas chaves específicas no próprio backend (comentário
em `_validate_dynamic`: "acoplada à chave, não generalizável sem lógica condicional entre campos,
fora de escopo da feature 123") — reproduzir a mesma checagem por chave no frontend (em vez de
inventar uma generalização maior) mantém paridade exata sem expandir escopo além do que o
backend já resolve.

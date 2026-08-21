# Feature 258 — cadastro manual de cliente na tela de Clientes

**Branch**: `258-cliente-manual` · **Created**: 2026-08-21 · **Status**: implementada
**Migration**: nenhuma

## Problema

A base de clientes só crescia por três caminhos automáticos — importação do Kommo, respostas de
formulário e o cadastro rápido de dentro do formulário de evento. Quem estava na tela de Clientes
(o comercial) **não tinha como cadastrar alguém ali**: precisava abrir um evento para conseguir
criar a ficha, ou esperar a próxima importação.

## Solução

Botão **"Nova cliente"** no cabeçalho da tela `/clientes` (e também no estado vazio da busca,
onde a falta dele era mais sentida) abrindo um diálogo com nome, telefone, e-mail, empresa, CPF,
CNPJ e endereço.

Reaproveita o endpoint que já existia (`POST /api/clientes/quick-create`, feature 165) — mesmo
gate (`COMERCIAL`, `FINANCEIRO`, `SUPERADMIN`) e **mesma regra de telefone único**.

### Decisões

1. **Telefone repetido não duplica.** O servidor devolve a ficha existente com `reused: true`;
   o diálogo mostra "Esse telefone já estava cadastrado — nada foi duplicado" com atalho para
   abrir a ficha dela. Cadastro duplicado silencioso seria pior que o problema original.
2. **Reaproveitar não sobrescreve.** Quando o telefone já existe, o cliente volta intocado —
   um cadastro rápido não pode apagar o CPF/nome que alguém já tinha conferido.
3. **CPF/CNPJ e endereço entram na criação** (`quick_create_client` ganhou os três campos, todos
   opcionais). Quem cadastra pela tela de Clientes costuma estar com o contrato ou a nota na
   mão; sem isso seria criar e reabrir a ficha para completar. O formulário de evento
   simplesmente não manda esses campos e segue igual.
4. **Lista e métricas se atualizam sozinhas** (invalidação de `clientes-list`,
   `clientes-metricas` e `clientes-search` no `useQuickCreateClient`): um cadastro que não
   aparece na lista parece que não salvou. Reaproveitamento não invalida nada — a base não mudou.
5. **`source="manual"`**, então o cadastro aparece separado de Kommo/formulário no gráfico de
   novos clientes por mês, que já quebrava por origem.

## Verificação

`specs/258-cliente-manual/verify_258.py` contra o `manto_local` — 7/7:
criação completa (com `source`, documentos e endereço), telefone repetido (reaproveita, não
duplica, não sobrescreve), normalização do telefone (DDI 55 — regra do `normalize_phone`),
validação de nome/telefone com o campo apontado no 400, RBAC (CASTING → 403) e presença na
listagem e nas métricas.

Na tela (manto_local, superadmin): diálogo abre com os 7 campos e foco no nome; enviar vazio
bloqueia com erro em nome e telefone; cadastro real aparece na lista sem recarregar a página;
telefone repetido cai no aviso de reaproveitamento com a ficha existente.

## Fora de escopo

Editar nome/telefone/e-mail/empresa depois (a ficha edita CPF/CNPJ/endereço; o resto continua
vindo da origem) e mesclagem de clientes duplicados — pendência antiga registrada em
`docs/03` na entrada de clientes/formulários.

# 306b — O motivo do cancelamento editável por Superadmin e Comercial

**Branch**: `306b-motivo-editavel` · **Created**: 2026-10-20 · **Status**: Implementada (aguarda o push
do dono) · **Migration**: nenhuma

## O pedido

Na manhã do deploy da 306 (20/10), uma Superadmin cancelou um evento escrevendo no motivo o que a
cliente tinha dito. Depois percebeu que o motivo aparece para todo usuário interno que abre o
evento, e quis tirar o texto. Mas o cancelamento não tem volta, e o motivo também não se editava.
O dono: "Faça com que o motivo do cancelamento seja editável por superadmin e comercial". Sobre o
histórico (20/10): **trocar no histórico também**, para o motivo antigo sumir de toda tela.

## O que muda

- **Quem edita**: Superadmin ou Comercial, pelo papel **real** (o "Ver como" não conta, a mesma
  régua de `pode_editar_venda_do_cancelado`). Financeiro e os demais papéis veem o motivo, mas não
  o editam.
- **Onde**: `PATCH /api/events/<id>/motivo-cancelamento` com o corpo `{motivo}`.
  - 404 sem evento; 403 sem papel; 409 `nao_cancelado` no evento vivo; 400 `fields.motivo` com
    o texto vazio, a mesma frase do diálogo de cancelar.
  - Responde `{ok, motivo, eventos}`, onde `eventos` são os ids dos dias que receberam o texto.
- **Alcance**: o motivo é do ato. A edição vale para o evento da URL e para os outros dias do
  mesmo grupo que estão cancelados com o **mesmo** motivo (o ato de "todos os dias" grava o mesmo
  texto em cada dia). Dia cancelado com outro motivo não muda. O grupo é travado antes (`travar_grupo`).
- **Histórico**: nas linhas do `EventLog` e do `AuditLog` (`event_cancelled`) desses dias, o
  motivo antigo é trocado pelo novo onde ele aparece logo depois dos prefixos que o cancelamento
  grava:
  - `Evento cancelado: ` (306 e 224);
  - `Dia cancelado: `;
  - `Evento cancelado com todos os dias do grupo de "…": `.

  A troca só vale quando o texto antigo vem seguido de ` | ` ou do fim da linha. Cada dia ganha
  ainda uma linha nova, "Editou o motivo do cancelamento", **sem** o texto antigo.
- **Tela**: no banner "Evento cancelado" do detalhe, um botão "Editar motivo" (flag
  `can_edit_motivo_cancelado`, que segue o "Ver como" como as outras flags) abre um diálogo com o
  texto atual. O erro do servidor aparece no campo. Cancelamentos e a ficha da cliente leem o
  mesmo campo e mudam sozinhos.
- **Nada mais muda**: o dinheiro, a comissão, os avisos e o Google ficam como estão. Os e-mails aos
  artistas e o sino do Casting já não levavam o motivo.

## Verificação

`specs/306b-motivo-editavel/verify_306b.py` contra o `manto_local`, com cenários vermelhos antes do
núcleo:

1. O Comercial edita: banner, histórico (as duas tabelas) e linha nova sem o texto antigo.
2. O Superadmin edita; o "Ver como Comercial" não muda o papel real.
3. **Deve falhar**: Financeiro e Casting recebem 403, e o banco fica intacto.
4. **Deve falhar**: o evento vivo recebe 409 `nao_cancelado`.
5. **Deve falhar**: o texto vazio recebe 400 `fields.motivo`.
6. Grupo cancelado inteiro: a edição pelo principal muda todos os dias. O dia cortado antes, com
   outro motivo, não muda.
7. A troca não pega um motivo mais longo que comece com o antigo, e não pega o texto antigo solto
   no meio de outra linha.
8. A flag `can_edit_motivo_cancelado`: verdadeira para Comercial e Superadmin no cancelado, falsa
   no vivo e para os outros papéis.

Mais: o `verify_306.py` inteiro, que dá 67/69. Os vermelhos 14b e 20 são as provas de mutação que
precisam da `main` de antes da 306; desde o merge `d29166f` a `main` já a contém. Também o typecheck,
o build, o `ruff` e a tela aberta do banner e do diálogo (Comercial em desktop e a 375px; Financeiro
sem o botão).

## Fora de escopo

- Esconder o motivo de algum papel. O dono pediu edição, não sigilo.
- Desfazer o cancelamento.
- Editar o motivo da solicitação de exclusão (`deletion_request_reason`).

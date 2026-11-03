# 326 — Novo evento: o nome da cliente fica, o telefone tem máscara e o orçamento se associa na tela

**Branch**: `326-novo-evento-cliente-e-orcamento` · **Created**: 2026-10-30 · **Status**: Entregue (na branch; `verify_326.py` 6/6, tela conferida) · **Migration**: nenhuma

## O pedido

O dono, criando um evento em 30/10: "digitei o nome da cliente e depois cliquei em cadastrar o cliente. Aí ele perde o
nome que eu escrevi. Tá faltando a máscara no telefone." E: "depois eu lembrei que tinha um orçamento já feito. Seria
interessante que ali logo nas primeiras coisas eu pudesse já associar um orçamento. […] Às vezes ela vai em novo
evento e lembra."

## O que muda

Nível 2: só o app interno, sem migration e sem endpoint novo. O orçamento reaproveita os dois endpoints que a tela já
consumia (`GET /api/orcamento/historico` e `GET /api/events/new/prefill`); os gates são o mesmo conjunto (Comercial e
Superadmin), e o verify prova isso.

1. **Nome perdido.** A busca de cliente (`ClientPicker`) e o cadastro rápido guardavam o texto em estados separados:
   "+ Cadastrar nova cliente" abria o formulário vazio. Agora o que foi digitado na busca entra no cadastro, como
   nome, ou como telefone quando é um número.
2. **Máscara do telefone.** `mascaraTelefone` nova em `@manto/ui`: `(11) 98765-4321` enquanto se digita; com `+` ou
   com mais de 11 dígitos vira número com DDI (`+55 (11) 98765-4321`, `+351 912345678`), que o servidor já aceita
   (`normalize_phone`, 10 a 13 dígitos). Vale no cadastro rápido do Novo evento e no "Nova cliente" da tela de
   Clientes, que tinham o mesmo campo cru.
3. **Associar orçamento no Novo evento.** Bloco "Orçamento" no topo do formulário, com a mesma busca do vínculo da
   aba Comercial (`OrcamentoPicker`, feature 273: cliente ou local, com o selo de quem já virou evento). Ao
   selecionar, o `orcamento_id` vai para o endereço (o mesmo da entrada pelo Histórico de orçamentos) e o
   pré-preenchimento de sempre roda. "Trocar" e "Desvincular" (os verbos da aba Comercial) desfazem; os botões de
   duração passam para dentro do bloco. Orçamento que já virou evento vivo é recusado no bloco (a criação daria 409).
   - **O que a pessoa já digitou fica.** Data, horário, local, valores e nota só são preenchidos pelo orçamento se o
     campo não foi alterado à mão (`getFieldState().isDirty`); o que o orçamento anterior preencheu é trocado pelo
     novo.
   - **Elenco**: o do orçamento vem primeiro e na ordem dele (o teto do cachê casa por posição no servidor); quem já
     estava na lista com o mesmo nome mantém talento, figurino e cachê; personagem digitado que o orçamento não tem
     vai para o fim, como linha acrescentada à mão.
   - Remover o vínculo tira os cachês do orçamento (`orc_caches`) e mantém o resto do que está na tela.

## Verificação

- `verify_326.py`: os dois endpoints do bloco respondem à Comercial e recusam (403) Financeiro e Casting — o bloco só
  funciona porque o gate do histórico é o mesmo da criação.
- `npm run typecheck`; tela aberta no Browser pane (nome levado ao cadastro, máscara, associar/trocar/remover
  orçamento, campo digitado preservado), sem salvar o evento (a criação escreve no Google Agenda).

**Resultado (30/10):** `verify_326.py` 6/6; typecheck limpo nas três SPAs; tela conferida com backend de Google dublado
e usuário Comercial descartável — nome levado ao cadastro; `(11) 98765-4321`, `(11) 3210-4455`, `+351912345678` e
`+55 (11) 98765-4321`; vincular com local e valor digitados preservados; elenco "homem aranha" + "Mulher Maravilha" →
Homem Aranha, Capitao America, Mulher Maravilha; troca tira o elenco do anterior; orçamento ocupado recusado com link;
desvincular; entrada antiga `?orcamento_id=` igual.

## Fora de escopo

- Máscara de CPF/CNPJ do cadastro rápido.
- Ficha da cliente sugerida a partir do nome do orçamento (o orçamento guarda só o nome, sem vínculo com `Client`).
- Associar orçamento na edição do evento — já existe pela tela do evento (feature 273).

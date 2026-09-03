# Feature 274 — O casting devolve o acesso ao portal para o artista

**Branch**: `274-reset-senha-pelo-casting` (da `main`, já com 269b/239b/273) · **Created**: 2026-09-03
**Status**: Pronto, aguardando push · **Migration**: nenhuma

> O número 274 estava reservado no plano das ondas (`specs/266-costuras-funil/ondas-2-4-plano.md`)
> para "cliente do orçamento como FK". Aquele item, e os seguintes, andam um número — o plano já
> avisa que a numeração dele é provisória e que o número definitivo se confere em `docs/03`.

## O pedido, nas palavras do dono

"Brenda de Lima Lopes e Tais Rangel não conseguem logar. Verifique o status de login no portal e se
as ferramentas de redefinição de senha estão corretas." E, depois do diagnóstico: "Sim, prepare
esse botão."

## O que o diagnóstico mostrou

As duas contas estavam **boas**: ativas, com senha definida, termos aceitos, e o login as encontra
tanto por CPF quanto por e-mail. O que travava era o caminho de recuperação, por dois motivos
diferentes:

1. **Tais Rangel** pediu redefinição em **01/09 às 13h55** e o token continua lá, sem uso. Ela
   recebeu o e-mail no auge do defeito da 269b: o botão apontava para `http://localhost:5000`.
   Corrigido, mas o pedido dela morreu.
2. **Brenda de Lima Lopes** nunca chegou a ter um token. `request_password_reset` só emite quando
   o e-mail digitado bate **exatamente** com `email_contact`, e quando não bate **não faz nada e
   não avisa** — é assim de propósito, para não revelar quem é cadastrado. O e-mail dela é
   `brendalloopes@gmail.com`, com dois L e dois O: quem digita "brendalopes" vê a mesma mensagem de
   sucesso e não recebe nada.

E o autoatendimento não tinha saída para nenhum dos dois casos: **"Primeiro Acesso" recusa quem já
tem senha** (`start_first_access`), e "Esqueci minha senha" é o caminho que já falhou. Do lado de
dentro **não existia ferramenta nenhuma** — nem um botão, nem um endpoint.

Outras oito pessoas estão na mesma fila: pediram redefinição entre 18/08 e 02/09 e ficaram com o
token pendente (Welthon, Marlon, Caroline, Raul, Rodrigo, Bruno, Lucimara e a própria Tais).

## Solução

**Seção "Acesso ao portal" na ficha do talento**, para quem gere talento (CASTING/SUPERADMIN, a
mesma régua de quem edita o cadastro):

- Mostra o que a pessoa que atende precisa saber: se o artista **já definiu senha** alguma vez, o
  **e-mail do login** em tamanho de leitura, e se há **link em aberto** (com a validade).
- Botão **"Enviar link de redefinição"**, com confirmação, que manda o e-mail de redefinição para o
  endereço cadastrado. Serve para quem tem senha e para quem nunca teve — desde a 259 o mesmo link
  define a primeira senha.
- A resposta repete o endereço: *"Link enviado para brendalloopes@gmail.com. Vale até 03/09 às
  21:01. Se o artista não receber, confira se este é mesmo o e-mail dele antes de reenviar."* É
  lendo o endereço em voz alta que se acha o erro de digitação — foi o caso da Brenda.
- Sem e-mail no cadastro, o botão fica desabilitado e a seção diz o que fazer.

**Backend**: `POST /api/talents/<id>/reset-senha` (`talents_write.py`, gate `_can_edit_talent`),
`enviar_reset_pelo_staff` em `portal_account_ops.py`, e o bloco `portal` no `GET /api/talents/<id>`
(só para quem gere talento). O token nasce em `emitir_token_de_reset`, agora **fonte única** dos
dois fluxos: o pedido do artista e o envio pelo casting só divergem em quem tem direito de pedir.

## Decisões

1. **O e-mail volta inteiro, não mascarado.** No fluxo público a máscara existe contra enumeração
   de conta; aqui quem chama já está com a ficha aberta e precisa conferir a grafia. Mascarar
   esconderia exatamente o defeito que o botão existe para resolver.
2. **Erro é devolvido, ao contrário do fluxo público.** Talento sem e-mail → 400 explicando. O
   silêncio protege contra enumeração quando quem pede é anônimo; para quem atende, silêncio é
   perda de tempo.
3. **Enviar de novo invalida o link anterior.** Um token por talento, sempre o último. Nunca dois
   links vivos.
4. **Nada de definir senha pelo painel.** O staff não escolhe, nem vê, senha de artista: manda o
   link e a pessoa escolhe. Mantém o modelo de 259 e evita senha combinada por WhatsApp.
5. **Fica no `AuditLog`.** É ação em nome de outra pessoa, com efeito na caixa de entrada dela.
6. **A validade é convertida para São Paulo na exibição.** O token vive em UTC e a comparação
   continua em UTC; só o que a pessoa lê converte. A tela chegou a dizer "vale até 00:01" para um
   link que expirava às 21:01 — a armadilha de fuso que a plataforma já pagou na agenda.

## Verificação

`verify_274.py` 8/8 contra `manto_local` com o SMTP dublado (nada é enviado): envio pelo casting
com token gravado, e-mail com link do portal público e trilha no `AuditLog`; talento sem senha
recebendo o mesmo link; talento sem e-mail com 400 e sem token; FINANCEIRO 403 e inexistente 404; o
link entregue redefinindo a senha de verdade; segundo envio invalidando o primeiro; bloco `portal`
aparecendo só para quem gere talento; validade dentro da janela de 1 hora em horário de São Paulo.
`npm run typecheck` limpo, `ruff` no baseline. Em tela, na ficha da Brenda no espelho: seção
renderizada com o e-mail correto e o envio confirmando o destino.

## Fora de escopo

Reenviar em lote para as oito pessoas com token pendente (é decisão do dono, e o botão agora
resolve caso a caso); trocar o e-mail do talento por aqui (o cadastro já edita); qualquer forma de
o staff ver ou definir a senha; aviso automático para quem pediu redefinição durante a janela do
defeito da 269b.

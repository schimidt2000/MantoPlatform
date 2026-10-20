# 311 — Aviso do prazo de pagamento (até 3 dias úteis) + a data do aceite no termo

**Branch**: `311-aviso-prazo-pagamento` · **Created**: 2026-10-20 · **Status**: pronta na branch (verify 8/8), aguardando deploy ·
**Migration**: nenhuma

## O pedido

Na prática o cachê sai em 2 dias úteis, e o banco de talentos se acostumou com isso. Quando o banco
atrasa e o pagamento cai no terceiro dia útil, a equipe sai mandando mensagem. O prazo escrito
sempre foi outro: o Termo de Consentimento do portal diz "em até 3 (três) dias úteis após a
realização do evento" desde a primeira versão (`app/templates/portal/terms.html`, commit
`37b61267`, 06/04/2026; primeiro aceite registrado em 30/04/2026). O dono quer avisar a base
inteira por e-mail e mostrar a cada pessoa onde está o termo que ela aceitou.

Contagem no backup de 20/10/2026 02:00: 309 talentos ativos, **181 aceitaram e 128 não** (122
nunca criaram senha; 30 já trabalharam em evento sem o aceite). Por isso o e-mail não pode dizer
"todo mundo aceitou": diz que quem entra no portal aceita o termo no primeiro acesso, e a versão
de quem não aceitou leva ao aceite.

O dono (20/10): "cria o comando e traz a data do aceite".

## O que muda

- **Comando `flask campanha-prazo-pagamento`** (`app/cli.py`), no molde do `campanha-fotos`
  (293): **dry-run por padrão**; `--enviar`, `--limite`, `--pausa` (3 s) e `--id` (repetível).
  - Público: talentos `active` com e-mail.
  - Pula quem tem devolução permanente em aberto contra o `email_contact` atual, e lista essas
    pessoas com o link `wa.me` pronto.
  - Pula quem já recebeu: uma linha no `AuditLog` (`campanha_prazo_pagamento_311`) por envio que
    deu certo, então rodar de novo não repete.
  - Uma conexão SMTP para o lote.
  - O dry-run imprime um exemplo de cada versão e não grava token.
- **Duas versões do e-mail** (`send_prazo_pagamento_email`, `app/email_service.py`), com o mesmo
  assunto, "Prazo de pagamento: até 3 dias úteis":
  - **Aceitou**: "Você aceitou esse termo em 12 de junho de 2026". O botão "Ver o termo que
    aceitei" leva a `{PORTAL_URL}/termos`; quem estiver sem sessão passa pelo login e volta para lá.
  - **Não aceitou**: diz que o termo aparece no primeiro acesso.
    - Sem senha, ou com senha temporária (`must_change_password`): o botão é um link de criar senha
      (`CAMPANHA_RESET_TTL`, 7 dias) com `?destino=/termos`.
    - Com senha própria: o botão leva a `/termos`, e o texto lembra do "Esqueci minha senha".
- **A data do aceite volta à tela do termo**. A versão Jinja da 091 mostrava "Você aceitou em
  DD/MM/AAAA", e isso se perdeu na migração para React (191).
  - `GET /api/portal/auth/me`, o login e o aceite ganham `terms_accepted_at`: horário de parede de
    São Paulo em ISO ingênuo, a convenção do portal (`lib/format.ts`). O campo `terms_accepted`
    continua igual.
  - `/termos` mostra "Você aceitou este termo em 12 de junho de 2026."
  - A coluna continua em UTC (`datetime.utcnow()`); só a exibição converte, como em
    `expiracao_para_exibir`. Sem isso, um aceite às 22h sairia com a data do dia seguinte.

## Verificação

`specs/311-aviso-prazo-pagamento/verify_311.py` contra o `manto_local`, com `MAIL_SUPPRESS_SEND`:

1. O dry-run classifica nos baldes certos (aceitou / não aceitou / bounce / já recebeu / sem
   e-mail), não envia nada e não grava token.
2. `--enviar` manda uma mensagem por pessoa e marca o `AuditLog`. Uma segunda rodada manda zero.
3. Versão "aceitou": traz a data em São Paulo e o link `/termos`, sem link de senha.
4. Versão "não aceitou, sem senha": traz o link de criar senha com `destino=%2Ftermos` e a
   validade de 7 dias. Versão "não aceitou, com senha": traz `/termos`, sem token.
5. **Deve falhar**: um aceite às 01:30 UTC sai com a data do dia anterior em São Paulo, não com a
   data UTC.
6. `/api/portal/auth/me` devolve `terms_accepted_at` em São Paulo para quem aceitou e `null` para
   quem não aceitou.
7. Nenhum corpo leva `localhost`, e todo corpo diz "até 3 dias úteis".

Mais: `ruff check` nos arquivos tocados, `npm run typecheck` e a tela `/termos` aberta a 375px.

## Fora de escopo

- Mudar o texto do termo. Ele é jurídico, e o prazo já é esse.
- Exigir o aceite para escalar ou para pagar (os 30 que trabalharam sem aceitar). Fica registrado
  no `docs/05`.
- Mandar por WhatsApp. O comando só lista quem tem e-mail morto.

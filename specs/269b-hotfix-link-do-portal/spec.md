# Hotfix 269b — O convite que mandava o artista para o localhost

**Branch**: `269b-hotfix-link-do-portal` (da `main`) · **Created**: 2026-09-03
**Status**: Pronto, aguardando push · **Migration**: nenhuma

## O pedido, nas palavras do dono

"Olha o link que está indo nos convites pelo email. Precisamos resolver isso em definitivo, para
que as pessoas não recebam o link localhost. Isso é inadmissível." (print de um convite real com o
botão "Acessar portal e confirmar" apontando para `http://localhost:5000`.)

## Causa

A variável de ambiente **`PORTAL_URL` está setada com `http://localhost:5000` na produção**. Não é
o `.env` local vazando: o `.env` é gitignored e não vai no deploy — o valor mora no painel do
Render (`render.yaml` declarava a chave como `sync: false`) e é idêntico ao que o `.env.example`
sugeria. Confirmado por SSH no serviço `srv-da8o06on74is73ehf4q0`:

```
PORTAL_URL=http://localhost:5000
FLASK_ENV=production
```

A feature 269 (01/09) atacou este mesmo sintoma nas mensagens **copiadas por humano** e deu default
real à variável, mas registrou de propósito que os e-mails do **servidor** continuariam lendo a
env, "onde um ambiente de teste precisa mesmo apontar para si". Default protege quem **esquece** de
definir a variável; não protege quem a define **errada** — e era esse o caso em produção.

## Alcance

Tudo que passa por `email_service._portal_url()`: convite, lembrete de confirmação (231), aviso de
remoção, aviso de mudança do evento, anúncio do portal, boas-vindas — e
`talent_portal/portal_links.portal_reset_url`, a **redefinição de senha**.

Convite e lembrete têm contorno (a mensagem de WhatsApp da 269 leva o endereço certo, e quem já usa
o portal o tem salvo): em produção, agosto fechou 176 de 194 convites aceitos e julho 186 de 196.
A redefinição de senha **não tem contorno** — o link é o único caminho e estava morto.

## Correção, em duas camadas

1. **`app/config.py::_url_para_fora`** — `PORTAL_URL` e `PUBLIC_BASE_URL` só aceitam endereço
   alcançável de fora: esquema `http`/`https` e host que não seja `localhost`, `127.x`, `0.0.0.0`,
   `::1`, faixa privada (`10/192.168/172.16-31`), `host.docker.internal` ou `.local`. Valor
   recusado cai na constante pública (`PORTAL_BASE_URL` / `PLATFORM_BASE_URL`) e entra em
   `AVISOS_DE_URL`, que `create_app` grita no log do deploy — config errada e invisível é a origem
   deste hotfix. O boot também registra sempre `[links externos] portal=… plataforma=…`.
2. **`email_service._send`** — nenhum e-mail sai com link local no corpo, venha de onde vier
   (`url_for(_external=True)`, host do request, string colada à mão). Recusa com log de erro
   nomeando o link e as variáveis a conferir.

**Como o ambiente local continua podendo apontar para si** (a necessidade que a 269 registrou): a
permissão usa o mesmo sinal que já decide se o processo fala com pessoas reais — `_suppress_mail()`.
Banco local ⇒ e-mail suprimido ⇒ o valor local é aceito. `MAIL_ALLOW_LOCAL_SEND=true` (o pedido
explícito de "quero enviar de verdade daqui") destrava o envio e é o único jeito de deixar sair um
e-mail com link local, porque nesse caso quem testa é o próprio destinatário.

De carona: `PORTAL_URL` saiu do `render.yaml` (não ter a variável é melhor que tê-la certa), o
`.env.example` deixou de sugerir o valor local, e `api_notificar_pagamento` perdeu o fallback para
`request.url_root` — que atrás do proxy reverso já era o endereço errado, como o próprio comentário
dizia.

## Decisões

1. **Sanear, não derrubar.** Recusar o boot com env errada tiraria a produção do ar por um detalhe
   de configuração; ignorar o valor e gritar no log conserta o dano e deixa rastro.
2. **A trava mora no caminho da mensagem.** Só corrigir a variável no painel resolveria hoje e
   deixaria a armadilha armada para o próximo deploy, serviço recriado ou staging.
3. **O escape hatch é o mesmo que já existia.** Nenhuma variável nova: quem já podia enviar e-mail
   de um ambiente local continua podendo, com link local inclusive.
4. **Sem migration, sem mudança de UX.** Só configuração e envio.

## Verificação

`verify_269b.py` 6/6 contra `manto_local`, SMTP dublado (nada é enviado): config em processo que
envia de verdade (ignora local, 2 avisos) × processo local (mantém, sem aviso) × envio local
explícito (volta ao público); 23 endereços aceitos/recusados um a um; `_send` recusando três formas
de link local sem tocar no SMTP e passando com link público; convite de papel real do espelho com
link público e, com `PORTAL_URL` forçada para localhost, barrado antes de sair; reset de senha
público. Smoke de boot nas duas pontas mostrando o `ERROR` do valor recusado e o `INFO` dos
endereços efetivos. `ruff` no baseline.

## Pendência do dono (painel, não é código)

Apagar a variável `PORTAL_URL` do serviço `manto-backend` no Render. Depois do deploy o valor já é
ignorado, mas enquanto ela existir cada boot vai gritar que foi recusada.

## Fora de escopo

Reenviar os convites pendentes (62 em produção) e avisar quem tentou redefinir senha — decisão do
dono, não do código. Auditoria das outras variáveis de ambiente do serviço (`GOOGLE_OAUTH_REDIRECT_URI`,
`S3_PUBLIC_URL`) ficou registrada como próxima varredura.

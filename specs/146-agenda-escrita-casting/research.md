# Research — escrita de casting (146, US1 escalar)

## 1. Como reusar a lógica sem duplicar nem quebrar o Jinja

**Decisão**: extrair o núcleo de `_handle_assign_casting` para `casting_ops.assign_role(...)`
com parâmetros explícitos (sem `request.form`, `flash`, `current_user`). O handler Jinja vira
wrapper fino (lê form + current_user, chama o núcleo, dá `flash`); a API é o segundo adaptador.

**Rationale**: é a única forma de ter UMA implementação da regra (cap, invite, e-mails)
servindo os dois caminhos (Princípio I) sem reescrever. O risco — mudar o comportamento do
Jinja ao transformá-lo em wrapper — é coberto pela verificação de paridade (Jinja×API×esperado).

**Alternativa rejeitada**: reimplementar a lógica na API. Divergiria (esquecer e-mail/cap) e
duplicaria ~90 linhas de regra sensível. Inaceitável numa ação com efeito colateral real.

## 2. E-mails no teste

**Decisão**: a verificação monkeypatcha `app.email_service.send_async` (usado pelo núcleo)
para capturar as chamadas em vez de enviar. Assim testamos "quantos convites/remoções seriam
enviados" sem mandar e-mail real contra dados de produção espelhados.

**Rationale**: os e-mails são parte do comportamento a preservar (SC-002: exatamente um
convite), mas disparar e-mail real num script de verificação é inaceitável.

## 3. Conflito de talento: avisar, não bloquear

**Decisão**: o endpoint NÃO recusa por conflito de disponibilidade — grava e devolve o estado,
igual ao Jinja (que só sinaliza na UI, não bloqueia). O aviso visual de conflito no seletor é
melhoria separada.

**Rationale**: paridade. Bloquear seria mudar a regra de negócio; fora do escopo desta fatia.

## 4. Idempotência do ponto de vista do usuário

**Decisão**: escalar atualiza a MESMA linha do cargo (não cria linha nova). Reenviar a mesma
requisição não gera 2º cargo. O 2º envio pode reprocessar (novo log/e-mail se o talento mudou),
mas com o mesmo talento+cachê é essencialmente no-op de estado. O front previne o clique-duplo
com feedback de pending (Princípio V).

**Rationale**: "um clique a mais nunca cria registro duplicado" — como a operação é um UPDATE
do cargo (não INSERT), isso é naturalmente satisfeito para a linha; o front cobre a UX.

# Pesquisa — 333 Orçamento e formulário pela conversa

As decisões de produto vieram do dono (spec, Clarifications); aqui está só o "como".

## R1 — O envio do orçamento reaproveita o envio da conversa

- **Decisão**: `app/conversas/costura_ops.py` (`enviar_orcamento`) não fala com a Meta. Ele chama `envio_ops.enviar_texto`
  para cada parte da mensagem e `envio_ops.enviar_arquivo` para o PDF, que já fazem a chave idempotente, a trava, a
  janela, o commit antes da chamada e o "não entregue" com o motivo.
- **Chave**: a tela manda uma `chave_envio` (UUID, 36 caracteres). As partes usam `{chave}:1`, `{chave}:2`… e
  `{chave}:pdf`, dentro do teto de 64. Repetir a chave refaz o mesmo pedido: cada parte já enviada volta como está, e
  uma parte que faltou (queda no meio) sai agora.
- **Pré-condições antes de tudo**: canal, trava e janela são conferidos uma vez, antes de criar a ficha e o registro.
  Com a janela fechada, nada nasce (cenário 5). Para isso, o `envio_ops` ganha a função pública `conferir_envio`, que
  é o `_pre_condicoes` de hoje.
- **PDF**: `gerar_orcamento_pdf(quote_for_entry(entry))`, o mesmo do download, com o mesmo nome
  (`Orcamento_Manto_<cliente>.pdf`). O PDF só é gerado se a parte do PDF ainda não existe pela chave.
- **Ordem**: as partes do texto e depois o PDF, uma a uma, cada uma no próprio commit. A falha da Meta numa parte não
  levanta (a mensagem fica "falhou"), então a seguinte ainda sai; a recusa de pré-condição (a janela fechou no meio)
  levanta e para.

## R2 — Divisão do texto

- **WhatsApp**: `TEXTO_MAXIMO` (4.096 caracteres). A mensagem do orçamento cabe; acima disso, divide igual.
- **Instagram**: `TEXTO_MAXIMO_IG_BYTES` (1.000 bytes de UTF-8). Divide entre parágrafos (`\n\n`); um parágrafo maior
  que o teto divide por linha, e uma linha maior, por palavra. Nunca corta dentro de um caractere.
- **Função pura** `dividir_texto(texto, limite, medir)`, testada no verify (cenário 4: cada parte ≤ 1.000 bytes e a
  junção devolve o texto).

## R3 — A ficha no envio

- **Conversa com ficha**: usa a ficha.
- **Sem ficha, com `cliente` no pedido** (`{"id"}` ou `{"nome", "telefone"}`): liga ou cria (R4) e usa.
- **Sem ficha, WhatsApp, sem `cliente`**: procura a ficha pelo telefone com e sem o nono dígito
  (`variantes_de_telefone`, a regra da 325); achou uma, usa. Senão, cria.
  - Nome: o `client_name` do orçamento; sem ele, o nome do perfil; sem os dois, o telefone legível.
  - Origem: `conversa`.
- **Sem ficha, Instagram, sem `cliente`**: 422 `fields.cliente` "Selecione a ficha da cliente ou informe nome e
  telefone." (o IGSID não é telefone).
- **Orçamento**: `client_id` recebe a ficha **só se estiver vazio** (FR-006).

## R4 — Ligar, trocar e remover a ficha à mão

- `app/conversas/ficha_ops.py`:
  - `ligar(conversa_id, dados)`: `{"client_id"}` liga a uma ficha existente (inexistente → 422 `fields.cliente`);
    `{"nome", "telefone"}` cria pela base de clientes (`client_ops.quick_create_client`, que reaproveita a ficha do
    mesmo telefone), com origem `conversa`.
  - `remover(conversa_id)`.
- **A escolha manual fica**: coluna nova `conversas.ficha_manual`. A ligação automática da 325
  (`aviso_ops._vincular_cliente`) não age com ela ligada — nem depois de "Remover vínculo", senão a próxima mensagem
  religaria a ficha errada.
- **Reaproveitada**: a resposta diz quando a ficha "nova" já existia pelo telefone, e a tela avisa "Esta ficha já
  existia e foi ligada à conversa.".
- **Origem nova**: `quick_create_client` ganha o parâmetro `source` (padrão `manual`), e `client_metrics` ganha o
  balde `conversa` (sem ele, a ficha cairia em "Manual" sem aviso, como diz o próprio código).

## R5 — Onde fica o registro do envio

- Tabela nova `orcamento_envios`: orçamento (CASCADE), conversa (CASCADE), autor (SET NULL), `chave_envio` UNIQUE, a
  primeira mensagem de texto e a do PDF (SET NULL) e `created_at`.
- Gravada depois da ficha e antes da primeira parte, com `ON CONFLICT DO NOTHING` na chave; os ids das mensagens entram
  no fim.
- É a base do selo do histórico e da lista de envios. Na 3c, também da linha do tempo.

## R6 — As duas portas

- **Na conversa**: a lista dos recentes usa o `GET /api/orcamento/historico` que já existe (o mesmo gate, o time
  inteiro), com `date_from` de 30 dias atrás e `q`. A tela mostra até 50.
- **Na tela do orçamento**: a escolha da conversa usa o `GET /api/conversas?busca=` que já existe. O botão só aparece
  com `conversas_ligadas` do `/api/auth/me`.
- **Envio**: as duas usam o mesmo `POST /api/conversas/<id>/orcamento`.

## R7 — O formulário

- `GET /api/conversas/<id>/formularios`: os dois formulários públicos, cada um com o título, o link curto e o texto
  pronto montados no servidor (o texto fica num lugar só, pelo XV).
  - `comum` → "Pré-contrato", `{PLATFORM_BASE_URL}/f/pre-contrato`;
  - `corporativo` → "Corporativo", `{PLATFORM_BASE_URL}/f/corporativo`.
- **Texto**: "Oi, {primeiro nome}! Para reservarmos a data, preencha o formulário: {link}". O primeiro nome vem da ficha
  e, sem ela, do nome do perfil. Sem nome (só telefone ou "Contato do Instagram"), "Oi! Para reservarmos a data…".
- **A tela insere o texto no campo de mensagem**; quem envia é o "Enviar" de sempre.

## R8 — O histórico e o evento

- `_entry_summary` ganha `enviado_em` (o último envio), num SELECT agrupado só para as linhas da página.
- O detalhe ganha `cliente` (`{id, nome}` ou `null`) e `envios` (conversa, canal, nome, autor e quando).
- `_build_orcamento_prefill` (`app/calendar/routes.py`, domínio que não se refatora de passagem) ganha só a chave
  `cliente`. A tela do evento a soma às clientes como "Contratante", como faz com a do formulário (298).

## R9 — Migration e base

- `c333e1a5b7d9`, com `down_revision = "b332d5f7a9c1"` (head da 332): `orcamento_history.client_id` (FK SET NULL,
  índice), `conversas.ficha_manual` (Boolean, `server_default false`) e `orcamento_envios`. Aditiva. A ordem de merge
  fica 325 → 328 → 330 → 332 → 333.

## R10 — Verificação

- Molde do `verify_330`: a `MetaFalsa` responde ao `whatsapp_client` (`enviar`, `subir_midia`) e ao
  `instagram_client` (`enviar`, `enviar_arquivo`). O verify confere o que saiu: o corpo do texto, o PDF (começa com
  `%PDF`) e a ordem.
- Conversas semeadas pelo webhook assinado (a mensagem da cliente abre a janela), como nas features anteriores.

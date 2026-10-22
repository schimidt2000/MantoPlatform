# 316 — Revisão de português e tom em todas as superfícies

**Branch**: `316-tom-dos-textos` · **Created**: 2026-10-22 · **Status**: pronta, aguardando merge ·
**Migration**: nenhuma

## O pedido

O dono (22/10): "faça uma varredura inteira no sistema interno e todas as páginas externas também
por checagens de português. Ajuste o tom, algumas coisas parecem largadas. Exemplo: Colocar
comprovante > inserir comprovante. No interno ajuste para operacional, eficaz e claro. Deixando em
páginas externas em tom mais lúdico, mas ainda assim com muita clareza." Aprovou a amostra de
sugestões (app interno) e pediu: "Revise, altere e faça push. Com atenção para fazer sentido com o
restante da página."

## O que muda

Só texto visível. Nenhum identificador, chave de API, valor de enum, código de erro, status HTTP,
chave de `fields`, string comparada em lógica, URL ou texto jurídico (termo de consentimento) mudou.

**Guia de tom** (fonte: a conversa com o dono, consolidada em três superfícies):

- **App interno** (`frontend/apps/internal`, e-mails e alertas para a equipe, mensagens de erro da
  API): operacional, imperativo curto, confirmação é fato. Saem "pra", "dá para" (→ "é possível"),
  "pôr/colocar" (→ "inserir"), "mexer" (→ "alterar"), "alguma coisa", "nada" (→ "nenhum …"),
  "aqui" apontando para a tela (→ "nesta tela/lista" ou omitido), "Pronto."/"Tudo certo"/"Feito!",
  diminutivos, "Tente de novo" (→ "Tente novamente"), Title Case em título de cartão e botão.
- **Site público** (`frontend/apps/public`: loja, Papai Noel, avaliação da cliente, cadastro de
  talento, catálogo): lúdico e claro; a copy já estava afinada, mudanças pontuais (reticências,
  "e-mail", "este/esta" para o que está na tela, "minutinhos" → "alguns minutos").
- **Portal do artista** (`frontend/apps/portal`, e-mails ao talento): cordial e profissional.

**Glossário fechado** (vale nas três superfícies):

- Comprovante: **Inserir comprovante** / **Ver comprovante** / **Excluir comprovante**. Anexo em
  geral: botão de subir arquivo é "Inserir"; "Anexe/Anexar" sai. (No cadastro público, "Escolha a
  foto…", porque o botão do componente diz "Escolher arquivo".)
- **Situação**, não "Status", em cabeçalho de coluna, rótulo de campo e filtro ("Todas as
  situações"). Só no texto visível.
- **Excluir** = apaga o registro; **Remover** = sai de uma lista/vínculo sem apagar ("Remover da
  escala", "Remover do funil"; "Excluir observação", "Excluir o vídeo da tag").
- Inserir (valor, arquivo), Informar (motivo, dado), Selecionar (opção), Ver (link de arquivo).
- Estado vazio: "Nenhum/Nenhuma X [cadastrado|registrado|encontrado] [ainda]." com ponto.
- "e-mail", "Superadmin", "a cliente" (feminino), "Planilha de Pagamentos", "Ex.:", "…".

**Alcance** (505 trocas em 168 arquivos): app interno (pages, components, EventDetail, nfc, home,
notificações, orçamento, revisão, charts, lib), site público, portal, `app/email_service.py`
(e-mails ao talento, à cliente e à equipe), mensagens de `json_error`/`fields`/exceções de domínio
em `app/api/*` e `app/*/*_ops.py`. Dois exemplos por família na entrada do `docs/03`.

**Correções de passagem**: convite por WhatsApp sem acento ("Ola… Voce… Cache: … Horario:",
`lib/eventDetail.ts`); "1 avaliações" vira "1 avaliação" (`FeedbackSection`); e-mail interno
saudava "Olá, Olá!" quando o usuário não tem nome (`email_service.py`, agora "Olá, equipe!").

## Verificação

Não há regra de negócio: não há `verify_316.py`.

1. Cada troca foi proposta por leitura do arquivo inteiro (dez revisores em paralelo, um por área),
   revisada uma a uma, e aplicada por substituição exata com unicidade conferida (505/505). CRLF e
   UTF-8 preservados (diff sem mojibake, sem BOM; +509/−510 linhas).
2. `cd frontend && npm run typecheck` (três apps) verde. `py_compile` nos 30 `.py` tocados.
   `ruff check` nos tocados: só os 3 avisos que já existiam na `main` (`producao_ops.py` F401/E741).
3. Tela aberta no Browser pane contra o `manto_local`: Home, evento (Financeiro, Casting),
   Pagamentos e Clientes no app interno; loja e cadastro no público a 375px; login e avaliação no
   portal.

## Fora de escopo (dívidas registradas no `docs/05`)

- `producao_ops.py:875` "Só um super admin aprova…": `figurino_producao_write.py:223` decide o 403
  por `"super admin" in exc.message.lower()`; trocar o texto exige trocar a comparação junto.
- Rótulos do menu lateral e títulos de módulo em Title Case ("Banco de Talentos", "Calculadora de
  Orçamento", "Planilha de Pagamentos"): nome de seção, decisão de produto para o app todo.
- Mensagens técnicas que só aparecem com o frontend quebrado (`form_response_id inválido`,
  `Envie a lista completa em \`items\``) e mensagens com enum em texto ("Status inválido (use: …)").
- Cabeçalho do CSV de comissões (`lib/financeiro.ts`: "Status", "Qtd de Vendas") pode ser lido por
  planilha externa pelo nome da coluna — não mudou.
- "Google Calendar" × "Google Agenda" convivem nas mensagens da API.
- O e-mail do prazo de pagamento (311) é texto do dono, assinado, já enviado a 276 pessoas — intacto.
- Texto do Termo de Consentimento e do PDF de orçamento (frase do dono, espelhada no WhatsApp).

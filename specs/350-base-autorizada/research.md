# Pesquisa (Phase 0) — 350 base autorizada

Fonte externa: relatório "Máquina de vendas Manto" (17/11/2026), seções 3.6, 5.5–5.7, 8.2, 8.4; notas
`festas_social_base.md` (LGPD art. 5º XII, 8º, 14, 15–18; Guia de Legítimo Interesse da ANPD; Política do
WhatsApp Business; opt-in da Meta). Código lido na `main` `20bf93c0`.

## D1 — Prova do consentimento: histórico append-only

- **Decisão**: tabela `cliente_consentimentos`, uma linha por aceite ou retirada, com o **texto completo**
  exibido, a versão, a origem, a referência (conversa, mensagem, evento) e o autor. O estado atual fica em
  colunas da ficha (`marketing_opt_in_*`, `marketing_opt_out_*`) para as consultas baratas.
- **Porquê**: LGPD art. 8º §2º — o ônus da prova é do controlador; só a coluna da 344 perde o aceite antigo
  quando há retirada.
- **Alternativas**: só colunas na ficha (perde histórico); log genérico em `audit_logs` (não guarda o texto
  nem é consultável por ficha).

## D2 — Estado "com aceite"

- **Decisão**: com aceite ⇔ `clients.marketing_opt_in_at IS NOT NULL`. A retirada zera
  `marketing_opt_in_at/source/version` e grava `marketing_opt_out_at/source`.
- **Porquê**: um predicado só, igual ao da 344; a loja só reaplica aceite se `order.marketing_opt_in_at >
  marketing_opt_out_at`.
- **Alternativas**: comparar aceite × retirada em toda consulta (fácil de errar).

## D3 — Relógio

- **Decisão**: `now_sp()` em todo carimbo novo (consentimento, criança, pós-evento).
- **Porquê**: `marketing_opt_in_at` da 344 vem do pedido virtual, que usa `now_sp()` (`docs/00` §6 item 2).
- **Alternativas**: UTC (exigiria converter o legado).

## D4 — Criança

- **Decisão**: tabela `cliente_criancas` (ficha, primeiro nome, `nascimento` Date, aceite próprio). A linha
  só existe com o aceite; remover = apagar a linha + retirada no histórico **sem** nome nem data.
- **Porquê**: LGPD art. 14 §1º (consentimento específico e em destaque de um dos pais, por criança — irmãos
  são aceites separados) e arts. 15–16 (término = eliminação). Ano completo para a idade.
- **Alternativas**: colunas na ficha (uma criança só); dia/mês sem ano (perde a idade, que o lembrete usa).

## D5 — Saída automática

- **Decisão**: a mensagem inteira, normalizada (`strip_accents_lower`, sem pontuação/emoji nas pontas,
  espaços colapsados), contra `PALAVRAS_DE_SAIDA`; vale para texto e para botão (o "Parar promoções" do
  modelo de marketing chega como interativa). Erro 131050 no status assíncrono (`_aplicar_status`) e na
  recusa síncrona (`_registrar_falha`).
- **Porquê**: a política do WhatsApp manda respeitar o pedido de parar; frase com "sair" no meio ("vou
  sair às 15h") não pode tirar ninguém.
- **Alternativas**: "contém a palavra" (falso positivo); classificador (opaco, sem prova).

## D6 — Guarda de prospecção

- **Decisão**: `enviar_modelo` recusa (409 `sem_aceite`) modelo de categoria `MARKETING` quando a ficha da
  conversa não tem aceite ou não há ficha. Utilidade e autenticação passam. O pós-evento sai como texto
  livre na janela.
- **Porquê**: é o único caminho de mensagem de marketing que existe no sistema hoje; a categoria vem da
  Meta (`serializar_modelo` já expõe `categoria`).

## D7 — Pós-evento

- **Decisão**: mensagem montada no backend (`pos_evento_ops.mensagem`), prévia por
  `GET /api/events/<id>/pos-evento?fotos_url=`; "Copiar" copia a prévia na hora (gesto do usuário — o
  Safari exige) e registra; "Enviar pela conversa" usa `envio_ops.enviar_texto` com chave
  `pos-evento-<id>` (idempotente: o segundo clique não manda de novo). Um registro por evento
  (`UNIQUE(event_id)`).
- **Porquê**: uma fonte só para o texto (copiado e enviado iguais); a trava do envio já existe.
- **Alternativas**: montar no React (duas fontes); disparo automático (fora de escopo).

## D8 — Aceite pela cliente na página pública

- **Decisão**: o `GET /api/avaliar/<token>` ganha o bloco `consentimento` (só se o evento tem
  contratante); `POST /api/avaliar/<token>/consentimento` grava na ficha da contratante com a origem
  "Pós-evento (página de avaliação)", referência `evento:<id>` e autor nulo. A tela manda a versão do texto
  que exibiu; versão diferente da atual → 409 `texto_mudou` (o texto gravado é sempre o que a pessoa viu).
- **Porquê**: prova mais forte (a própria cliente marcou); a URL já circula.

## D9 — Indicação sem dado de terceiro

- **Decisão**: "Indicar uma amiga" abre `https://wa.me/?text=…` com o primeiro nome de quem indica e o
  WhatsApp da Manto (`WHATSAPP_LOJA`). Nenhum dado da amiga é colhido; a vendedora preenche "Indicado por"
  quando a amiga chegar. Código de indicação lido na primeira mensagem é da feature 348.
- **Porquê**: colher telefone da amiga seria tratar dado de quem não consentiu.

## D10 — Parceiro

- **Decisão**: entidade `parceiros` (tipo buffet | assessoria | agencia | outro, comissão declarada %,
  ativo). Ficha → parceiro por `clients.parceiro_id`. Sem pagamento de comissão (o BV do evento segue).
- **Porquê**: a pesquisa (5.5) recomenda comissão sempre declarada; o pagamento é do Financeiro e de outra
  feature.

## D11 — Orçamento

- **Decisão**: uma linha no fim da mensagem de WhatsApp do orçamento convida a receber novidades ("responda
  QUERO"); o registro é pela vendedora (origem "Resposta ao orçamento"). O PDF não muda.
- **Porquê**: `OrcamentoHistory` não liga à ficha (todas as linhas com `client_id` vazio), então não há
  onde gravar sozinho; a frase de deslocamento (texto assinado pelo dono) fica intacta.

## Pontos para parecer jurídico (vão ao relatório)

1. Aceite registrado pela equipe (telefone, pessoalmente, conversa) vale como prova sem a mensagem escrita?
2. A pessoa que abre o link de avaliação é tratada como a contratante — basta para o art. 14 §5º
   ("esforços razoáveis para verificar que o consentimento veio do responsável")?
3. Pós-evento (com pedido de indicação) sem aceite prévio: legítimo interesse de cliente atual?
4. "SAIR" deveria apagar também os aniversários? Prazo de guarda do dado da criança (proposta da pesquisa:
   24–36 meses sem evento nem interação).
5. Comissão de parceiro "declarada": precisa constar no orçamento/contrato da cliente?

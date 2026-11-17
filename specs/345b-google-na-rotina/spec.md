# 345b — Google Ads na rotina de segunda e diário das mudanças aprovadas no chat

**Branch**: `345b-google-na-rotina` · **Created**: 2026-11-17 · **Status**: Pronto na branch, sem push
(`verify_345b.py` 32/32; com o código da `main`, 22/30) · **Migration**: nenhuma

## O pedido

O dono, depois da análise do Google Ads de 16–17/11 e da pesquisa "Máquina de vendas Manto": "siga com a
345b". A 345 entrou em produção esperando o conector MCP `google-ads`, que não foi instalado. O acesso ao
Google ficou pela API REST, com OAuth do próprio dono (projeto Cloud `manto-marketing`, conta `4115580695`),
e as mudanças de 17/11 no Google (PMAX e Concorrentes pausados; as duas campanhas de Pesquisa limpas) foram
feitas no chat, fora do diário.

## O que muda

1. **`scripts/marketing/google_ads.py`** (novo, versionado) — cliente REST da Google Ads API, usado só na
   máquina do dono:
   - `login` (OAuth "App para computador", token em `~/.google-ads/token.json`, fora do repositório);
   - `coletar --inicio --fim --saida <pasta>`: campanhas e anúncios por dia, já no formato de
     `campaign_metrics` do `POST /run` e de `items` do `POST /anuncios`;
   - `ler`, `pausar`, `ativar` e `verba` de uma campanha: o padrão é ensaio (`validateOnly`), e só
     `--aplicar` altera de verdade.
   - A conversão do Google ("Contato por Whatsapp") é o toque no botão, não a conversa: entra em `results`,
     **nunca** em `conversations`.
2. **`POST /api/marketing-agent/<token>/run` aceita `diario`** (lista opcional): mudanças que o dono aprovou
   no chat viram entradas do diário com `origem = "rotina"`, reavaliação em 14 dias (ou `reavaliar_em`).
   - Valida tudo antes de escrever: item inválido = 400 e nada gravado.
   - Idempotente pelo `run_id` (a rodada repetida não duplica entrada).
   - Sem endpoint novo e sem migration: usa as colunas de `marketing_diario`.
3. **Skill `marketing-auditor`**: o passo do Google usa o script; as propostas aprovadas do Google também
   são executadas pelo script; mudança aprovada no chat vai no `diario` do `/run`. Sazonalidade e regras de
   parada atualizadas com a pesquisa de 17/11 (escola planeja em jun–ago e fecha fornecedor em out–dez;
   empresa pede proposta de ago a nov; não propor aumento de verba sem origem gravada).
4. **Desempenho usa o relógio de São Paulo**: `app/api/marketing_read.py` trocava de dia depois das 21h
   (`date.today()` no servidor em UTC). Passa a `hoje_sp()`, como o resto da 345.
5. **Textos desatualizados**: o estado vazio do Desempenho ainda mandava exportar CSV; o README dos scripts
   ainda falava do Railway.

## Verificação

`verify_345b.py` no espelho `manto_345` (dados `Demo345`, descartável):

1. `/run` com `diario` de 2 itens cria 2 entradas `origem = "rotina"` (conferido por conexão separada).
2. O mesmo `run_id` de novo devolve `replayed` e não duplica.
3. `diario` com item sem `motivo` → 400 com o campo; nem a rodada nem a entrada ficam gravadas. No código
   da `main` o campo é ignorado e a rodada grava: o cenário falha lá.
4. Token errado → 404 (portão).
5. `GET /api/marketing/desempenho` com o relógio de SP num domingo 22h30 (UTC já segunda): a semana corrente
   termina no domingo de SP. Falha na `main` (`date.today()` do servidor).
6. `google_ads.converter_*`: linhas reais do Google (`dia_camp.json`) viram `campaign_metrics` com `spend`
   em reais, `results` = conversões e nenhum `conversations`.

Mais `ruff check` nos arquivos tocados, `npm run typecheck` e a tela do Desempenho aberta.

## Fora de escopo

- Conversões de volta para o Google e a Meta, `gclid` e código de referência no site (feature 348 e
  seguintes).
- Painel atribuído, metas e calendário como dado (351).
- O botão do Google na avaliação continua só para nota 5 (decisão do dono, 17/11).

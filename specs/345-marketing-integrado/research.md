# Pesquisa — Feature 345

## R1. Como a rotina fala com a Meta e o Google

- **Decisão**: pelos conectores do Claude (Meta Ads MCP oficial, `mcp.facebook.com/ads`; Google Ads MCP oficial,
  `googleads/google-ads-mcp`, só leitura), dentro da tarefa agendada da máquina do dono. O ERP só recebe os números
  pela entrada de token da 256.
- **Por quê**: os dois conectores já estão autenticados na máquina do dono. Chamar a Graph API ou a Google Ads API de
  dentro do Flask exigiria guardar token de longa duração no Render e um segundo efeito externo para travar
  (Princípio XIV).
- **Rejeitado**: (a) continuar com CSV exportado à mão, que é o que parou a 256; (b) intermediário pago (Adspirer),
  com escrita nas contas e custo mensal.

## R2. Google Ads sem developer token

- **Decisão**: projeto Cloud `manto-marketing` no nível **Explorer**, já concedido em 16/11 (print do dono), com
  2.880 operações por dia em produção. É o suficiente para uma rodada semanal (dezenas de consultas GAQL).
- **Fonte**: blog do Google Ads API de 10/09/2026 e página "Access levels": o developer token acabou em 09/09/2026 e o
  acesso agora segue o projeto Cloud.
- **Falta**: o cliente OAuth "App para computador", tela de permissão **Interno**, para o refresh token não vencer a
  cada 7 dias.

## R3. Custo por venda sem atribuição

- **Decisão**: custo **misto** por frente (gasto da frente ÷ vendas da frente), rotulado como misto na tela.
- **Por quê**: em 16/11, 0 de 258 clientes de 2026 tinham origem. O custo atribuído depende do CRM (325–335) no ar e do
  `ctwa_clid`, que fica para a feature seguinte.
- **Rejeitado**: usar `utm_campaign` do Kommo (`attributed_clients` da 256), que está vazio em 100% dos clientes de
  2026.

## R4. Teto por frente

- **Decisão**: 25% da mediana da margem bruta da frente nos últimos 365 dias, editável pelo Superadmin.
- **Por quê**: a mediana resiste aos contratos gigantes do corporativo (média R$ 31,7 mil × mediana R$ 5,1 mil). 25%
  deixa 75% da margem para estrutura e lucro.

## R5. Melhores práticas que a rotina vai seguir (registro para a skill)

- **Objetivo da campanha**: otimizar para conversa (Mensagens, Click-to-WhatsApp), não para clique.
  - Os dados da própria conta mostram isso: tráfego custou R$ 35 por conversa, mensagens custaram R$ 6–8.
  - O tráfego a R$ 0,03 por clique teve CTR 194% acima do benchmark da Meta e ~0 conversa, que é sinal de clique
    acidental.
- **Posicionamento**: Audience Network fora em campanha de conversa e de tráfego, porque 35% da verba de "Leads" foi
  para lá, com 31% de CTR.
- **Formulário instantâneo** só com "maior intenção" e pergunta de filtro: 638 cadastros a R$ 8 vieram frios (V4).
- **Filtro de público classe A**: "a partir de R$ X" no criativo e geografia (bairros e cidades), porque a Meta não
  segmenta por renda no Brasil.
- **Sazonalidade**: a venda acontece ~3 semanas antes do evento (mediana). Para encher jan–jul, a verba corre de
  dez a jun. Corporativo e escolas planejam o ano em jan–fev.

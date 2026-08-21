# Contrato — pasta de entrada e arquivos CSV

## Pastas (todas em `scripts/marketing/`, gitignored)

| pasta | uso |
|-------|-----|
| `inbox/` | o dono salva os exports aqui (qualquer nome de arquivo; `.csv`) |
| `processed/<run_id>/` | para onde os arquivos vão depois de lidos (aceitos e rejeitados, com `_REJEITADO` no nome) |
| `runs/<run_id>/` | `manifest.json`, `normalizado.json`, `resultado.json`, `relatorio.html`, `resumo.md` |
| `data/marketing_store.sqlite` (`marketing_store_local.sqlite` em `--local`) | memória operacional |

## Tipos reconhecidos e conjunto mínimo de colunas

Aliases em `column_maps.json` (editável). O tipo é o primeiro cujo conjunto mínimo é satisfeito (todas as colunas obrigatórias encontradas, comparação sem acento/caixa).

| kind | obrigatórias (qualquer alias) | opcionais | granularidade |
|------|-------------------------------|-----------|---------------|
| `meta_content` | id do post (`Identificação da publicação`/`Post ID`), horário de publicação (`Horário de publicação`/`Publish time`), alcance **ou** visualizações (`Alcance`/`Reach`/`Visualizações`/`Views`) | permalink, tipo, descrição, curtidas, comentários, salvamentos, compartilhamentos, `Data` | fotografia (snapshot = coluna `Data` se houver, senão a data da rodada — e o relatório diz que a data foi assumida) |
| `meta_account` | data (`Data`/`Date`), seguidores **ou** alcance (`Seguidores`/`Followers`/`Alcance`) | visitas ao perfil | diária |
| `meta_ads` | nome da campanha (`Nome da campanha`/`Campaign name`), valor usado (`Valor usado (BRL)`/`Amount spent (BRL)`), início e fim dos relatórios (`Início dos relatórios`/`Reporting starts`, `Término dos relatórios`/`Reporting ends`) **ou** `Dia`/`Day` | impressões, alcance, cliques no link, resultados, tipo de resultado | diária se houver `Dia`; senão agregada |
| `google_ads` | campanha (`Campanha`/`Campaign`), custo (`Custo`/`Cost`), moeda (`Código da moeda`/`Currency code`) | `Dia`/`Day`, impressões (`Impr.`/`Impressions`), cliques, conversões, CPC méd. | diária se houver `Dia`; senão agregada (período lido do preâmbulo "1 de ago. de 2026 - 7 de ago. de 2026") |

## Regras de leitura (parsers.py)

1. BOM removido; delimitador por sniff (`,` `;` `\t`); codificação UTF-8 com fallback `latin-1`.
2. Google Ads: ignora linhas antes do cabeçalho (preâmbulo) e linhas cujo primeiro campo começa com `Total`.
3. Números: remove moeda/espaço; `1.234,56` → 1234.56; `1,234.56` → 1234.56; `1234` → 1234; **ambíguo** (`1.234` ou `1,234` isolados com exatamente 3 dígitos após o único separador) ⇒ linha rejeitada com motivo; se > 10 % das linhas do arquivo forem rejeitadas ⇒ arquivo inteiro rejeitado.
4. Datas: `dd/mm/yyyy`, `yyyy-mm-dd`, `dd/mm/yyyy hh:mm`, `"1 de ago. de 2026"` (meses pt-BR abreviados) e `Aug 1, 2026`.
5. Moeda: `meta_ads` assume BRL pelo rótulo `(BRL)` da coluna — rótulo com outra moeda ⇒ `currency` dela; `google_ads` lê a coluna. ≠ `BRL` ⇒ métricas gravadas, **reembolso não** (FR-018), achado.
6. Arquivo vazio/só cabeçalho ⇒ `rejected: "sem linhas"`; sem conjunto mínimo ⇒ `rejected: "colunas faltantes: X, Y"`; sha256 já visto ⇒ `skipped_duplicate` (não reprocessa, não move para rejeitado).
7. Nunca inventar: qualquer coluna opcional ausente ⇒ `null`, nunca 0.

## Saída normalizada (`runs/<id>/normalizado.json`)

Mesmo shape das listas `post_metrics`, `campaign_metrics`, `account_metrics` do `POST /run` (ver `agent-endpoints.md`), mais `files[]` com o veredito de cada arquivo.

## Instruções ao operador (vão no README e no estado vazio da tela)

- Meta Business Suite → Insights → **Conteúdo** → Exportar → CSV (últimos 90 dias) — 1×/semana.
- Meta Business Suite → Insights → **Público/Conta** → Exportar → CSV — 1×/semana.
- Gerenciador de Anúncios → Relatórios → **Detalhamento: Dia** → Exportar CSV — 1×/semana.
- Google Ads → Campanhas → Segmento **Dia** → Baixar → CSV — ou agendar envio semanal por e-mail e salvar o anexo na pasta.
- Salvar tudo em `scripts/marketing/inbox/` até domingo à noite; a rotina roda segunda 06:30.

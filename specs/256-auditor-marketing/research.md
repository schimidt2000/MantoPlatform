# Research — Feature 256 (auditor de marketing)

Fase 0 do plano. Cada item: **Decisão → Justificativa → Alternativas**. Nenhum `NEEDS CLARIFICATION` restou na spec (clarificações de 2026-08-20).

## R1. Como a rotina fala com o ERP

- **Decisão**: só HTTP, por três endpoints exclusivos do agente (`GET .../context`, `POST .../run`, `POST .../report`) gated por `MARKETING_AGENT_TOKEN` no molde de `app/api/audit_agent.py` (404 para token errado/ausente; sem env, nada funciona).
- **Justificativa**: a única escrita permitida (Gasto Extra + histórico) precisa passar por `gastos_ops.create_expense()` e pela idempotência no servidor; e o contexto (metas via `goal_health()`, CAC via `client_metrics()`) já existe como lógica Python no app — duplicar nos scripts violaria o Princípio I. Bônus: nenhum arquivo de URL de banco é lido pelos scripts de marketing (o auditor 221 lê produção por psycopg porque precisa de varredura ampla; aqui o contexto é estreito).
- **Alternativas**: psycopg read-only + escrita direta (rejeitado: escrita fora da regra de negócio; segredos de banco no agente); reaproveitar o token `AUDIT_AGENT_TOKEN` (rejeitado: escopos diferentes — um token de leitura de comprovantes não deve poder criar gasto).

## R2. Período do reembolso automático

- **Decisão**: **mês civil** por plataforma. Primeira rodada que vê gasto no mês cria o Gasto Extra pendente (competência = último dia do mês, descrição "Anúncios Meta Ads — agosto/2026 (auditor de marketing)", reembolso ao titular, nota "reembolso previsto dia 10/09"); rodadas seguintes atualizam valor e linhas por campanha **enquanto pendente**; aprovado/rejeitado congela; divergência posterior vira achado.
- **Justificativa**: é a unidade da fatura do cartão e do vencimento dia 10 (decisão do dono); semanal geraria 4–5 reembolsos miúdos por plataforma e a conta não fecharia com a fatura. Idempotência natural: chave (plataforma, ano-mês).
- **Alternativas**: por rodada/semana (rejeitado: fragmenta); por campanha (rejeitado: dezenas de gastos; o detalhe por campanha vai em linhas filhas).
- **Verificar na implementação**: `SpecialExpense` não tem data de vencimento — o "dia 10" entra na nota/descrição e no relatório; se a Planilha de Pagamentos tiver conceito de data prevista para reembolso, usar (tarefa de pesquisa rápida em `app/financeiro/*` durante tasks).

## R3. Gráficos no e-mail

- **Decisão**: barras em HTML/CSS (tabelas com `<td>` de largura proporcional, cores do tema do e-mail existente) para série semanal, gasto por campanha e funil. SVG só na tela do ERP.
- **Justificativa**: Gmail (web e app) remove `<svg>` inline e bloqueia `<style>` parcialmente; imagens exigiriam anexos CID + renderizador (matplotlib não está no `requirements.txt`). Barras CSS renderizam em Gmail, Outlook e Apple Mail.
- **Alternativas**: PNG via matplotlib anexado (rejeitado: dependência nova + peso); SVG inline (rejeitado: invisível no Gmail).

## R4. Gráficos na tela

- **Decisão**: três componentes SVG próprios em `components/charts/` (`LineSeriesChart`, `BarListChart`, `FunnelChart`), dimensionados por `viewBox` + atributos SVG (sem `style={{}}`), cores pelos tokens do tema (`fill="currentColor"` + classes `text-accent`, `text-gold`, `text-green`), tooltips por `<title>` + legenda textual abaixo (acessibilidade sem depender só de hover).
- **Justificativa**: o projeto não tem lib de gráfico (grep confirma: zero `<svg`/`recharts` nas páginas; barras do Financeiro são `div`s Tailwind). Três gráficos simples não justificam dependência. A skill `dataviz` será carregada na implementação para paleta/forma.
- **Alternativas**: Recharts (rejeitado: dependência nova, tema duplicado); `div`s Tailwind (ok para barras, ruim para série temporal).

## R5. Formatos dos exports (estado atual, pt-BR)

- **Meta Business Suite → Insights → Conteúdo → Exportar (CSV)**: uma linha por post com totais acumulados até a data do export. Colunas típicas: `Identificação da publicação`, `Nome da conta`, `Descrição`, `Horário de publicação`, `Link permanente`, `Tipo de publicação`, `Visualizações`/`Alcance`, `Curtidas`, `Compartilhamentos`, `Comentários`, `Salvamentos`. → **fotografia** (`snapshot_date` = data do export ou coluna `Data`).
- **Meta Business Suite → Insights → Conta/Público → Exportar**: linhas diárias (`Data`, `Seguidores`, `Alcance`, `Visitas ao perfil`).
- **Gerenciador de Anúncios (Meta Ads) → Relatórios → Exportar CSV**: `Nome da campanha`, `Início dos relatórios`, `Término dos relatórios`, `Valor usado (BRL)`, `Impressões`, `Alcance`, `Cliques no link`, `Resultados`, `Tipo de resultado`, `Custo por resultados`. Com "Detalhamento → Dia" vira uma linha por dia.
- **Google Ads → Campanhas → Baixar CSV**: 2 linhas de preâmbulo (título do relatório; intervalo "1 de ago. de 2026 - 7 de ago. de 2026"), cabeçalho `Campanha`, `Status da campanha`, `Código da moeda`, `Custo`, `Impr.`, `Cliques`, `CTR`, `CPC méd.`, `Conversões`, `Custo/conv.`; linhas de rodapé `Total: …`. Com segmento "Dia" ganha coluna `Dia`.
- **Decisão**: reconhecimento por **assinatura de colunas** (conjunto mínimo obrigatório por tipo) com aliases em `column_maps.json` (pt-BR e en-US desde o início); sniff de delimitador (`,`/`;`/tab) e BOM; descarte de preâmbulo e rodapé "Total"; números aceitam `1.234,56` e `1,234.56` (decide pela posição do último separador; se só houver um separador e ele for `.` com exatamente 3 dígitos depois, rejeita como ambíguo); datas `dd/mm/yyyy`, `yyyy-mm-dd` e "1 de ago. de 2026". Arquivo sem o conjunto mínimo → `rejeitado` com motivo nomeando as colunas que faltaram.
- **Risco aceito**: os nomes acima são os vigentes em 08/2026; mudança de rótulo é absorvida editando o JSON (FR-002), sem código.

## R6. Sobreposição diário × agregado (campanhas)

- **Decisão**: linhas de campanha guardam `period_start`/`period_end`; para gasto mensal, somam-se só as linhas **diárias** quando existirem para as mesmas datas; linhas agregadas que cruzam datas já cobertas por diárias são ignoradas no cálculo e geram achado `periodo_sobreposto` (nível atenção). O quickstart instrui exportar com detalhamento por dia.
- **Alternativas**: rejeitar agregados (rejeitado: o primeiro export do dono provavelmente será agregado); ratear agregado por dia (rejeitado: inventa número).

## R7. Vínculo post ↔ card

- **Decisão**: 1) `permalink` normalizado (remove querystring/`utm`, barra final, `www.`) igual → vínculo `permalink`; 2) senão, se houver exatamente um card `publicado` com `platform` igual e `publish_date` = data de publicação do post → vínculo `data`; 3) senão `nenhum` + achado `post_nao_vinculado` listando candidatos. O vínculo fica gravado na métrica (`marketing_post_id`, `link_method`) e pode ser refeito quando o link for preenchido depois (rodada seguinte revincula métricas sem vínculo).
- **Dialog**: ao mudar o status para `publicado` sem link, o campo ganha destaque e texto "Cole o link do post para o relatório semanal reconhecer esta publicação" — não bloqueia (FR-010).

## R8. Atribuição campanha → lead → evento

- **Decisão**: importador do Kommo passa a ler `Origem do Lead`, `utm_source`, `utm_medium`, `utm_campaign` (colunas confirmadas no export real `kommo_export_leads_2026-06-29.csv`) com a mesma regra "mais recente sobrescreve" de `_apply_metadata`. Atribuição no contexto: `Client.utm_campaign` (normalizado: minúsculas, sem acento, `_`/`-` → espaço) × `campaign_name` normalizado; leads = clientes com `kommo_created_at` na janela; eventos fechados = clientes com evento (`EventClient`) cujo evento tem `start_at` ≥ data do lead. CAC do mês = soma do gasto do mês ÷ `client_metrics().new_by_month[mês].total` (zero → "sem clientes novos no mês").
- **Alternativas**: casar por `utm_source` só (rejeitado: não separa campanhas).

## R9. Agendamento e catch-up

- **Decisão**: scheduled task `auditoria-marketing-semanal` (cron `30 6 * * 1`, jitter como a financeira), prompt curto apontando para `.claude/skills/marketing-auditor/SKILL.md`; o runtime já faz catch-up na próxima abertura (comportamento observado na tarefa 221).
- **Ordem**: 06:30 para não disputar com a financeira (06:02).

## R10. Memória local (SQLite) × histórico no ERP

- **Decisão**: SQLite local guarda só o operacional (rodadas, hashes de arquivo, última janela, modo local/prod separados como no 221); o histórico analítico vive no Postgres do ERP (fonte da tela e do relatório comparativo). A resposta do `POST /run` é gravada em `runs/<id>/resultado.json` para o relatório.
- **Justificativa**: evita dois históricos divergentes; o ERP é a verdade.

## R11. Serializer do Gasto Extra

- **Decisão**: `serialize_expense` (em `gastos_ops`/API) ganha `marketing_batch: {platform, month, reported_total, lines:[{campaign_name, amount}], run_id, files:[...]}` ou `null`; a tela de Gastos Extras mostra um bloco "Gerado pelo auditor de marketing" com as linhas (tarefa de UI pequena, reaproveitando `DenseCard`).

## R12. Verificação (Test-First)

- **Decisão**: `verify_256.py` cobre (na ordem do quickstart): migration aplicada; parsers com as 4 fixtures + 2 inválidas; `POST /run` sem env → 404, token errado → 404; ingestão idempotente (mesmo payload 2×); reembolso mensal (cria → atualiza pendente → congela aprovado → achado de divergência); vínculo por permalink/data/nenhum; importador Kommo com utms; `GET /marketing/desempenho` RBAC (MARKETING ok, CASTING 403); `PATCH` permalink inválido → 400 com campo. Limpeza total no `finally` (usuário descartável com `roles.clear()`; registros por prefixo `__v256_`).

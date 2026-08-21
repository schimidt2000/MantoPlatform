# Auditor de marketing semanal (feature 256)

Rotina que roda toda **segunda-feira às 06:30** na máquina do dono (Claude Code, assinatura —
zero API), no molde do auditor financeiro (`scripts/auditor/`, feature 221). Ela lê os exports
da Meta e do Google Ads salvos na pasta de entrada, grava o histórico no ERP, mantém o
**reembolso do gasto de anúncios** (um Gasto Extra de Marketing por plataforma e mês, pendente,
com o detalhe por campanha) e manda o relatório por e-mail.

## O que ela escreve no ERP — e só isso

1. Histórico de métricas (posts, campanhas, conta) e registro das rodadas/arquivos.
2. **Gasto Extra de categoria Marketing**, desembolso *reembolso* ao titular do cartão,
   status *pendente*, sem comprovante (a fatura do cartão é anexada depois pelo financeiro).
   Um por plataforma e mês civil; atualizado enquanto pendente; congelado ao ser aprovado.

Tudo passa por `/api/marketing-agent/<token>/…` com o token de `.marketing-agent-token`
(raiz do repositório, gitignored). Os scripts **não** leem banco nenhum.

## Pastas (criadas em runtime por `config.ensure_dirs()`, todas gitignored)

| pasta | uso |
|-------|-----|
| `inbox/` | salve aqui os CSVs exportados (qualquer nome) |
| `processed/<run_id>/` | para onde os arquivos vão depois de lidos (`_REJEITADO` no nome quando for o caso) |
| `runs/<run_id>/` | `manifest.json`, `normalizado.json`, `contexto.json`, `resultado.json`, `findings.json`, `relatorio.html`, `resumo.md` |
| `data/` | memória local (SQLite): rodadas, hashes de arquivo, achados já reportados |

## Como exportar (≈ 10 min por semana)

- **Meta Business Suite → Insights → Conteúdo → Exportar → CSV** (últimos 90 dias).
- **Meta Business Suite → Insights → Público/Conta → Exportar → CSV**.
- **Gerenciador de Anúncios → Relatórios → Detalhamento: Dia → Exportar CSV**.
- **Google Ads → Campanhas → Segmento: Dia → Baixar → CSV** (ou agendar o envio semanal por
  e-mail e salvar o anexo na pasta).

Salve tudo em `inbox/` até domingo à noite. Formatos e colunas reconhecidas:
`specs/256-auditor-marketing/contracts/csv-inbox.md` e `column_maps.json` (editável — novo
rótulo de coluna entra ali, sem código).

## Rodada (a skill `.claude/skills/marketing-auditor` faz isso sozinha)

```powershell
cd scripts\marketing
..\..\.venv\Scripts\python.exe collect.py            # lê a inbox → runs/<id>/  (imprime run_id)
..\..\.venv\Scripts\python.exe publish.py --run <id> # contexto + ingestão no ERP
..\..\.venv\Scripts\python.exe checks.py  --run <id> # achados (com supressão de repetidos)
..\..\.venv\Scripts\python.exe report.py  --run <id> --send
```

`--local` em todos eles usa o Flask local (`http://localhost:5000`) contra o `manto_local`; o
servidor recusa `mode=local` fora de `FLASK_ENV=development`, então uma rodada de teste nunca
cria gasto em produção. A memória local de teste e a de produção são arquivos separados.

## Segredos

`.marketing-agent-token` (raiz) = env `MARKETING_AGENT_TOKEN` no Railway. Sem o env em produção
os endpoints respondem 404 e a rotina não funciona — é o interruptor geral. Nunca copie o token
para relatório, `resumo.md` ou chat.

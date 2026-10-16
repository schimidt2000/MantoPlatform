# Quickstart de verificação — feature 307

## Pré-requisitos

- `manto_local` restaurado (espelho da produção) e `.local-db-url` presente.
- Venv do projeto (`.venv`) ativo; frontend com dependências instaladas.

## 1. Verify (PowerShell, na raiz do repo)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe specs\307-natal-papai-noel-calculadora\verify_307.py --regressao
```

Esperado antes do núcleo: 1–9, 11–13, 15 e 16 vermelhos; 10 e 14 verdes por desenho (paridade e gate
já existentes). Esperado ao fim, **com `--regressao`**: `18/18`; sem a flag o 17 sai PULADO e a
contagem é `17/17 · 1 pulado`. O verify salva a configuração de preços real, aplica a de teste
(markup 2,6; coordenador 250; Papai Noel no cachê ANTIGO `[600, 650, 675, 700]`, sem "Ajudante do
Noel" e sem `datas_especiais` — a migração entrega 712/423/faixa) e **restaura no `finally`** —
conferir pelo cenário 18 e por `git status` limpo.

Números-chave (coluna 1h, 1 coordenador, SP, sem NF):

| Cenário | Esperado |
|---|---|
| 20/12, Papai Noel | 2.501,20 |
| 20/12, Noel + Ajudante do Noel | 3.601,00 |
| 24/12, Papai Noel | 5.010,00 (20h: 5.110,00) |
| 25/12, Noel + Ajudante | 7.181,00 |
| 24/12, Noel + boneco (200) | 7.181,00 (piso 650) |
| 24/12, 2h | 10.020,00 |
| 24/12 + BV 10 % | `snapshot.acrescimos[0].valores_brl[0] == 501.00` |
| Teto 24/12 | Noel 1.000 / Ajudante 650 / Coord 500 (+50 se ≥ 19h) |

Regressão: `.\.venv\Scripts\python.exe specs\305-bv-do-orcamento-no-evento\verify_305.py --regressao`
(305 verde; 273 na linha de base 8/15).

## 2. Typecheck e lint

```powershell
cd frontend; npm run typecheck; cd ..
.\.venv\Scripts\ruff.exe check app\orcamento\settings.py app\orcamento\pricing.py app\orcamento\quote_ops.py app\orcamento\pdf.py app\calendar\routes.py app\calendar\orcamento_evento_ops.py app\educamanto\quote_ops.py app\api\orcamento_write.py
```

## 3. Telas (Browser pane, `manto-conferir-tela`)

Backend `manto-backend-sem-google` + Vite `internal` (launch.json). Logar como superadmin descartável.

1. `/orcamento`: adicionar especial "Papai Noel"; data vazia → dica "Em 24/12 e 25/12 a tabela
   especial entra pela data"; data 2026-12-24 → aviso dourado "🎄 Data especial — Véspera e Natal:
   markup 3,34× e cachês próprios…" (conferir "3,34×" por JS) e total 1h R$ 5.010,00 / 2h
   R$ 10.020,00; trocar para 2026-12-20 → o aviso some, R$ 2.501,20; durante o recálculo o botão
   diz "Recalculando…" e fica desabilitado.
2. "Gerar Orçamento" em 24/12 → `/orcamento/:id` com "🎄 Valores da data especial: Véspera e Natal"
   e a nota na mensagem; "Baixar PDF" abre com a nota em itálico.
3. `/orcamento/configuracoes`: card "Datas especiais — Véspera e Natal" com dias (chips), markup,
   coordenador, piso, cachês sobrescritos (chips) e nota; markup 33,40 e salvar → 400 com o erro no
   card e o foco no campo; markup 3,50 e salvar → sucesso; recalcular em 24/12 → R$ 5.250,00;
   voltar para 3,34.

## 4. Pós-deploy (produção, só leitura)

Sonda `/api/` com JSON; abrir `/orcamento/configuracoes` e conferir Papai Noel 712 / Ajudante do
Noel 423 / bloco de Natal; orçar um Noel em 20/12 e um em 24/12. Avisar a equipe: parar de somar o
"Outro" nos orçamentos de Noel e usar o item "Ajudante do Noel".

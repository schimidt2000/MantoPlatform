# Quickstart — validar a Feature 306

**Spec**: [spec.md](./spec.md) · **Plano**: [plan.md](./plan.md) · **Modelo**: [data-model.md](./data-model.md)
· **Contratos**: [contracts/api.md](./contracts/api.md)

Roteiro de validação: como rodar e o que esperar. O que construir está no `tasks.md`.

## Pré-requisitos

- `manto_local` atualizado:
  `C:\Users\schim\Desktop\Manto_Platform\scripts\db\refresh-local-db.ps1`. O script restaura o dump das
  02:00; com `-Fresh`, baixa um novo da produção. O refresh volta o banco a `a7c3e91f4d28`, então rode o §4
  depois de cada um.
- Nada deste roteiro escreve na produção, fora o evento descartável do §9. As outras idas a ela são
  leituras por SSH (§2, §7 e §9).
- O backend local fica **parado** enquanto o verify e os verifies antigos rodam. A guarda herdada do
  `verify_303` sai com código 2 se `calendar_auto_sync_at` for recente.
- Do worktree (`C:\tmp\mp306`), estes ficam só no repositório principal
  (`C:\Users\schim\Desktop\Manto_Platform`): o `.venv`, `scripts\db\` e `.marketing-agent-token`. O
  worktree tem cópia do `.local-db-url` (se faltar, leia a do principal) e nasce sem `node_modules` (§6).
- Todo comando Python roda na raiz do worktree:

```powershell
cd C:\tmp\mp306
$py = 'C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe'   # o worktree não tem .venv
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'
$env:PYTHONPATH = (Get-Location).Path              # o `app` importado é o da branch, nunca o do principal
[Console]::OutputEncoding = [Text.Encoding]::UTF8  # acento intacto no que se grava com Out-File
```

Do repositório principal, com a branch em checkout, `$py` vira `.venv\Scripts\python.exe` e o resto fica
igual.

## 1. Verify (Princípio VIII)

```powershell
& $py specs\306-dinheiro-do-cancelamento\verify_306.py                # o portão: os 59 e as variantes
& $py specs\306-dinheiro-do-cancelamento\verify_306.py --so=2,2b,8    # iteração; a limpeza (27) roda sempre
& $py specs\306-dinheiro-do-cancelamento\verify_306.py --nucleo       # Fundação e História 1, sem as rotas
& $py specs\306-dinheiro-do-cancelamento\verify_306.py --regressao    # mais os verifies antigos (§5)
```

**Esperado**
- **Total**: a rodada termina em `59/59 OK` (os 57 da spec, mais 37b e 38c). As variantes rodam dentro
  do seu cenário e não mudam a contagem. A saída é 1 quando algo falha e 2 pela guarda de ambiente.
- **"Deve falhar?"**:
  - 20 são "sim": 3, 4, 5, 6, 15, 16, 16b, 16c, 16d, 18, 19, 28, 29, 33, 34, 38, 40, 42d, 45b e 45c. Verde
    = a recusa aconteceu, com o código certo e nada gravado;
  - 38 são "não";
  - o 27 (limpeza) é "—".
- **Chão**:
  - e-mail travado e espião de `send_removal_email`: zero envio, conferido depois de `_esperar_threads`;
  - dublê de `app.calendar.service.delete_event` em todo cancelamento (show e ensaios), que conta as
    chamadas. O 27 afirma que nada escapou dele;
  - escrita sempre conferida por conexão separada; login só por `POST /api/auth/login`; requisições fora do
    `app_context`.
- **Descartáveis**: têm prefixo `__v306_` e são apagados no `finally`, na ordem da spec. São eles:
  - usuários SUPERADMIN, COMERCIAL, FINANCEIRO, CASTING, FIGURINO, ENSAIO, MARKETING e ARTISTA_3D;
  - um vendedor;
  - um talento com e-mail de teste, numa vaga que o sistema criou (`talent_id IS NULL`). Nunca uma
    `EventRole` inventada.

  O aquecimento da Planilha (M−1 a M+2) cria salários e recorrentes que ficam no espelho, e a saída diz
  quais.
- **Harness `main` × branch**: usado nos cenários 1, 14b, 17, 20, 23 e 41 e na regressão das cobranças da
  Home sem devolução.
  - Faz `git archive` de `git merge-base HEAD main` numa pasta do `%TEMP%` e roda os dois lados em
    subprocesso, no mesmo banco.
  - A comparação é exata: Decimal a 0,01, percentual a 0,1.
  - Precisa da `main` local e do `git` no PATH.
- **Variantes**, cada uma dentro do seu cenário:
  - **2/8 prévia = execução**: com `hoje` no dia 2 e no dia 10, GET `…/impacto-exclusao?devolucao=` antes
    e POST depois. `retido`, `comissao_retido`, `ajuste`, `ciclo`, `repasse_em` e `bv_retido` têm de ser
    iguais ao gravado. O retrato pela conexão separada acusa um GET que escreva;
  - 9/10-desfazer;
  - 16/17-`paid_amount`;
  - 16b cheia 0 (cortesia com valor e evento sem vendedor);
  - 38-comprovante;
  - 39 devolução do dia depois do principal cancelado;
  - 44 dois sinos.
- **Mutações**: rodam dentro do cenário, no molde de `_deve_quebrar` do `verify_305`. Com a regra errada
  ligada, o cenário tem de quebrar.
  - 14b e 20, contra a `main` (no 20, a `main` dá −600);
  - 16c: um beneficiário só; nota sem prefixo;
  - 16d e 42: apagar e recriar;
  - 16e: taxa de hoje;
  - 42c: data antiga;
  - 45c: lista lida da escala de hoje; remoção sem a condição;
  - 2/8: "simular escreve".

**Primeira rodada, antes do núcleo.** Roda com o verify, o `retrato_main_branch.py` e o `contagem_pre_deploy.py`
escritos e nenhuma linha de núcleo:

```powershell
& $py specs\306-dinheiro-do-cancelamento\verify_306.py --regressao |
  Out-File -Encoding utf8 specs\306-dinheiro-do-cancelamento\verify_306_primeira_falha.txt
```

- **Podem estar verdes, sem defeito**:
  - o 1, o 23 e o 26, que comparam a branch ainda igual à `main` ou só leem;
  - o 27;
  - dentro do 6 e do 28, as afirmações que já valem hoje: 403 do COMERCIAL no cancelar e 401 sem sessão
    nas rotas que existem.
- **O 5 não**: o HEAD responde 400 ao "já cancelado" (`agenda_write.py:609-610`), e o cenário espera 409
  `ja_cancelado`.
- Qualquer outro verde é defeito do verify.
- As últimas linhas do `--regressao` são a base dos verifies antigos (§5).

**`--nucleo`.** Serve para a Fundação e a História 1 fecharem antes de a API existir.
- Neste modo, semeiam `event_cancellations` por ORM e chamam a reconciliação e `bv_da_planilha` direto,
  sem as rotas:
  - os cenários 7–11, 12, 17 e 30;
  - as variantes 9/10-desfazer e 16/17-`paid_amount`;
  - no 8, a comparação `reconciliar(simular=True)` × `simular=False`.
- O 16b se reduz à variante 16b cheia 0, chamando `comissao_cheia_do_evento` direto.
- Os outros cenários rodam como sempre.
- Da História 2 em diante, esses cenários fecham pela API. O portão é sempre a rodada sem argumentos.

**Por fase** (blocos do verify). Ao fechar cada fase, rode a rodada inteira:
- os cenários da fase e das anteriores ficam verdes;
- os das fases seguintes ficam vermelhos, pelos motivos da tabela;
- verde fora de hora é defeito.

| Bloco | Fase | Verde ao fim da fase |
|---|---|---|
| B0 | Fundação | 1, 23, 26 e 27; a parte de regressão do 41 (comissões dos grupos e cobranças da Home sem devolução), verde desde aqui; com `--nucleo`, a variante 16b cheia 0 |
| B1 | História 1 | 13, 14 e 14b. Com `--nucleo`: 7–11, 12 (sem a DRE), 17 e 30; as variantes 9/10-desfazer e 16/17-`paid_amount`; e, no 8, `simular=True` × `simular=False`. O `verify_305` tem de estar verde (§5) |
| B2 | História 2 | Pela API: 2 e 8, com a variante 2/8 prévia = execução; 2b (sem o aviso), 3, 4 (sem o corte e a multa), 5, 6, 7 e 9–11; 12 e 32 sem a DRE; 15, 16, 17 (sem o satélite), 18, 19, 25, 28, 30, 31, 34 e 36. As variantes 9/10-desfazer e 16/17-`paid_amount` pela API. As partes "COMERCIAL/FINANCEIRO → 409" do 16b, do 16c(v) e do 16d |
| B3 | História 3 | 20, 22 e 24; a parte da DRE do 12 e do 32; o 21 menos o satélite (a parte virtual fecha aqui; a multa é semeada por ORM, com `SpecialExpense.CATEGORY_MULTA_CANCELAMENTO`). O 23 segue verde |
| B4 | História 4 | 16b (sem o satélite, e com a variante 16b cheia 0 pela API), 16c, 16d e 16e. O `verify_305` tem de estar verde antes (§5) |
| B5 | História 5 | 29, 35, 37, 37b, 38 (+ 38-comprovante), 38c, 39 (+ a variante 39 devolução do dia depois do principal cancelado) e 41. 42 (sem aviso e ensaio), 42b (sem a multa), 42c e 42d (sem o cachê pago). A parte de satélite do 4, do 16b, do 17 e do 21. Do 40, desagrupar e agrupar |
| B6 | História 6 | 33, 40, 42e, 43, 44 (+ 44 dois sinos), 45, 45b e 45c; o que faltava do 2b, do 4, do 42, do 42b e do 42d. A rodada chega a `59/59 OK` |
| B9 | limpeza | 27 (roda sempre) |

Os dois cenários novos:
- **37b**: um comprovante de 200 num satélite refaz o retido e a comissão do principal cancelado.
- **38c**: corte com a base paga, desfazer o pago e sincronizar dá Σ = 75.

## 2. Contagem (`contagem_pre_deploy.py`)

O script só lê:
- não chama `create_app()` nem importa `app`;
- abre a transação com `default_transaction_read_only=on`;
- usa `psycopg` ou `psycopg2` (a produção só tem o `psycopg2`);
- lê o `DATABASE_URL` e tira o `+psycopg` do esquema.

A saída traz quantidades, R$ e ids, nunca nome, e-mail ou PIX, porque vai versionada para a pasta da
feature.

**Espelho**: no Setup, em `contagem_2026-10-15.txt`; no Polimento, de novo, com a data do dia.

```powershell
& $py specs\306-dinheiro-do-cancelamento\contagem_pre_deploy.py |
  Out-File -Encoding utf8 specs\306-dinheiro-do-cancelamento\contagem_2026-10-15.txt
```

Referência: Contexto técnico do plano, com o espelho de 15/10 e o dump de 30/09.

| Grupo | Números |
|---|---|
| Eventos | 0 cancelados; 0 marcados; 7 grupos; 14 ensaios futuros ligados (8 a satélite); 0 cachê pago em evento futuro |
| Comissões | 0 `no_banco`; 0 linhas vivas de evento cancelado; 72 linhas que o resync alcança; 142 pagas (25 de evento futuro); 2 com `original_id` |
| Gastos | 84 aprovados com evento |
| Usuários ativos | CASTING 2; ENSAIO 2; SUPERADMIN 3 |
| Banco | `alembic_version` = `a7c3e91f4d28` |

Num espelho mais novo, número diferente não é defeito: é o dado do dia. O cenário 26 roda o mesmo script e
prova que ele não escreve.

**Produção**: no dia do deploy, antes do push (§9). O SSH do Render não repassa stdin, então o script vai
no próprio comando. Ele vai comprimido (gzip + base64) para caber na linha de comando do Windows (cerca de
32 mil caracteres). No container, roda pelo `.venv`, com o `DATABASE_URL` do serviço:

```powershell
$bytes = [IO.File]::ReadAllBytes((Resolve-Path specs\306-dinheiro-do-cancelamento\contagem_pre_deploy.py))
$ms = New-Object IO.MemoryStream
$gz = New-Object IO.Compression.GZipStream($ms, [IO.Compression.CompressionMode]::Compress)
$gz.Write($bytes, 0, $bytes.Length); $gz.Close()
$b64 = [Convert]::ToBase64String($ms.ToArray()); $b64.Length   # bem abaixo de 32 mil
ssh -i $HOME\.ssh\render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com `
  "cd /opt/render/project/src && echo $b64 | base64 -d | gunzip > /tmp/contagem_306.py && .venv/bin/python /tmp/contagem_306.py; rm -f /tmp/contagem_306.py" |
  Out-File -Encoding utf8 specs\306-dinheiro-do-cancelamento\contagem_AAAA-MM-DD_producao.txt
```

A data do nome é a de Brasília, tirada de `Get-Date` no PowerShell; o `date` do Git Bash pode devolver UTC.
Nas duas rodadas, a saída conta:
- cancelados, inclusive os sem venda nem comprovante;
- comissões `a_pagar` negativas com evento, `no_banco` por mês, ciclos abertos de soma zero com linha de
  valor (o grupo aberto da 267c), linhas vivas de evento cancelado e órfãos `a_pagar`;
- devoluções com tipo nulo, pendentes ligadas e ligadas a evento vivo; gasto aprovado com categoria fora de
  `CATEGORIES`;
- BV em satélite, BV não pago de `legado` e BV não pago sem recebedor ou PIX;
- marcados pela 303;
- comprovantes sem valor e pago maior que a venda;
- grupos com dia futuro, com o principal fora do 1º dia ou cruzando o mês, e satélites com comissão própria;
- eventos futuros com cachê pago; shows futuros com ensaio e os escalados deles; escalados sem e-mail e
  talentos sem PIX;
- usuários ativos FINANCEIRO e ENSAIO.

## 3. Telas `main` × branch (`retrato_main_branch.py`)

```powershell
& $py specs\306-dinheiro-do-cancelamento\retrato_main_branch.py
```

**Esperado**: em todos os meses do espelho sem cancelamento, saem idênticos ao centavo entre `main` e
branch (SC-002, cenário 23):
- a DRE (API e Jinja), a Tendência e os painéis da DRE (`GET /api/financeiro/dashboard`);
- o Dashboard Comercial (`GET /api/vendas/pipeline`) e o `/admin/desempenho`;
- a ficha de toda cliente com evento (`GET /api/clientes/<id>`), a lista e as métricas (`GET /api/clientes/`,
  `GET /api/clientes/metricas`);
- a Performance e as cobranças da Home (`GET /api/dashboard`);
- Comissões (`GET /api/financeiro/comissoes`: KPIs, `by_seller`, `month_status`) e os itens de comissão e de
  BV da Planilha (`GET /api/financeiro/pagamentos`). Os dois gravam no GET (resync): a `main` aquece os meses
  antes, e a rodada da branch não pode escrever linha nenhuma (o cenário 26 confere pelo retrato de linhas).

Ficam fora, listados à parte porque mudam de propósito: o ticket médio do Jinja (FR-043), o `sale_count`, o
item aberto de comissão de soma zero com linha de valor (R6) e, para cada cancelado `legado` (hoje nenhum no
espelho), três meses: o do `cancelled_at`, onde o retido entra; o do `expense_date` de cada devolução ligada a
ele, que sai dos gastos (FR-042); e, só na Tendência, o mês do evento, que deixa de contar a venda e o cachê
(FR-043). No resto da DRE o mês do evento continua comparado, porque ela já exclui o cancelado.
- Mês com cancelado `legado` (hoje não há nenhum) sai da comparação e é listado à parte, porque ali a
  diferença é a esperada.
- Em divergência, a saída é 1 e mostra o mês e a linha.

**Como compara**
- Os dois lados vêm do harness do §1 (`git archive` da base).
- O relógio é fixo: troca `datetime` em `app.financeiro.routes`, em `app.api.financeiro_read` e, na branch,
  em `app.financeiro.dre_ops`.
- `ensure_recurring_entries` fica neutralizado, porque o GET da DRE grava.
- O Jinja é lido por `template_rendered` de `GET /financeiro/?period=custom…`.
- O ticket médio do Jinja fica fora da comparação: ele muda de propósito (FR-043).
- O script não importa nada que só exista na branch.
- Roda sem cancelado do verify no banco, ou seja, depois da limpeza. O cenário 23 o chama antes de qualquer
  cancelamento.

## 4. Migration

```powershell
& $py -m flask db heads                                               # uma cabeça só: a da 306
& $py -m flask db upgrade; & $py seed.py
& $py -m flask db downgrade a7c3e91f4d28; & $py -m flask db upgrade   # ida e volta
```

**Esperado**
- A migration tem `down_revision = "a7c3e91f4d28"`.
- `event_cancellations`, `event_cancellation_bvs` e `event_cancellation_elenco` são criadas vazias, e
  nenhuma tabela existente ganha coluna.
- O `downgrade` derruba elenco → bvs → cancelamentos.
- `create_app()` sobe com os mappers configurados. Um `AmbiguousForeignKeysError` aparece aqui, e não no
  `startCommand`.
- A ida e volta roda com as três tabelas vazias, depois da limpeza do verify. Este é o lugar único do roteiro
  (o data-model §10 e o plan apontam para cá; o §7 o repete no venv 3.11). Banco descartável do dump não é
  preciso: a migration só cria tabelas.

## 5. Verifies antigos (regressão)

O `--regressao` (§1) roda todos em subprocesso, um por vez, e falha se algum terminar pior que a base
gravada na primeira rodada. Para rodar um a um:

```powershell
$env:MARKETING_AGENT_TOKEN = (Get-Content C:\Users\schim\Desktop\Manto_Platform\.marketing-agent-token -Raw).Trim()   # só o 256 usa
& $py specs\303-sync-nao-apaga-venda\verify_303.py
& $py specs\267-integridade-comissao\verify_267.py
& $py specs\267b-hotfix-data-da-venda\verify_267b.py
& $py specs\267c-hotfix-trava-do-lote\verify_267c.py
& $py specs\299-sem-valor-cobrancas\verify_299.py
& $py specs\215b-hotfix-taxa-e-vendedor\verify_215b.py
& $py specs\305-bv-do-orcamento-no-evento\verify_305.py
& $py specs\205-loja-interacoes-virtuais\verify_205.py
& $py specs\266-costuras-funil\verify_266.py
& $py specs\258-cliente-manual\verify_258.py
& $py specs\256-auditor-marketing\verify_256.py
& $py specs\273-orcamento-para-evento\verify_273.py
& $py specs\301-orcamentos-visiveis-comercial\verify_301.py
& $py specs\272-notificacoes-internas\verify_272.py
& $py specs\238-teto-autorizado\verify_238.py
& $py specs\271-hotfix-corrida-lancamentos\verify_271.py
& $py specs\307-natal-papai-noel-calculadora\verify_307.py
```

| Verify | O que muda com a 306 | Fase em que pode quebrar primeiro |
|---|---|---|
| `verify_303` | **Reescrito**: o `c12_nao_cancela` (`:2339`) passa a cancelar o marcado. A exclusão continua recusada, com o `MSG_MARCADO` (`:167`) novo | História 2 |
| `verify_267` | **Reescrito** em `:278-289`: lê o bloco `cancelamento` de um `legado`, em vez de `kpi["commission"]` de um cancelado gravado à mão | História 2 |
| `verify_267b`, `verify_267c` | Extração da comissão, item da Planilha (`S:C`, `S:C:pago`) e desfazer, que agora trava os eventos antes | História 1 |
| `verify_299` | Ciclo da comissão | História 1 |
| `verify_215b` | A regra do cancelado roda antes da taxa e do vendedor | História 2 |
| `verify_305` | `marcar_status_do_bv` substitui o ramo BV da 305 (`app/api/financeiro_write.py:163-194`), e o 409 do BV com `valor_esperado` divergente ganha o código `valor_mudou`; `valor_esperado` também no `expense`; `_montar_acrescimos` fatiado não muda o vivo. Roda ao fechar a História 1 e de novo logo depois da extração, antes de ela ser usada no cancelado | História 1 (`marcar_status_do_bv`), e de novo na História 4 (a extração) |
| `verify_205` | Pipeline e Loja Virtual | História 2 |
| `verify_266`, `verify_258`, `verify_256` | Rodar de novo | Polimento |
| `verify_273` (base 8/15), `verify_301` | O 409 novo em `set_event_orcamento`, antes de aplicar a venda e antes da autoria da 301 | História 2 |
| `verify_272` | `DESTINATARIOS_POR_KIND` ganha dois kinds | História 6 |
| `verify_238` | `assign_role` ganha a condição do e-mail de remoção | História 6 |
| `verify_271` | `GET /api/dashboard`: Performance (História 3) e cobrança da Home (História 5) | História 3 |
| `verify_307` | Arquivos em comum com a 307 (`orcamento_evento_ops.py`, `orcamento/quote_ops.py`, `calendar/routes.py`) | História 2 |

- O `verify_305` roda sem `--regressao`. A regressão dele repete 267b, 215b, 267c e 267, e traz o 273 com
  base conhecida de 8/15; o 273 entra aqui por conta própria, comparado com essa base.
- Os verifies de `scripts/db/` não rodam: o `verify_151_excluir_sync.py`, por exemplo, falaria com o Google
  real. Eles envelhecem e vão ao `docs/05` como dívida.

## 6. Portões

```powershell
cd C:\tmp\mp306\frontend
npm ci                  # uma vez: o worktree nasce sem node_modules
npm run typecheck       # um comando, as três SPAs
npm run build           # antes do merge
cd ..
$ruff = 'C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\ruff.exe'
& $ruff check @(git diff --name-only --diff-filter=d main -- '*.py') @(git ls-files --others --exclude-standard -- '*.py')
& $ruff format specs\306-dinheiro-do-cancelamento\verify_306.py specs\306-dinheiro-do-cancelamento\retrato_main_branch.py `
  specs\306-dinheiro-do-cancelamento\contagem_pre_deploy.py app\financeiro\dre_ops.py
```

- O portão do `ruff check` é **nenhum erro novo**. Em `d855d1a` (e de novo em `6356b80`, com a 307), os arquivos de `app/` que a 306 toca já
  somam 14 erros: 8 em `app/calendar/routes.py`, 5 em `app/models.py` e 1 em `app/financeiro/routes.py`.
  Eles não se limpam de passagem; compare com a mesma lista na `main`.
- `ruff format` só roda nos três scripts novos e no `dre_ops.py`.

## 7. Build num venv Python 3.11 (antes do push)

Por que reproduzir o build:
- o `startCommand` roda `flask db upgrade && python seed.py`;
- o build do Render (Python 3.11.9) reinstala as dependências transitivas na última versão. Foi isso que
  derrubou a 303 em 01/10: o SQLAlchemy 2.1 trouxe o psycopg 3;
- o `.venv` local é Python 3.14 com psycopg 3, então verde nele não prova o build.

```powershell
$v = "$env:TEMP\venv306_py311"
uv venv --python 3.11 $v
uv pip install --python "$v\Scripts\python.exe" -r requirements.txt tzdata       # tzdata só no Windows
uv pip freeze --python "$v\Scripts\python.exe" | Out-File -Encoding utf8 "$env:TEMP\freeze_306_py311.txt"
ssh -i $HOME\.ssh\render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com `
  '/opt/render/project/src/.venv/bin/python -m pip freeze' | Out-File -Encoding utf8 "$env:TEMP\freeze_306_prod.txt"
Compare-Object (Get-Content "$env:TEMP\freeze_306_prod.txt") (Get-Content "$env:TEMP\freeze_306_py311.txt")
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim() -replace '^postgresql\+psycopg://', 'postgresql://'
& "$v\Scripts\python.exe" -m flask db downgrade a7c3e91f4d28
& "$v\Scripts\python.exe" -m flask db upgrade; & "$v\Scripts\python.exe" seed.py
& "$v\Scripts\python.exe" specs\306-dinheiro-do-cancelamento\verify_306.py
```

**Esperado**
- O `Compare-Object` lista o que o build da noite vai trocar, além do `tzdata`. Uma versão maior nova de
  dependência transitiva é fixada no `requirements.txt` antes do push.
- Migration, seed e `59/59 OK` passam nesse venv.
- Depois, volte o `DATABASE_URL` ao valor dos pré-requisitos.

## 8. Tela aberta (desktop; app interno)

**Dados**: o verify semeia e limpa os dados da conferência.

```powershell
& $py specs\306-dinheiro-do-cancelamento\verify_306.py --semear-tela   # imprime ids e usuários por item; não limpa
# … conferir …
& $py specs\306-dinheiro-do-cancelamento\verify_306.py --limpar-tela   # com o backend parado
```

O `--semear-tela` cria:
- o **evento-exemplo** da spec: venda 2.000, comprovante de 1.000, BV 200 a pagar sem recebedor nem PIX,
  nota fiscal e comissão cheia 90 (taxa de 5%) a pagar ao vendedor descartável;
- **três grupos**: um para "todos os dias", um para o corte de um satélite e um para a passagem do
  principal;
- um **show com escalados** e um **com cachê pago**;
- um **evento marcado** (`google_missing_since`);
- uma **linha `no_banco`** com data no dia 1º;
- os **usuários por papel**.

Os eventos ficam em meses isolados. O cancelamento cai no mês corrente.

**Subir, com as variáveis dos pré-requisitos em cada terminal**:

```powershell
# terminal 1: o Flask do worktree, com o Google dublado (insert, update e delete só registram)
& $py C:\Users\schim\Desktop\Manto_Platform\scripts\db\run-local-sem-google.py
# terminal 2: o app interno do worktree
cd C:\tmp\mp306\frontend; npm run dev:internal
```

- Abra o Browser pane por URL (`http://localhost:5173`), com a porta 5000 livre.
- **Não use**:
  - as entradas `manto-backend-sem-google` e `manto-internal` do `launch.json` do usuário: elas servem o
    repositório principal, isto é, o código da `main`;
  - as do `.claude/launch.json` do repositório: usam `.venv` e `scripts\db\` relativos, que o worktree não
    tem.

**Regras da conferência**
- **E-mail e Google**:
  - o e-mail fica travado (`_suppress_mail`, porque o banco é localhost);
  - o Google fica dublado, e a remoção do cancelamento passa também pela trava
    `CALENDAR_SUPPRESS_EVENT_WRITES`.
- **Entrar e digitar**:
  - o login é com os descartáveis do `--semear-tela`, porque a senha do SUPERADMIN do espelho muda a cada
    verify;
  - preencha pelo setter nativo. No `MoneyInput`, o setter só aceita dígitos (`60000` = R$ 600,00);
  - entre um diálogo e outro, recarregue a página: o Dialog fechado não desmonta.
- **DRE antiga**:
  - é o Flask direto: `http://localhost:5000/financeiro/?period=custom&start=AAAA-MM-01&end=AAAA-MM-DD`;
  - a sessão do app interno vale lá, porque o cookie é de `localhost` e não distingue porta;
  - nunca abra a raiz `http://localhost:5000/`: ela redireciona para a produção.

**O que conferir**. Entre parênteses, a fase em que o item fica disponível.

*Diálogo de cancelar* (Superadmin):
1. (H2) Evento-exemplo:
   - nada vem escolhido entre Tudo, Parte e Nada;
   - "A cliente pagou R$ 1.000,00";
   - com Parte 600, a prévia (≥ 400 ms depois de parar de digitar, sem piscar) mostra retido 400, BV do
     retido 40 e a comissão do retido 18, com o efeito na linha: a de 90 a pagar vira 18 no lugar;
   - recebedor e PIX do BV, e o imposto (por ter nota), são obrigatórios;
   - o erro aparece no campo, sem apagar o que foi digitado;
   - depois de confirmar, o resultado do item 8 bate com a prévia.
2. (H5) Principal de grupo: a lista dos dias vivos e "Cancelar todos os dias", sem o aviso antigo de líder.
3. (H5) Dia que não é o principal: "Novo valor da venda" é obrigatório.
4. (H6) Show com cachê pago: a recusa diz qual dia, não tem botão de cancelar e aponta Gastos Extras.
5. (H6) Show com escalados: o bloco "Multa ao elenco" tem uma linha por escalação (artista, vaga e dia), o
   cachê de referência, "faltavam N dias" e o aviso de talento sem PIX. Campo vazio = sem multa.
6. (H5) "Cancelar só este dia" no principal diz para qual dia a venda passa (o dia vivo mais cedo).

*Evento cancelado*:

7. (H5) Depois do item 6:
   - o novo principal mostra venda, comprovantes e comissão;
   - o antigo 1º dia tem o link "a venda passou para DD/MM".
8. "Resultado do cancelamento" e "Alterar devolução".
   - **(H2) Evento-exemplo**:
     - o resultado aparece no lugar dos KPIs: 1.000 / 600 / 400 / 18 / 40;
     - em "Alterar devolução", 600 → 800 relê retido 200, comissão 9 e BV 20;
     - com a devolução marcada paga na Planilha, diminuí-la dá 409 `abaixo_do_piso` no campo.
   - **(H5) Dia cortado** (o satélite do grupo do item 2):
     - não há campo de imposto;
     - 300 → 30 refaz a devolução do dia e o "já devolvido", e a comissão do principal vivo não muda;
     - acima do teto, 409 `acima_do_teto` com o teto;
     - abaixo do piso, 409 `abaixo_do_piso`;
     - depois de cancelar o resto do grupo, a mesma alteração refaz o retido e a comissão do principal.
9. (H4) Dados de venda abertos ao Superadmin:
   - valor corrigido, com o resultado relido;
   - troca de vendedor com o aviso de que "o retido e a comissão do retido passam a <novo>";
   - BV corrigido, com o BV pago só leitura;
   - reembolso lançado; nota e parcela gravadas;
   - "Editar tudo" ausente.
10. (H6) "Lançar multa ao elenco":
    - quem saiu da escala aparece marcado;
    - 150 vira o Gasto Extra "Multa de cancelamento"; vazio e 0 são ignorados;
    - tudo vazio ou 0 dá o erro "Informe a multa de ao menos um artista" no campo, e nada é lançado;
    - multa já lançada mostra erro no campo ("Corrija em Gastos Extras").
11. (H6) Como CASTING: o sino do cancelado (um por dia com escalados) abre o evento em `?aba=producao`.
12. (H2) Como COMERCIAL, com login real e não pelo "Ver como":
    - a tela é só de consulta;
    - numa aba aberta antes do cancelamento, acrescentar um comprovante mostra a frase do 409 `cancelado`
      no painel, e não o texto fixo.
13. (H2) A aba Comercial continua presente com `kpi` ausente.

*Evento marcado*:

14. (H2) As duas saídas ("Devolver ao Google" e cancelar) aparecem no diálogo e no banner.
    - A 375×812, o botão do banner tem largura total.
    - A faixa some logo depois de cancelar, sem esperar o poll.

*Financeiro e comercial*:

15. (H2) Gastos Extras, com a devolução travada (rótulo e ações):
    - "Salvar" sem mexer passa, e corrigir o PIX também;
    - mudar o valor dá a frase do 409 com link ao evento;
    - o tipo "cliente" não aparece ao criar.
16. (H1) Comissões do vendedor descartável:
    - filtro e quarto card "No banco";
    - colunas tipo e ciclo;
    - a data de borda no dia 1º, sem voltar um dia.
17. (H2; multa na H6) Planilha:
    - o BV do retido no mês do evento, com recebedor e PIX (40; 20 depois do 800 do item 8);
    - a devolução e a multa no mês do cancelamento;
    - no detalhe dos itens de comissão, as linhas (`commission_lines`), inclusive as de valor negativo.
18. (H5) Painel "Grupo comercial" com um dia cancelado:
    - sem "Agrupar mais um" nem "Desfazer" no dia cancelado;
    - o KPI do principal sem o custo dele.
19. (H3) DRE nova (`/financeiro`) e antiga do mês corrente, iguais ao centavo:
    - a linha "Retido de cancelamentos" traz a soma dos retidos do mês;
    - o resultado é o de antes + retido − imposto − BV do retido − comissão do retido. No evento-exemplo
      com nota e imposto 64, isso dá +278 (+342 sem nota), nunca −600;
    - o mês do evento fica sem nada.
20. (H3) O retido no vendedor congelado: a sublinha "de N cancelamentos" no Dashboard Comercial (`/vendas`)
    e o retido e os cancelados em `/admin/desempenho`.
21. (H2) `/events/cancelamentos` (Superadmin):
    - o resumo de cada cancelado e o estado da devolução, inclusive "no banco";
    - o PIX aparece só com `show_financeiro`.

## 9. Antes do merge e deploy

**Antes do merge**
1. A branch está rebaseada sobre a `main`, que já tem 303, 215b, 267c, 305 e 307 (`6356b80`), com as citações
   `arquivo:linha` reconferidas se a `main` andar de novo.
2. Tudo verde:
   - o §1 sem argumentos e com `--regressao`, mais o §3 idêntico, o §5 e o §6;
   - o §8, os 21 itens;
   - `/speckit-converge` sem gaps;
   - docs escritos.
3. `git status --short` limpo e `migrations/versions/` sem untracked.
4. O §7 passa no venv 3.11.

**Contagem do dia**: o §2 em produção, com os números no `docs/03`. Nada bloqueia o deploy, mas o dono
precisa saber, antes do push:
- quantos cancelados existentes (`legado`) há: a DRE do mês deles muda no deploy, porque a devolução sai
  dos gastos;
- as linhas `no_banco`, que passam a aparecer em Comissões;
- os marcados pela 303, que serão os primeiros cancelados;
- os BVs não pagos sem PIX, que o diálogo vai pedir;
- os grupos com o principal fora do 1º dia;
- os itens abertos de comissão de soma zero com linha de valor, que hoje somem da Planilha e passam a
  aparecer também em mês sem cancelamento (R6);
- os cancelados `legado` sem dinheiro, que hoje se excluem (inclusive pelo sync) e passam a dar 409 na
  exclusão (R7);
- a Tendência do mês do evento de cada `legado`, que deixa de contar a venda e o cachê (FR-043);
- as vendas vivas com devolução lançada à mão, cuja cobrança na Home passa a descontá-la (risco aceito 16).

**Deploy**
- Só quando o dono pedir ("push", "sobe"). O push é o merge na `main` mais `git push origin main`, numa
  chamada isolada.
- À noite (≥ 19h de Brasília, conferido por `Get-Date`), sozinha, com backend e frontend no mesmo push.
- O `startCommand` não muda, e não há env nova.

**Depois do push**
- **Backend no ar**: sonde duas vezes; 502 isolado é troca de container.

  ```powershell
  curl.exe -s https://app.mantoproducoes.com.br/api/formularios/comum/schema                  # JSON = Flask no ar e migration aplicada
  curl.exe -s -o NUL -w '%{http_code}' -X PATCH https://app.mantoproducoes.com.br/api/events/1/devolucao   # 401 = backend novo; 404 = ainda o antigo
  ```

- **Container**, por SSH e só leitura: o código, a revisão do banco e o bundle.

  ```powershell
  ssh -i $HOME\.ssh\render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com `
    'cd /opt/render/project/src && grep -c alterar_devolucao app/calendar/cancel_ops.py && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask db current'
  ssh -i $HOME\.ssh\render_manto_ed25519 srv-da8nvsgn74is73ehe9a0@ssh.oregon.render.com `
    'grep -rl Alterar.devolu /opt/render/project/src/frontend/apps/internal/dist/assets'
  ```

  A revisão é a da 306 `(head)`, e o bundle novo tem o texto. Uma tela que não bate com o código é bundle
  antigo no navegador: recarregue.
- **Evento descartável**:
  - título que diga que é teste, contrato anexado (para o diálogo oferecer "cancelar") e **sem venda**;
  - sem artista de verdade escalado e sem ensaio, porque o cancelamento avisa elenco e equipes e tira o
    ensaio do Google;
  - cancelar com "Nada".
- **Telas, depois do descartável**:
  - `/events/cancelamentos` mostra o evento. Ele fica lá para sempre (risco aceito 9);
  - a DRE do mês, nas duas telas, aparece **sem** a linha do retido: cancelado sem dinheiro fica fora
    (P-24). A antiga só responde pelo domínio direto do backend
    (`https://manto-backend.onrender.com/financeiro/`), com login próprio;
  - a Planilha do mês seguinte e Comissões não mudam.
- **`docs/03`**: "EM PRODUÇÃO desde …", conferido pela sonda, com `git log --oneline -1` batendo.

**Rollback**
- Enquanto nenhum cancelamento real aconteceu, reverter o merge (`git revert -m 1 <merge>` + push) é limpo.
  A migration é aditiva: as tabelas ficam, o código antigo as ignora, e não se roda `downgrade`.
- O descartável não tem venda, comissão nem BV: o código antigo não tem o que estragar nele.
- Depois do primeiro cancelamento real, só se corrige para a frente (`306b`). Nunca `downgrade` com linha
  em `event_cancellations`: ele apaga o congelamento, e nada mais se refaz. Sobre os dados novos, o código
  antigo:
  - zeraria a comissão do retido;
  - tomaria o ajuste do corte de dia (`a_pagar` com `original_id`, ligado ao principal vivo) pela comissão do
    evento e o regravaria com a cheia;
  - listaria pelo cheio o BV não pago do cancelado, e a Planilha da 305 deixaria marcá-lo pago por esse valor;
  - deixaria excluir o cancelado vazio, inclusive pelo sync, e o CASCADE levaria o congelamento junto.
- Não voltam: ensaios apagados, e-mails enviados e venda passada de dia.
- Antes de um segundo deploy às cegas, peça ao dono o log do painel.

**O dono roda**: nada.

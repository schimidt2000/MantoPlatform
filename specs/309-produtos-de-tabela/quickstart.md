# Quickstart — 309 Produtos de tabela

> Como provar a feature de ponta a ponta. Tudo roda no worktree `C:\tmp\mp309` (a árvore principal está
> com a 308 de outro chat). `.venv` e `node_modules` são os do repositório principal, por caminho
> absoluto; `.local-db-url` já foi copiado para o worktree.

## Pré-requisitos

- `manto_local` no ar (espelho da produção; a configuração de preços real é salva e restaurada pelo
  verify por conexão separada).
- PowerShell: `$env:DATABASE_URL = (gc .local-db-url -Raw).Trim(); $env:FLASK_ENV = "development";
  $env:MANTO_SEM_THREADS = "1"; $env:PYTHONUTF8 = "1"` (sem `MANTO_SEM_THREADS` sobem as threads reais
  — o espelho tem token do Google e e-mail reais).
- Frontend: `node_modules` do principal — se o worktree não tiver, junção
  `cmd /c mklink /J C:\tmp\mp309\frontend\node_modules C:\Users\schim\Desktop\Manto_Platform\frontend\node_modules`
  (e o mesmo para `frontend/apps/*/node_modules` e `frontend/packages/*/node_modules` que existirem no
  principal).

## 1. Verify (Princípio VIII — vermelho antes do núcleo)

```powershell
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\309-produtos-de-tabela\verify_309.py
```

Primeira rodada (antes de `produtos.py`): cenários 2–15 e 18 FALHAM pelos motivos certos (chave
`produtos` ignorada → total 2.210 em vez de 2.500; sem `quote.produtos`; migração ainda entrega 712;
script inexistente); cenário 1 (paridade) e 17 (403) passam. Saída guardada em
`verify_309_primeira_falha.txt`.

Rodada final (portão da feature):

```powershell
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\309-produtos-de-tabela\verify_309.py --regressao
```

Esperado: `20/20 OK` — inclui o cenário 19 (`verify_307.py --regressao` reescrito e `verify_305.py
--regressao` em subprocesso). `--so=2,3` roda só os cenários listados (aspas simples no PowerShell:
`'--so=2,3'`).

## 2. Lint e typecheck

```powershell
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\ruff.exe check app\orcamento\ app\api\orcamento_write.py app\calendar\routes.py app\calendar\orcamento_evento_ops.py app\educamanto\quote_ops.py scripts\oneoff\rebaixar_tetos_noel_309.py specs\309-produtos-de-tabela\verify_309.py
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\ruff.exe format app\orcamento\produtos.py scripts\oneoff\rebaixar_tetos_noel_309.py specs\309-produtos-de-tabela\verify_309.py
cd frontend; npm run typecheck   # três SPAs
```

## 3. Telas (skill `manto-conferir-tela`, Browser pane — `launch.json` `manto-internal` + `manto-backend-sem-google`)

| Tela | O que conferir |
|---|---|
| `/orcamento` | card "Produtos de tabela" com Combobox; escolher "Visita Mágica — Papai Noel" em 20/12 → painel mostra **um valor** R$ 2.500,00; em 24/12 → R$ 5.000,00 + aviso dourado; somar um boneco → 4 colunas (boneco × markup + 2.500); coordenador mostra "1 incluído no produto"; "Papai Noel" avulso sem produto → aviso "use o produto"; simular `quote.produtos` ausente (devtools) → botão travado |
| `/orcamento/:id` (após Gerar) | linha "📦 Visita Mágica — Papai Noel — preço de tabela R$ 2.500,00"; memória com linha `produto` e fundo próprio; mensagem com o bloco do produto |
| `/orcamento/configuracoes` | card "Produtos de tabela": editar preço, adicionar faixa, chip de vaga; salvar com preço 0 → 400 com o campo destacado e foco; card "Estimativa" (fator/markup) |
| `/events/new?orcamento_id=<id>` | vagas Papai Noel / Coordenador / Maquiador com teto 600 / 250 / 250 (superadmin vê "Teto: …"); em 24/12 1.000 / 500 / 250 |

Depois da conferência, restaurar a tabela do `manto_local` se algum "Salvar" persistiu dados de teste
(o verify compara com a produção na preparação e avisa).

## 4. Script dos tetos já gravados (dry-run local, execute em produção)

```powershell
# local (espelho): só relatório
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe scripts\oneoff\rebaixar_tetos_noel_309.py
```

Em produção, no Shell do Render (ou SSH `srv-da8o06on74is73ehf4q0`): `cd /opt/render/project/src &&
MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python scripts/oneoff/rebaixar_tetos_noel_309.py` → ler o
relatório → `--execute` → rodar de novo sem flag e conferir "0 a corrigir".

## 5. Pós-deploy (só quando o dono pedir "push" — skill `manto-deploy`)

Merge `--no-ff` na `main` a partir do worktree (`git -C C:\Users\schim\Desktop\Manto_Platform` só se a
árvore principal estiver limpa e na `main`; senão, merge dentro do worktree e `git push origin main`),
sonda `/api/formularios/comum/schema` em JSON, `RENDER_GIT_COMMIT` por SSH, conferência só de leitura
(`settings.load()`: Noel 600, Ajudante 270, `produtos` com os dois padrão; `calculate_quote` com o produto
em 20/12 = 2.500 e em 24/12 = 5.000), script dos tetos, e aviso à equipe: a Visita Mágica agora é o
produto da calculadora — nada de "Papai Noel" avulso para visita, nada de acréscimo "Outro".

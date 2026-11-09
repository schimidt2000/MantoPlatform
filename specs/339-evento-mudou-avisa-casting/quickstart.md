# Quickstart — validar a Feature 339

Tudo roda a partir do worktree `C:\tmp\mp339`, com o `.venv` e os arquivos locais do checkout
principal (o worktree não tem `.env`, `.local-db-url` nem `.venv`).

## 1. Banco

O `manto_local` pode estar preso na migration de outra feature (memória "espelho próprio por
feature"). Se `flask db upgrade` acusar head desconhecido, crie `manto_339` do dump noturno e aponte o
`DATABASE_URL` para ele.

```powershell
$env:DATABASE_URL = (Get-Content C:\Users\schim\Desktop\Manto_Platform\.local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\flask.exe db upgrade
```

Esperado: a migration da 339 aplicada; `SELECT count(*) FROM event_roles WHERE teto_autorizado IS NOT
NULL` igual ao número de vagas com `cache_value > cache_cap` sem carrinho.

## 2. Verify

```powershell
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe specs\339-evento-mudou-avisa-casting\verify_339.py
```

Esperado: os cenários da tabela da spec (seção "Verificação"), cada um com OK; os dois que **devem
falhar** (12 e 21) aparecem como recusa correta. Google, e-mail e threads falsos (`research.md` R9):
nenhuma escrita no calendário da empresa, nenhum e-mail.

## 3. Portões de código

```powershell
cd frontend; npm run typecheck; cd ..
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\ruff.exe check <arquivos Python tocados>
```

## 4. Tela (skill `manto-conferir-tela`)

Backend e Vite próprios em outra porta (memória "conferir tela em worktree": o `preview_start` usa a
`launch.json` do checkout principal). Com um evento descartável de teste:

1. Como Comercial, trocar R&I → SHOW: resposta com o aviso de vincular o orçamento; nenhuma faixa
   para quem trocou.
2. Como Casting A e Casting B: sino com o aviso; faixa no evento com a lista de escalados. A dá
   "Ciente" → some para A, continua para B. Abrir pelo sino não apaga a faixa.
3. Como Ensaio: faixa sem valores de cachê.
4. Como Superadmin: linha do teto com "autorizado por … em …" depois de salvar acima do limite;
   trocar a pessoa e salvar o mesmo valor como Casting.
5. Remover uma de duas vagas iguais: título do evento e do ensaio futuro com uma ocorrência a menos.
6. Viewport mobile 375×812 no detalhe do evento (o Casting usa o celular).

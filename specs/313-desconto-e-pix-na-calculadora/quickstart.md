# Quickstart — validar a 313

## Pré-requisitos

Worktree `C:\tmp\mp313`; `.local-db-url` na raiz; ambiente do verify (PowerShell):

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'; $env:PYTHONPATH = (Get-Location).Path; $env:PYTHONUTF8 = '1'
```

## 1. O gabarito (antes de mexer no núcleo)

`python specs/313-desconto-e-pix-na-calculadora/gabarito_paridade.py --gravar <scratchpad>\gabarito313.json` — na
`c074657b` (só leitura; recalcula todos os `form_snapshot`). Guarda contagem e o hash do JSON.

## 2. O verify

`python specs/313-desconto-e-pix-na-calculadora/verify_313.py` → todos os cenários da spec OK (0 = tudo OK, 1 =
falha, 2 = ambiente impróprio). `--so=N,M` para iterar; a limpeza roda sempre. Regressão:
`specs/305-…/verify_305.py --regressao`, `specs/309-…/verify_309.py`, `specs/307-…/verify_307.py`,
`specs/235-…/verify_235.py` (o `verify_190` de `scripts/db/` saiu: importa um modelo que a 235 removeu).

## 3. Portões

- `cd frontend && npm run typecheck`; `ruff check` nos arquivos tocados (comparar com HEAD).
- **Tela aberta** (skill `manto-conferir-tela`, backend do worktree na 5011 com o Google dublado, interno na 5193):
  1. calculadora — desconto em % e pelo valor ("fechar as 2h por R$ 2.200"), ida e volta; digitar com pausa (sem %
     absurdo como resultado); erro no campo; produto de tabela; personalizado; duração extra com acréscimo em R$;
     BV em % e em reais (a linha nova de BV nascendo com "%"); o card Resultado com o cheio riscado, o PIX e o BV a
     repassar; tema claro e escuro;
  2. orçamento gerado (mensagem com "de/por" e os dois casos do PIX) e o **PDF aberto de verdade**;
  3. histórico com o selo "−N%";
  4. Novo evento a partir do orçamento com desconto e BV — o cheio e a venda separados, o selo do valor de venda, o
     quadro do BV acompanhando, a troca de duração e o "Outra (h)"; **sem salvar** (o `POST /api/events` escreve no
     Google sem trava — a gravação se prova no verify, com o Google dublado);
  5. EducaManto: o editor de acréscimos com a ajuda dele.
- A mensagem colada no WhatsApp e o PDF no celular (o que a cliente abre).

## 4. Depois do deploy (com o dono)

Um orçamento de verdade com desconto calculado em produção, o PDF baixado, e o primeiro evento criado a partir dele
conferido (cheio, venda, BV).

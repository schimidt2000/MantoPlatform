# Quickstart — 342

## Espelho próprio

O `manto_local` está numa migration do CRM. Crie `manto_342` do dump noturno (`DEVELOPMENT.md`
§Banco local), aponte `DATABASE_URL` para ele e rode `flask db upgrade`.

```powershell
$env:DATABASE_URL = '<url do manto_342>'; $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'; $env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -m flask db upgrade
.\.venv\Scripts\python.exe specs\342-nota-nasce-com-dados\verify_342.py
```

Esperado: todos os cenários da tabela da spec em verde, os marcados "deve falhar" recusados.

## Portões

```powershell
cd frontend; npm run typecheck
ruff check <arquivos tocados>
```

## Telas (Browser pane)

1. `/f/pre-contrato` e `/f/corporativo` em 375×812: marcar "Preciso de nota fiscal"; documento e
   e-mail vêm preenchidos; trocar para um CNPJ abre a pergunta do ISS; enviar com documento errado
   mostra o erro no campo.
2. Evento com esse formulário ligado → card Comercial → Editar: "Dados da nota" mostra as respostas
   da cliente e o município sugerido.
3. Evento sem documento em lugar nenhum: ligar "Precisa de nota fiscal" e salvar → erro no campo.
4. Tela inicial do Superadmin: painel "Notas a emitir" com e-mail e município.
5. Formulários → Editor: condição num campo personalizado.

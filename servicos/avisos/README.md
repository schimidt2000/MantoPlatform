# manto-avisos — a caixa de avisos de pagamento (feature 340)

Serviço web do Render que recebe o aviso de pagamento da InfinitePay e **só guarda**. Quem decide
se o pagamento vira venda continua sendo o `manto-backend`, que drena a tabela
`virtual_payment_inbox` a cada 10 s e no início de cada varredura da loja
(`app/marketing/virtuais_ops.py`, `drenar_caixa_de_avisos`).

## Por que existe

Todo push na `main` troca o `manto-backend`, e um serviço com disco persistente não troca de
container sem ficar fora do ar (~1 min de 502). A InfinitePay só reenvia o aviso quando recebe 400;
com 502 o aviso se perdia. Este serviço não tem disco, tem healthcheck (o Render só troca o container
depois de o novo responder) e só faz deploy quando esta pasta muda (`rootDir` no `render.yaml`).

## Por que não importa `app/`

Importar o app traria `create_app`, as threads de fundo, o Google e o e-mail, e cada mudança do
backend passaria a exigir deploy daqui. Este código tem de ser o que quase nunca muda. Ele repete três
regras curtas do backend, e o `verify_340.py` confere que as duas pontas concordam:

- o segredo do endereço (`virtuais_ops.token_do_aviso_valido`: atual, ou anterior dentro da janela);
- o teto de 64 KB do corpo (`app/api/virtuais_webhook.py`);
- o IP do cliente como o último item do `X-Forwarded-For` (`frontend/server.js`, `ipDoCliente`).

O segredo nunca vai para log nem para o banco.

## Contrato

`specs/340-caixa-de-avisos/contracts/manto-avisos.md`.

## Rodar local

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
C:\Users\schim\Desktop\Manto_Platform\.venv\Scripts\python.exe servicos\avisos\app.py 5340
```

O `gunicorn` não roda no Windows; `python app.py <porta>` sobe o servidor WSGI da biblioteca padrão,
só para teste manual. A verificação de verdade é o `verify_340.py`, que usa a aplicação WSGI direto.

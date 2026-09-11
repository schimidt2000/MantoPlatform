# Quickstart — como provar a feature 298 de ponta a ponta

## 1. Ambiente local (PowerShell, na raiz do repositório)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'
.\.venv\Scripts\python.exe -m flask db upgrade        # aplica a migration da 298 no manto_local
```

Conferir o head: `.\.venv\Scripts\python.exe -m flask db heads` deve mostrar só a revision da 298.

## 2. Verificação automática

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe specs\298-formulario-vira-evento\verify_298.py
```

- Esperado: `17/17 OK` (as 17 linhas da tabela da spec) e código de saída 0.
- O cenário 15 é o que **deve** ser recusado:
  - CASTING tenta encerrar e FINANCEIRO pede os dados para o cadastro de evento;
  - os dois recebem exatamente 403, e o formulário continua intacto;
  - como controle, COMERCIAL recebe 200 no mesmo formulário.
- Os cenários 14a e 14b substituem o antigo 14. No total são 17 linhas de verificação (1–13, 14a,
  14b, 15 e 16), e a saída esperada é `17/17 OK`.
- O verify nunca escreve no Google Agenda:
  - dentro do processo, `app.calendar.routes.insert_event` é trocado por uma chamada falsa que falha
    se for chamada;
  - o único `POST /api/events` é o da guarda de 409 (cenário 14a);
  - todo evento de teste leva "[TESTE verify 298] pode apagar" no título.
- Os dois comandos de correção também são exercitados pelo verify (cenário 14b): sem `--execute` só
  contam, com `--execute` aplicam.

```powershell
cd frontend; npm run typecheck; cd ..
.\.venv\Scripts\ruff.exe check <arquivos Python tocados>
```

## 3. Conferência de tela (Browser pane, skill `manto-conferir-tela`)

1. **Home**, logada como COMERCIAL:
   - bloco "Formulários sem evento na agenda" com os dois grupos, cores e marcas;
   - uma linha repetida que expande, e uma linha com sugestão;
   - estado vazio;
   - largura de computador e estreita;
   - movimento reduzido ligado.
2. **Home**, logada como FINANCEIRO (ou "Ver como FINANCEIRO"): a ação principal é "Abrir", não
   "Criar evento".
3. **Tela Formulários**:
   - cartões "Sem destino (desde 01/06)", "Com evento", "Encerrados" e "Histórico";
   - encerrar com "Outro" sem frase deve apontar o campo;
   - reabrir;
   - "Recebida em" na hora certa;
   - formulário com cliente diferente da cliente do evento: as duas aparecem e "usar a cliente do
     evento neste formulário" troca só a do formulário.
4. **Criar evento** a partir de:
   - um formulário nativo de festa;
   - um formulário da carga WhatsForm (hora dentro da data);
   - um corporativo (endereço do evento, briefing);
   - um com data de 2049 e "Boleto".

   Em cada um conferir os campos marcados, os alertas e o aviso de evento existente da cliente. Com a
   data suspeita, o Salvar continua ativo: clicar sem confirmar marca o campo com a explicação e rola
   até ele.
   **Não salvar** evento real em ambiente ligado ao Google.

## 4. Produção (depois do merge e do push, que o dono pede)

1. **Deploy.** O `startCommand` aplica a migration aditiva. Sondar
   `https://app.mantoproducoes.com.br/api/formularios/comum/schema`, que precisa devolver JSON. 502
   isolado nos primeiros minutos é troca de container.
2. **Avisos antigos**, no SSH do `manto-backend`, primeiro contando e depois executando:
   ```bash
   cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask formularios-avisos-resolvidos
   cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask formularios-avisos-resolvidos --execute
   ```
   Esperado: ~35 avisos na contagem de 10/09 (SC-007).
3. **Clientes dos formulários já ligados** (FR-020), no mesmo SSH, primeiro contando e depois
   executando:
   ```bash
   cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask formularios-cliente-do-evento
   cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/flask formularios-cliente-do-evento --execute
   ```
   Esperado: cerca de 69 na contagem de 10/09 (SC-004).
4. **Números**, com consulta só de leitura:
   - `sem_destino` ≤ 36 (SC-001);
   - nenhum aviso `form_response.nova` não lido de formulário com evento (SC-007);
   - nenhum formulário desde o corte ligado a evento com cliente e ainda sem cliente (SC-004);
   - o topo da Home deixa de somar o histórico (SC-008).

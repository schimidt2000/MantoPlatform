# Quickstart — como provar a feature 299 de ponta a ponta

## 0. Antes do deploy: conferência dos dados (decisão do dono, 14/09)

Rodar no `manto-backend`, só leitura, com `MANTO_SEM_THREADS=1`, o levantamento que lista:
- o grupo 344, com os comprovantes de cada evento, datas e valores;
- os outros 5 casos grandes de recebido acima do valor (85, 184, 288, 309, 319);
- as vendas desde a data de início que têm comprovante sem valor, com quanto cada uma passaria a
  cobrar em "Cobranças".

O script é o `specs/299-sem-valor-cobrancas/dados_pre_deploy_299.py`, versionado e só leitura. Ele
lista também a consulta do SC-001 e os eventos de valor simbólico com o bruto:

```bash
ssh -i ~/.ssh/render_manto_ed25519 srv-da8o06on74is73ehf4q0@ssh.oregon.render.com 'cd /opt/render/project/src && MANTO_SEM_THREADS=1 PYTHONPATH=$PWD .venv/bin/python -' < specs/299-sem-valor-cobrancas/dados_pre_deploy_299.py
```

O dono confere e corrige o que precisar **antes** de publicar.

**Aviso à equipe no dia** (o dono decide quem envia):

> A Home mudou: o painel "Comercial" virou dois — "Cobranças" e "Sem valor". Cobranças agora mostra
> todas as vendas com dinheiro a receber, com a data de vencimento, e por isso a lista ficou maior.
> O número do topo ficou menor porque só conta o que precisa de ação (vermelho e amarelo). Em "Sem
> valor" estão os eventos lançados sem valor de venda: é clicar em "Pôr o valor", digitar e salvar. No cadastro, quem
> ainda não tem o preço marca "Valor a definir" — não precisa mais pôr R$ 0,01.

## 1. Ambiente local (PowerShell, na raiz do repositório)

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'
```

Não há migration. Conferir que o `release_date` do espelho é 01/06/2026: o verify confere sozinho e
falha com a mensagem "corte do espelho diferente de 01/06".

## 2. Verificação automática

```powershell
.\.venv\Scripts\python.exe specs\299-sem-valor-cobrancas\verify_299.py
```

- **Resultado**: `17/17 OK` e código de saída 0.
- **Google**: a saída imprime as chamadas ao Google falso (`insert` e `update`).
  - Nenhuma chegou ao Google real: `service.insert_event` e `load_credentials` estouram se forem
    chamados.
  - Os eventos de teste levam "[TESTE verify 299] pode apagar" no título e `v299-` no
    `google_event_id`.
- **Cenário 16, o que DEVE ser recusado**:
  - CASTING recebe o dashboard sem o bloco `comercial` e o detalhe do evento sem `cobranca`/`venda`;
  - FINANCEIRO recebe exatamente 403 ao criar evento e ao editar tudo, e nada é gravado;
  - como controle, FINANCEIRO vê a cobrança do grupo na Home e aplica o orçamento dele (200); o
    COMERCIAL criando com 201 fica no cenário 5(a).

Regressões, rodar de novo e esperar o mesmo verde de antes:

```powershell
.\.venv\Scripts\python.exe specs\298-formulario-vira-evento\verify_298.py
.\.venv\Scripts\python.exe specs\273-orcamento-para-evento\verify_273.py
.\.venv\Scripts\python.exe specs\174-redesenho-fidelidade-visual\verify_174.py
```

- **`verify_298`**: continua 17/17. O `formularios` só ganha `para_agir`, por acréscimo.
- **`verify_273`**: a cortesia continua sem receber os valores do orçamento.
- **`verify_174`**: `comercial.pending_payments` continua sendo lista.

```powershell
cd frontend; npm run typecheck; cd ..
.\.venv\Scripts\ruff.exe check app\financeiro\cobranca_ops.py app\api\dashboard_service.py app\api\agenda_read.py app\api\agenda_write.py app\calendar\event_ops.py app\calendar\routes.py app\calendar\orcamento_evento_ops.py app\financeiro\comissoes_ops.py app\formularios\destino_ops.py app\constants.py
```

## 3. Conferência de tela (Browser pane, skill `manto-conferir-tela`)

1. **Home, como COMERCIAL**, no computador e a 375 px:
   - os painéis "Cobranças" e "Sem valor", com os cards do topo de mesmo nome;
   - cores e selos em português, sem `URGENT`/`WARN`/`INFO`;
   - "Mostrar todas";
   - estado vazio;
   - o total do topo sem as linhas cinza;
   - nenhuma rolagem horizontal;
   - movimento reduzido ligado;
   - "Pôr o valor" em 2 cliques: a aba Comercial abre em edição, com o foco no valor de venda
     final, e o segundo clique é "Salvar venda";
   - de volta à Home, a linha que ganhou valor sai com a animação.
2. **Home, como FINANCEIRO** ("Ver como"): a linha "sem valor" oferece "Abrir".
3. **Regressão da 298**: o painel de Formulários igual ao de antes, com o texto "passou há N dias",
   repetidos e sugestão.
4. **Cadastro de evento**:
   - "Valor a definir" esconde os valores;
   - salvar sem valor e sem a marca aponta o campo e leva o foco até ele;
   - com a marca, salva e o evento aparece em "Sem valor".
5. **Edição completa**:
   - de um evento importado do Google sem valor, abre marcada e salva só o título;
   - de um evento de R$ 0,01, abre desmarcada;
   - de um outro evento de grupo, a marca vem travada, com o link para o principal.
6. **Aba Comercial**:
   - "A definir" no lugar de R$ 0,00;
   - no principal de um grupo, "Recebido X de Y" com os comprovantes dos outros eventos;
   - no outro evento, o texto do grupo e o link para o principal.
7. **Janela de deploy** (SC-011):
   - o bundle novo com um payload de servidor antigo (sem `sem_valor`, `cobrancas_resumo`,
     `para_agir` nem os campos novos da linha): a Home sem erro, Cobranças com as linhas cinza e sem
     selo, sem o painel "Sem valor";
   - a `DashboardPage.tsx` da `main`, numa cópia temporária no harness, com o payload novo: o painel
     "Comercial" de hoje, sem erro.

## 4. Depois do deploy (quando o dono pedir)

Sem comando pós-deploy. Conferir na produção:
- o painel "Sem valor" com as vendas sem valor desde 01/06 (6 em 14/09, menos as que ganharam valor)
  e nenhum "🟧 VISITA TECNICA" ou "🟠 GRAVAÇÃO";
- o grupo 344 fora de "Cobranças";
- nenhuma linha por centavos;
- as vendas com metade paga aparecendo com vencimento.

Avisar a equipe no dia: as cobranças crescem (as escondidas aparecem) e o total do topo cai (as
cinza deixam de contar).

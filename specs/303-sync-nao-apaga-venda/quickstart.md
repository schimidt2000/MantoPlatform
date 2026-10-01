# Quickstart — validar a 303 de ponta a ponta

**Spec**: [spec.md](./spec.md) · **Contratos**: [contracts/api-endpoints.md](./contracts/api-endpoints.md)
· **Modelo**: [data-model.md](./data-model.md)

Roteiro de validação. Não traz código de implementação — isso é do `tasks.md`.

## 0. Ambiente

```powershell
cd C:\Users\schim\Desktop\Manto_Platform
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim()
$env:FLASK_ENV = 'development'
$env:MANTO_SEM_THREADS = '1'
$env:PYTHONUTF8 = '1'
```

O `manto_local` traz o token real do Google e credenciais reais de e-mail. **O backend local tem de
estar parado** enquanto o verify roda (a thread de sync falaria com o Google real sobre os eventos
de teste) — o verify aborta com exit 2 se perceber um sync recente.

## 1. Contagem pré-deploy (antes do `/speckit-tasks`, e de novo no dia do deploy)

Só leitura: lê o banco em transação somente leitura e o Google só com `list` e `get`.

```powershell
scripts\db\refresh-local-db.ps1                      # espelho do dump da madrugada
.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\contagem_pre_deploy.py --so-sonda
.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\contagem_pre_deploy.py
```

Esperado na saída: o que o Google responde para evento apagado (404, 410 ou `cancelled` — se vier
outra coisa, o dublê e o núcleo ganham o quarto caso antes de tudo); e, dos meses passados: eventos
com dinheiro confirmados ausentes (quantidade, R$ e lista), eventos que mudariam de data com elenco
de convite aceito, inconclusivos, pais vazios com ensaio ligado, SHOW sem venda com cachê na vaga
automática, e eventos que só têm reembolso, nota ou presente 3D.

**Rodada em 30/09: zero eventos passados fora do Google** (380 conferidos) — a primeira rodada do
"Limpar eventos fantasma" não marca nada. O resultado está em `research.md` (R17). No dia do deploy,
rodar de novo. Se qualquer das três linhas deixar de ser zero (eventos passados com dinheiro fora do
Google; eventos que mudariam de data com elenco de convite aceito; inconclusivos), o deploy sobe do
mesmo jeito — o ciclo automático não percorre mês passado — e o "Limpar eventos fantasma" **não é
rodado** até o dono decidir, com a lista (quantidade, R$, eventos e quantos e-mails de mudança de
data sairiam), entre: (a) rodar com a regra normal — cada evento é marcado e avisa; (b) resolver os
eventos da lista à mão antes de rodar. Esta entrega não tem "primeira rodada sem sino" (R6); se o
dono quiser isso, vira a correção 303b antes da limpeza. Os três números vão para a entrada da 303
no `docs/03`.

Depois do refresh, a migration local some: rode o passo 2 de novo.

## 2. Migration

```powershell
.venv\Scripts\flask.exe db upgrade
.venv\Scripts\python.exe seed.py
```

Esperado: head `a7c3e91f4d28`; `calendar_events.google_missing_since` existe e está nula em todos os
eventos; nenhum evento muda de comportamento.

## 3. Verify

```powershell
.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\verify_303.py            # o portão: tudo
.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\verify_303.py --ate B1   # por história
```

| Bloco | História | Cenários |
|---|---|---|
| B0 | chão | 0, 18 |
| B1 | 1 — o evento com dinheiro fica | 1, 1b, 2, 2b, 3, 4, 5, 6, 7, 7a, 7b, 13, 13b, 13c, 14, 15 |
| B2 | 5 — mudou de data não é sumiço | 8, 9, 13d |
| B3 | 2 — a faixa | 17 |
| B4 | 3 — devolver ao Google | 10, 10a a 10i, 11, 12 |
| B5 | 6 — portal | 24, 24b |
| B9 | limpeza | 41 |

- **Antes do núcleo** (primeira execução, gravada em `verify_303_primeira_falha.txt`): só podem estar
  verdes o chão (0 e 41), o 18 (a trava nasce no Setup), o 15, o sub-cenário "a lista inteira falha"
  do 13 e, do 7, só a afirmação de que o evento vazio é apagado (a auditoria com a resposta do
  Google e o retrato é vermelha). O 11 nasce vermelho inteiro (a rota ainda não existe). Qualquer
  outro verde é defeito do verify.
- Cenário que depende de evento marcado aparece como **BLOQUEADO** enquanto a História 1 não existe —
  não como falha de sintoma.
- O portão é a execução **sem argumentos**, terminando em `N/N OK` e com o último cenário afirmando
  que nenhuma chamada de rede escapou do dublê.

Depois da História 1, rodar o verify da Loja Virtual:

```powershell
.venv\Scripts\python.exe specs\205-loja-interacoes-virtuais\verify_205.py
```

Esperado: V7.1 e V7.2 verdes, nenhum id virtual entre os ids consultados (o espião da consulta é o
que prova), e a contagem de eventos não virtuais do mês igual antes e depois.

Os verifies antigos de `scripts/db/` **não** são rodados sem ajuste depois da 303: o
`verify_151_excluir_sync.py` consultaria o Google real com o token do espelho (research §Dívida).

## 4. Telas (skill `manto-conferir-tela`)

Com eventos marcados no `manto_local` — semeados em meses isolados (os passados em `MES_PASSADO`) e
marcados pelo próprio sync ou pela limpeza, com o dublê do Google; nunca marcar evento real do
espelho:

```powershell
.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\verify_303.py --semear-tela   # imprime os ids; não limpa
# … subir o backend local (manto-backend-local) e os Vite, conferir as telas …
.venv\Scripts\python.exe specs\303-sync-nao-apaga-venda\verify_303.py --limpar-tela   # com o backend parado
```

Os eventos semeados têm id falso no Google: o "Sincronizar" responde que o evento não está mais no
Google Agenda e a devolução responde a mensagem da trava. O "Limpar eventos fantasma" e o
"Sincronizar agora" leem o Google real mesmo no ambiente local (nada é escrito lá): só confirmar a
limpeza no item 8, por último, sabendo que o espelho será sincronizado com a agenda de verdade.

1. **Faixa** — como Superadmin e como Comercial: em duas telas quaisquer, no topo; continua visível
   ao rolar e depois de navegar a partir de uma página rolada. Como Figurino: ausente, e um único GET
   de `/api/events/sumidos-google` na aba de rede. Em 375×812: logo abaixo da barra do app, sem
   rolagem horizontal; o painel do sino cobre a faixa, não o contrário.
2. **Dois eventos marcados** — "2 eventos sumiram do Google Agenda"; a lista abre sobre o conteúdo
   sem empurrá-lo; cada linha leva ao evento certo; Esc fecha e o foco volta ao botão. Em 375×812:
   a frase inteira numa linha; a lista aberta ocupa a largura da tela, com o título cortado e a data
   inteira.
3. **Evento marcado, Superadmin** — o banner com a data em que o sistema percebeu, a frase de que a
   edição só vai ao Google na devolução, o quadro do que está em jogo (comissão dita como estimativa
   quando for), o botão "Devolver ao Google Agenda", a frase do cancelamento que chega depois e o
   texto "recriado à mão" recolhido. A régua de abas fica inteira e clicável logo abaixo da faixa.
   "Editar no Google Agenda" ausente; "Sincronizar" presente e respondendo que o evento não está no
   Google; "Excluir ou cancelar" desabilitado com o motivo. Com exclusão solicitada no mesmo evento:
   dois banners, "Analisar e decidir" desabilitado, "Recusar solicitação" funcionando. Conferir
   também em 375×812, sem rolagem horizontal. Num satélite marcado: a frase da venda do grupo com o
   link, e o botão de devolver presente.
4. **Diálogo de devolver** — mostra o título e a data que vão ao Google (dia inteiro como "(dia
   inteiro)", nunca "00:00 — 00:00"); com data passada, o aviso. Confirmar no ambiente local mostra,
   **dentro do diálogo**, a mensagem da trava ("Este ambiente não escreve no Google Agenda. Nada foi
   alterado."); o diálogo continua aberto e não fecha com Esc durante a ação.
5. **Evento marcado, Comercial** — a marca, a frase da edição e a frase "a decisão é do Superadmin",
   sem botão; "Solicitar exclusão" continua disponível. Como Figurino: só a parte comum. Conferir
   também em 375×812.
6. **Agenda** — o selo "Sumiu do Google" em Lista, Dia e no resultado da busca, e o ícone no chip do
   Mês, com a cor da categoria preservada.
7. **Sino** — o aviso urgente, com título, data, venda, recebido e escalados; some da contagem de
   não lidas quando o evento é resolvido (provado no verify, 9 e 10; no local nada retira a marca
   dos semeados). No painel do sino, em 375 px, o nome do evento e o
   "recebido" aparecem sem abrir o aviso.
8. **`/admin/sync`** — a confirmação do "Limpar eventos fantasma" (um diálogo do sistema, não o do
   navegador) e a mensagem do resultado dizem removidos, mantidos e marcados, com data atualizada,
   de volta ao Google, sem confirmação e com falha, com uma linha por mês que teve algo. Se a tela
   disser "Não foi possível concluir a ação", conferir em `/admin/logs` o que a limpeza fez antes de
   rodar de novo.
9. **Portal** em 375×812 e em 320 px — o aviso "Evento em confirmação — entre em contato com a
   produção" na Agenda, em Convites e no Histórico, como primeira caixa depois do cabeçalho do
   cartão (em Convites, antes do cachê e dos botões), quebrando linha sem rolagem horizontal;
   "Aceitar" e "Recusar" continuam no convite; a palavra "Google" não aparece.
10. Movimento reduzido emulado: a faixa aparece e some sem transição.

## 5. Portões antes do merge

```powershell
cd frontend; npm run typecheck; cd ..
.venv\Scripts\ruff.exe check app\calendar app\api app\notificacoes app\talent_portal app\config.py app\models.py app\constants.py
```

`ruff format` só em `app/calendar/sumico_ops.py`, na migration e no verify (arquivos novos). O
portão do `ruff check` é **nenhum erro novo**: `app/calendar/routes.py` já carrega erros antigos
(`docs/05`, item 55) que não são limpos de passagem — comparar com a saída da `main`.

## 6. Deploy e o teste que só a produção permite

Deploy à noite, num push só: o `render.yaml` redeploya backend e frontend no mesmo push
(`autoDeploy: true` nos dois) e a ordem entre eles não é garantida — por isso todo campo novo é
opcional, e a janela é a de research §Riscos (por minutos, bundle novo com backend antigo não mostra
a faixa; backend novo com bundle antigo mostra o evento marcado como comum). Depois do push, conferir
a produção por `GET /api/events/sumidos-google` devolvendo JSON: 401 sem sessão é o backend novo;
404 ainda é o antigo. Com sessão de Superadmin, `pode_ver: true` — a produção nasce com a trava de
escrita desligada, sem variável nova no painel (o passo 3 abaixo é a prova).

O "Devolver ao Google" **não pode** ser exercitado contra o Google real antes da produção (a trava
impede). Logo depois do deploy, com o dono:

1. Criar no sistema um evento descartável num mês vazio, com um valor de venda simbólico.
2. Apagá-lo no Google Agenda e esperar o ciclo (até 10 minutos): o evento continua, marcado; a faixa
   e o sino acendem.
3. Devolver ao Google pela tela: o evento reaparece na Agenda, com id novo; a marca e a faixa somem.
4. Esperar mais um ciclo: **um** evento só no sistema e na Agenda (sem duplicata).
5. Apagar o evento descartável pelo sistema (tirando a venda antes).

Se o passo 3 falhar, a marca continua e nada se perde — mas o evento de teste segue marcado, com a
faixa acesa para Superadmin e Comercial, e não pode ser excluído (FR-045). Saída sem código novo:
restaurar o evento na lixeira do Google Agenda (o mesmo id volta e o ciclo seguinte tira a marca) e
então excluí-lo pelo sistema.

## 7. Se precisar voltar atrás

`git revert` do merge: a migration é aditiva e nullable, então o código antigo lê e grava no banco
migrado sem downgrade. Eventos marcados nesse meio-tempo voltam a ser tratados como comuns — e, como
não estão no Google, **seriam apagados pela limpeza antiga** no ciclo seguinte. Antes de reverter:
(1) listar os marcados (`SELECT id, title, start_at FROM calendar_events WHERE google_missing_since
IS NOT NULL AND cancelled_at IS NULL`); (2) devolver **todos** ao Google, inclusive os que foram
cancelados de verdade — eles voltam à Agenda e ficam lá; o que fazer com eles depois do revert é
decisão do dono na hora. Anotar a lista não preserva nada: o primeiro ciclo depois do revert (em até
10 minutos) apaga o evento com comprovantes, contrato e escala. Só reverter com a faixa vazia.

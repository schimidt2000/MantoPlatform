# Quickstart — validação da Feature 301

**Spec**: [spec.md](./spec.md) · **Plano**: [plan.md](./plan.md) · **Contrato**:
[contracts/api-endpoints.md](./contracts/api-endpoints.md) · **Data**: 2026-09-21

Guia para **provar que a feature funciona**, não para implementá-la. O que fazer em cada arquivo
está no `tasks.md`.

---

## Pré-requisitos

| | |
|---|---|
| Banco | `manto_local` (espelho da produção) de pé em `localhost:5432`; URL em `.local-db-url` |
| Python | `.venv` do repositório |
| Node | `frontend/` com dependências instaladas |
| Migration | **nenhuma a aplicar** — a feature não muda o banco |
| Env nova | **nenhuma** — nada a preencher no painel do Render |

Três variáveis valem para **todo** comando Python deste guia. Sem elas o script escreve em
serviços reais (o espelho traz token do Google e credenciais de e-mail) e sobem threads de fundo:

```powershell
$env:DATABASE_URL = (Get-Content .local-db-url -Raw).Trim(); $env:FLASK_ENV = 'development'; $env:MANTO_SEM_THREADS = '1'
```

---

## 1. O verify (a prova principal)

```powershell
.venv\Scripts\python.exe specs\301-orcamentos-visiveis-comercial\verify_301.py
```

**Esperado ao fim da implementação**: `13/13 OK`, código de retorno 0.

**Esperado ANTES da implementação** (Princípio VIII): falha — e **pelos motivos certos**. Os
cenários 1–7 devem falhar por dono (403/404/lista vazia), não por `ImportError`, credencial errada
ou endereço inválido. Se falharem por outra coisa, o verify está errado, não o código.

Os 13 cenários estão tabelados na spec (§Verificação). Três usuários descartáveis: **A** (COMERCIAL,
autor), **B** (COMERCIAL, quem prova a feature), **F** (FINANCEIRO, prova que o portão não mudou).
Cinco cenários **devem falhar**: 8 (trocar/soltar alheio), 9 (re-aplicar alheio), 10 (DELETE
alheio — com o contraste de A apagando o mesmo), 11 (FINANCEIRO listando) e 12 (FINANCEIRO
tentando vincular orçamento alheio).

### Os dois pontos onde este verify passa verde sem testar nada

São os únicos lugares em que um verify desta feature engana. Ambos já estão marcados na tabela de
cenários da spec; aqui está o porquê:

1. **Cenário 5 (auditoria do reenvio)** — `audit()` só faz `db.session.add`
   (`app/utils.py:46`), e o endpoint de e-mail **não commita hoje**. Conferir a linha pela sessão
   do app encontra o registro no autoflush e dá verde mesmo sem commit; em produção o registro
   nunca nasce. **Confira por conexão separada.** É literalmente o defeito do hotfix 257.
2. **Cenários 7 e 9 (vínculo e valores do evento)** — mesma armadilha:
   `set_event_orcamento` não comita, quem comita é a view. Ler `event.orcamento_history_id`,
   `sale_value` e `sale_date` pela sessão do app não prova persistência. **Conexão separada.**

Outras armadilhas do esqueleto (login só por `POST /api/auth/login`, requisições HTTP **fora** de
`app.app_context()`, `roles.clear()` antes de apagar usuário) estão em `DEVELOPMENT.md`
§"Escrever um verify" e na skill `manto-verify`.

### Estado conhecido do espelho

A senha do SUPERADMIN local **muda a cada verify** (eles chamam `set_password`) — redefina, não
peça. Se alguma conta de distância der 400 "Endereço não encontrado", é lixo de verify antigo em
`SiteSetting.manto_address`, não defeito desta feature (ela não toca em Maps).

---

## 2. Tipos do frontend

```bash
cd frontend && npm run typecheck
```

**Esperado**: limpo nas três SPAs. Esta feature **remove** uma chave do payload
(`is_superadmin` de `OrcamentoHistoricoResponse`) — o typecheck é quem prova que nenhum consumidor
ficou para trás. Se acusar erro em `OrcamentoPicker.tsx`, é sinal certo: ele compartilha o tipo e
precisa da linha do vendedor (R6).

---

## 3. Tela aberta (portão da constituição)

`tsc` limpo não prova tela. Abrir no Browser pane, **logado como B — COMERCIAL, não superadmin**
(a tela do superadmin já funcionava e não prova nada). Telas internas de staff: sem exigência de
viewport mobile.

### 3.1 `/orcamento/historico`

| Conferir | Esperado |
|---|---|
| Linhas | aparecem orçamentos de **outras pessoas**, não só os de B |
| Coluna "Vendedor" | presente e preenchida (hoje só o superadmin vê) |
| Seletor de vendedor | presente, com os nomes; filtrar por um colega separa certo |
| Escopo inicial | a lista abre com **o time inteiro**, sem filtro pré-aplicado (FR-012) |
| "Ver" na linha de um colega | abre o detalhe congelado, sem "Orçamento não encontrado" |
| "Recalcular" na linha de um colega | a calculadora abre repopulada |
| "Baixar PDF" / "Enviar por e-mail" | concluem |
| **"Excluir" na linha de um colega** | **não aparece**; na linha do próprio B, aparece |

### 3.2 Um evento vendido por outra pessoa

| Conferir | Esperado |
|---|---|
| Aba Comercial | mostra os chips do que o orçamento vendeu e "Abrir orçamento" |
| Nome do vendedor | visível — é ele que a recusa vai citar |
| "Aplicar ao evento" / "Trocar" / "Desvincular" | **não oferecidos** (o orçamento é de outra pessoa) |
| Aviso no lugar dos botões | diz **de quem é** o orçamento e que só essa pessoa ou o superadmin mexem |

> **O erro que esta conferência caça**: se os três botões aparecerem, a tela ficou deduzindo
> permissão de `!orc && venda.tem_orcamento` em vez de ler `pode_gerir`. Com o payload novo essa
> dedução é sempre `false`, então os botões aparecem e o servidor recusa depois do clique. É o
> defeito mais provável desta feature.

### 3.3 Vincular o orçamento de um colega (FR-011)

Num evento **sem** orçamento, buscar pelo nome do cliente de um orçamento de colega:

| Conferir | Esperado |
|---|---|
| Busca | encontra o orçamento do colega (hoje não encontra) |
| Linha do resultado | mostra **de quem é** |
| Vincular | conclui; o evento recebe o que o orçamento vendeu |
| Depois de vinculado | os botões de gerir **somem** para B — quem manda agora é o autor. Comportamento correto e documentado nos Casos de borda |

---

## 4. Regressões a conferir (o que NÃO pode mudar)

| Conferir | Esperado |
|---|---|
| Usuário **FINANCEIRO** no histórico | continua **403** |
| Usuário FINANCEIRO num evento com orçamento | continua **sem** o bloco do orçamento |
| **EducaManto** (`/educamanto`, histórico) | inalterado — já mostrava tudo para todos |
| `DELETE` de orçamento com evento vivo vinculado, **feito pelo autor** | continua **409** com `event_id` |
| `DELETE` do mesmo orçamento por quem **não** é o autor | **404** — a checagem de autoria vem antes do 409, e continua assim de propósito |
| Um orçamento em dois eventos vivos | continua barrado (`OrcamentoJaVinculado`) |
| Configuração de Preços | continua só do SUPERADMIN |

---

## 5. Antes de chamar de pronto

```bash
ruff check app/api/orcamento_read.py app/api/orcamento_write.py app/api/agenda_read.py app/api/agenda_write.py app/calendar/orcamento_evento_ops.py
```

- [ ] `verify_301.py` → `13/13 OK`
- [ ] `npm run typecheck` limpo
- [ ] `ruff check` limpo nos tocados
- [ ] Telas de §3 conferidas **como COMERCIAL não-superadmin**
- [ ] Regressões de §4 conferidas
- [ ] `docs/01` §3.13 e §4.3, `docs/02` e `docs/03` atualizados (FR-014)
- [ ] `git status --short` limpo

**Deploy**: comum. Não toca `startCommand`, `render.yaml`, volume nem migration; sem backfill e
sem passo manual no Shell do Render. Vale a janela de ~60s de 502 do deploy — push em lote e fora
do horário comercial, como sempre.

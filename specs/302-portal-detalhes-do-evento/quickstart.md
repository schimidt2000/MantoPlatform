# Quickstart — validação da Feature 302

**Spec**: [spec.md](./spec.md) · **Plano**: [plan.md](./plan.md) · **Contrato**:
[contracts/api-endpoints.md](./contracts/api-endpoints.md) · **Data**: 2026-09-22

Guia para **provar que a feature funciona**, não para implementá-la. O que fazer em cada arquivo
está no `tasks.md`.

---

## Pré-requisitos

| | |
|---|---|
| Banco | `manto_local` (espelho da produção) em `localhost:5432`; URL em `.local-db-url` |
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
.venv\Scripts\python.exe specs\302-portal-detalhes-do-evento\verify_302.py
```

**Esperado ao fim da implementação**: `22/22 OK`, código de retorno 0.

**Esperado ANTES da implementação** (Princípio VIII): falha — e **pelos motivos certos**. Os
cenários 1-8b devem falhar por **chave ausente no payload** (`before_event`, `role_type`) ou por
**o código `"manto"` aparecer cru no JSON**. Se falharem por `ImportError`, credencial errada ou
endereço inválido, o verify está errado, não o código.

Os cenários estão tabelados na spec (§Verificação). Dois talentos descartáveis: **T** (o que prova
a feature) e **U** (o que prova que não vê nada de T). Um usuário de staff descartável para o
cenário 13. Três cenários **devem falhar**: 9 (T não vê nada de U), 9b (sem sessão nenhuma) e 10
(figurino de evento alheio).

### Os três pontos em que este verify passa verde sem testar nada

1. **Cenário 13 escreve.** `save_logistics` comita, mas conferir pela sessão do app encontra o
   valor no autoflush mesmo se o commit sumir numa refatoração. **Conexão separada** — é
   literalmente o defeito do hotfix 257.
2. **O arranjo é o que dá sentido a tudo.** Um verify que só faça `GET /api/portal/agenda` e
   cheque a presença das chaves passa verde num talento sem ensaio e sem logística — que é **todo
   mundo hoje** (zero eventos futuros com maquiagem). O cenário precisa **assumir uma role
   existente** com `talent_id IS NULL` e **criar** ensaio e logística.
3. **Cenário 3 precisa dos dois ensaios semeados.** O espelho tem um caso real de show com dois,
   mas é **um só** — depender dele é depender de uma linha de produção que pode sumir. Sem semear,
   a asserção "traz os dois" passa com um item e não prova nada.

### Duas armadilhas que sujam serviços reais

- **Semear ensaio pelo endpoint cria evento no Google Agenda da empresa.**
  `POST /api/events/<id>/ensaios` chama `insert_event`; as travas `_suppress_*` cobrem e-mail e
  convite, **não** isso. Insira o `CalendarEvent` filho direto no banco, com `google_event_id`
  descartável.
- **Nunca criar `EventRole` com `character_name` inventado**: o sync do Google apaga a role e
  dispara e-mail de remoção para gente de verdade. Assuma role existente com `talent_id IS NULL` e
  devolva `talent_id = None` na limpeza.

### Estado conhecido do espelho

Restaure no `finally` os campos de logística dos eventos que o verify tocar — eles são eventos
reais do espelho, não descartáveis. A senha do SUPERADMIN local muda a cada verify; redefina, não
peça.

---

## 2. Tipos do frontend

```bash
cd frontend && npm run typecheck
```

**Esperado**: limpo nas três SPAs. Esta feature **não remove** nenhuma chave de payload, então o
typecheck aqui é rede de segurança, não prova. Dois pontos onde ele acusa de propósito:

- `PortalHistoricoItem extends PortalRole` — as chaves novas chegam ao histórico sozinhas;
- **o `tsc` não vai te ajudar aqui**: remover só a seção não orfana import nenhum, porque o card
  continua referenciando `RatingLink`, `CacheLine` e `formatRelativeDay` pelos dois ramos da prop
  que distingue futuro de passado. Os imports só ficam órfãos depois que os ramos mortos saírem —
  e a prop em si, sempre verdadeira, o `noUnusedLocals` nunca acusa. É leitura humana.

---

## 3. Telas abertas (portão da constituição)

`tsc` limpo não prova card. Abrir no Browser pane, **em viewport mobile 375×812**, logado como um
talento que tenha um evento futuro **com ensaio** (semeie um, como o verify faz, e desfaça depois).

### 3.1 `/portal/agenda`

| Conferir | Esperado |
|---|---|
| Linha principal | `sexta-feira, 3 de out, 16:00 às 20:00 · Local` |
| Evento sem horário final | mostra só o início — sem traço nem "às" órfãos |
| Bloco "Antes do evento" | presente e **recolhido**; abre com um toque; alvo ≥44px |
| Dentro do bloco | ensaio com data, hora e endereço; maquiagem e saída quando houver |
| Evento sem nada | **não existe bloco** — o card fica do tamanho de hoje |
| Rótulo | `Função: Coordenador` na vaga de cargo, `Personagem: X` na de personagem |
| **Seção HISTÓRICO** | **não existe mais** |
| Barra inferior | o contador de "eventos a avaliar" continua aceso na aba Histórico |
| 320px a 430px | sem rolagem horizontal, nada abaixo de 12px |

### 3.2 `/portal/convites`

| Conferir | Esperado |
|---|---|
| Bloco "Antes do evento" | **presente** — é onde a informação muda a decisão (FR-009a) |
| Faixa horária e rótulo | iguais aos da Agenda |

> **O erro que esta conferência caça**: se o bloco aparecer na Agenda e não nos Convites, o
> componente foi colado só numa tela em vez de virar peça compartilhada — o mesmo desvio que fez o
> cachê sumir dos convites antes da feature 230.

### 3.3 `/portal/historico`

| Conferir | Esperado |
|---|---|
| Lista | todas as apresentações passadas, com os totais |
| Rótulo | `Função:` para cargo |
| Bloco | **ausente** — preparação não se aplica ao que já passou |
| Link de avaliar | continua em cada linha |

### 3.4 `/portal/eventos/:id/figurino`

| Conferir | Esperado |
|---|---|
| Topo | nome do evento e **data por extenso** — hoje a ficha abre sem nenhuma referência |
| Hora | **não aparece**: FR-014 pede nome e data. A hora está no card de onde a pessoa veio |

### 3.5 Tela interna do evento

| Conferir | Esperado |
|---|---|
| Evento futuro, com elenco, sem logística | chip **Logística** na faixa de pendências, em estado de pendência, levando à aba Produção |
| Seção "Logística & trajeto" | alerta em linha explicando que o elenco está escalado e os horários não foram definidos |
| Depois de salvar a logística | chip e alerta somem |
| Evento futuro **sem** elenco | sem chip |
| Evento passado | sem chip |
| Quem não pode editar o evento | sem chip — não se cobra de quem não pode resolver |
| "Copiar convite" de um Coordenador | a mensagem diz `Função: Coordenador` e, se houver maquiagem, `Local: Manto Produções` — nunca `manto` |

---

## 4. Regressões a conferir (o que NÃO pode mudar)

| Conferir | Esperado |
|---|---|
| `GET /api/portal/agenda` | **continua** trazendo a lista de passados no payload (FR-013a) — abrir o JSON e confirmar |
| Contador de convites pendentes | inalterado |
| Cachê, deslocamento e "a combinar com a produção" | inalterados nas três telas |
| Aviso de alteração + botão **Ciente** | continua funcionando |
| `Ver ficha de figurino` | continua só quando há ficha |
| Coordenador na ficha de figurino | continua vendo o elenco inteiro |
| Evento cancelado | continua fora do portal |
| Escalação recusada | continua fora |
| Rotas Flask do portal | só `/portal/photo` existe (as 20 rotas Jinja saíram na fase 2 da remoção do Jinja) — nada a conferir aqui, e nada a criar |

---

## 5. Antes de chamar de pronto

```bash
ruff check app/talent_portal/portal_ops.py app/calendar/event_ops.py app/email_service.py app/api/portal_figurino.py app/constants.py
```

- [ ] `verify_302.py` → `22/22 OK`
- [ ] `npm run typecheck` limpo
- [ ] `ruff check` limpo nos tocados
- [ ] Telas de §3 conferidas **em viewport mobile**
- [ ] Regressões de §4 conferidas
- [ ] `docs/01`, `docs/02`, `docs/03` e `docs/05` atualizados
- [ ] `git status --short` limpo

**Deploy**: comum. Não toca `startCommand`, `render.yaml`, volume nem migration; sem backfill e
sem passo manual no Shell do Render. Vale a janela de ~60s de 502 — push em lote e fora do horário
comercial.

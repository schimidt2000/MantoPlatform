# Remoção do Jinja legado — ONDE PARAMOS e por quê

**Trabalho pausado por decisão do João em 20/08/2026.** Não é abandono nem bloqueio técnico: é
uma decisão de risco/benefício, explicada abaixo. Leia isto antes de retomar.

---

## Em uma frase

**A parte que valia a pena está feita e em produção.** O que sobrou é dívida arrumada, não ferida
aberta — e para removê-la seria preciso mexer no código que calcula cachê de artista e comissão de
vendedor, que é risco sem urgência.

---

## O que foi feito (45 commits, tudo em `main` e no GitHub)

| Fase | O que era | Estado |
| --- | --- | --- |
| 1 | Órfãos e código morto | ✅ produção |
| 2 | Portal do Artista Jinja (20 rotas, 12 templates) | ✅ produção |
| 3 | Onze blueprints substituídos pelo React | ✅ produção |
| 5 | `/avaliar` — o link da cliente | ✅ produção |
| 6 | `calendar` + `financeiro` | ⏸️ **pausada — os 5 pré-requisitos foram feitos, a remoção não** |
| 7 | `auth` e fechamento | ⬜ não iniciada |

**Saldo:** ~19.000 linhas de Jinja removidas. Templates: 84 → 17 arquivos. Rotas Flask: 530 → 382.

### O que ainda é Jinja hoje

`calendar` (agenda, eventos, ensaios, cargos), `financeiro` (+ `/vendas/`) e `auth` (login,
perfil, troca de senha). **Nenhum deles é alcançável pela porta pública** — `frontend/server.js`
só repassa dez prefixos ao Flask. Eles respondem apenas pelo domínio direto do serviço backend,
que não é divulgado.

---

## Defeitos REAIS corrigidos no caminho

Estes não são limpeza. Se um dia alguém reverter a remoção, **reverter estes junto seria um
retrocesso**:

| Commit | O que estava quebrado |
| --- | --- |
| `d4d16cc` | **O link de avaliação que as clientes recebem caía na página Jinja antiga**, embora a página React existisse e funcionasse. Os tokens nunca expiram. |
| `a58f54b` | **Dava para gravar venda num evento satélite** pela API — o valor entrava no banco e sumia de todos os relatórios, porque o financeiro pula satélites de propósito. |
| `a58f54b` | **Não dava para cancelar um evento principal** pela interface nova: a tela mandava desagrupar antes, e desagrupar não existia lá. Beco sem saída. |
| `a01ab48` | **Editar a venda pela tela nova não sincronizava a comissão.** O gêmeo Jinja sincronizava — a mesma edição dava resultado diferente conforme a tela. |
| `16f6f1a` | Um painel derrubava a **página inteira do evento** (tela branca) quando um campo novo não vinha do servidor — o que acontece em toda janela de deploy. |

Também foi **construída** a feature de agrupar/desagrupar evento (`246`/`247`), que o João
classificou como importantíssima e que não existia na plataforma nova.

---

## Por que paramos

O que resta da Fase 6 **não é apagar views**. A medição mostrou que
`app/calendar/routes.py` **exporta 47 símbolos distintos, em 86 pontos de import, para 13 módulos
vivos** e 15 scripts. Aquele arquivo virou uma **biblioteca compartilhada com views penduradas**.

E dois dos símbolos a extrair são:

- `_compute_performer_caches` — calcula **o cachê de cada artista**. Um arredondamento aplicado
  por parcela em vez de na soma muda o valor em até R$ 1 por pessoa, em silêncio.
- `_create_event_row` — grava `sale_value` e calcula acréscimo percentual.

**A conta não fecha:** o ganho de apagar aquelas views é arrumação; o risco é mexer em dinheiro,
sem prazo e sem ninguém pedindo.

---

## Se um dia fizer sentido retomar

O gatilho natural **não é "está sujo"** — é alguém precisar mexer no `calendar` por outro motivo.
Aí a extração paga o próprio custo.

O plano completo está em **[`PLANO_EXTRACAO_CALENDAR.md`](PLANO_EXTRACAO_CALENDAR.md)**: quatro
cortes em ordem de risco crescente, as cinco injeções obrigatórias (uma delas evita um ciclo de
import que trava o boot), as armadilhas já mapeadas e o protocolo de verificação.

**A regra que este trabalho todo ensinou**, e que vale para qualquer remoção neste repositório:

> Antes de apagar qualquer blueprint, rodar
> `grep -rn "from app\.<nome>\.routes import"` no repositório **inteiro, `scripts/` incluído**.
> Foi assim que se descobriu que cinco módulos vivos importavam lógica de negócio de dentro do
> Jinja — inclusive o que serve o formulário público que as clientes preenchem.

E, para código que mexe em dinheiro: comparar o resultado para os **450 eventos** do espelho entre
um worktree do `main` e o branch, item a item. Nem o `ruff` nem o `create_app()` pegam mudança de
número. Foi assim que a régua de comissão foi extraída com zero divergência (`1343939`).

---

## Ferramentas que ficaram

Vivem em `scripts/db/` (pasta gitignorada, então só existem nesta máquina):

| Script | Para quê |
| --- | --- |
| `check_url_for_orfaos.py` | Detector estático de `BuildError`: varre os templates e confere cada `url_for` contra o `url_map` real. **Rodar depois de qualquer remoção.** |
| `verify_241_avaliar_react.py` | O link da cliente continua abrindo o React |
| `verify_246_grupos_api.py` | Agrupar/desagrupar, e os 5 grupos reais intactos |
| `verify_249_comercial_ops.py` | As 4 regras das coleções comerciais (inclui: BV pago não pode "despagar") |
| `verify_251_acrescimos_parcelas_api.py` | Acréscimos, parcelas e CRUD de nota fiscal |
| `verify_206_react_primario.py` | O guardião pré-existente: 301 da raiz e as rotas de arquivo |

---

## Pendências que são decisão do dono (nada foi tocado)

1. **3 eventos com venda e sem linha de comissão** — ids `69` (R$ 4.180), `62` (R$ 6.800) e `203`
   (R$ 1.375), todos sem `sale_date`. Depois do commit `a01ab48`, abrir cada um e salvar a aba
   Comercial faz a linha nascer.
2. **Comissão órfã do evento 287** — R$ 137,50 marcados como *pagos* num evento que virou satélite
   e teve a venda zerada. Comissão paga é dinheiro que saiu: só um humano decide se vira estorno.
3. **Nota fiscal** tem CRUD na API (`252`) mas o painel do `FinanceiroSection` ainda não usa.
4. **`Produtos Catalogo/`** e o CSV do Kommo seguem na raiz — o botão de reimportar o catálogo é
   um no-op (o importador pula tudo que já está no banco e o CSV é um export congelado).

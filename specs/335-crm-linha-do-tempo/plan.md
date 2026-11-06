<!-- ADAPTADO PARA A MANTO (2026-09-08) — reaplicar após qualquer atualização do Spec Kit; para este
     arquivo o hash em .specify/integrations/speckit.manifest.json deixa de conferir de propósito. -->
# Plano de implementação: 335 — Linha do tempo da ficha e funil das conversas

**Branch**: `335-crm-linha-do-tempo` (sobre a `334-crm-origem-do-anuncio`) | **Data**: 2026-11-06 | **Spec**:
[spec.md](./spec.md)

## Resumo

Tudo derivado do que já existe, sem tabela nova.
- **Linha do tempo**: um endpoint de leitura monta os marcos da ficha (entrada, primeiro contato de cada conversa,
  anúncios, orçamentos enviados, formulários, eventos, pagamentos, avaliações) e a ficha ganha o cartão.
- **Funil**: um núcleo calcula, para as conversas cujo primeiro contato caiu no período, a etapa mais avançada de cada
  uma (Chegou → Orçamento enviado → Formulário → Evento fechado → Pagou → Avaliou), com filtros de canal e campanha, a
  divisão por vendedor, campanha ou canal e a lista de quem parou em cada etapa. Tela nova "Funil" no Comercial.

## Contexto técnico

**Linguagem/Versão**: Python 3.11 (Flask + SQLAlchemy); TypeScript + React 18 (Vite).

**Dependências principais**: as da casa; nenhuma nova.

**Armazenamento**: PostgreSQL. Nenhuma migration ([data-model.md](data-model.md)).

**Verificação**: `verify_335.py` (molde do `verify_334`); 325, 328, 330, 332, 333 e 334 como regressão; `npm run
typecheck`; tela pela worktree em desktop e 375×812.

**Restrições**: só leitura; fusos misturados nas fontes (UTC e São Paulo) normalizados na saída; a base fora da `main`.

**Escala/escopo**: 3 endpoints novos (linha do tempo, funil, parados); 2 núcleos novos (`linha_do_tempo_ops`,
`funil_ops`); 1 tela nova (Funil) e 1 cartão novo (ficha). Um trimestre tem cerca de 2.000 conversas: o funil faz um
punhado de consultas em lote, nunca uma por conversa.

## Constitution Check

| Princípio / seção | Como o plano cumpre |
|---|---|
| I. Reutilizar antes de criar | O primeiro contato e a campanha vêm das tabelas da 325/334; os eventos da ficha seguem a regra do `get_client_detail` (vivos, via `EventClient`); o grupo de eventos segue o `group_leader_id` (137). Nenhuma tabela de funil (lição da 021). |
| II. Padrões de código | Type hints, docstrings, constantes (rótulos das etapas e dos marcos) em `app/conversas/constantes.py`; `ruff check` nos tocados. |
| III. Camadas / API First | `app/conversas/funil_ops.py` e `app/clientes/linha_do_tempo_ops.py` sem `request`; os endpoints validam, chamam e serializam. |
| IV. Não quebrar | Só leitura e telas novas; a ficha ganha um cartão. Verifies anteriores como regressão. |
| V. UI/UX com feedback | Carregando, vazio e erro em cada bloco; período padrão o mês corrente; a etapa tocada fica marcada. |
| VI/VIII | Esteira completa; verify antes do núcleo, com 2 cenários que devem falhar (RBAC e período inválido). |
| XIII. RBAC | Funil e parados: `pode_conversas` (Comercial/Superadmin, papel real). Linha do tempo: `_require_vendas` da ficha (Comercial, Financeiro, Superadmin); os links de conversa e de orçamento só para quem abre essas telas. |
| XIV. Config / efeito externo | Nenhum: só leitura, sem chamada externa. |
| XV. Texto por superfície | Interno operacional: "Funil", "Chegou", "Orçamento enviado", "Pararam em …", "Linha do tempo", "Primeiro contato pelo WhatsApp". |
| Stack | Sem migration; sem dependência. |

**Resultado**: ✅ sem violação.

## Estrutura

```text
app/conversas/funil_ops.py                         # coorte do período, etapa mais avançada, divisão, parados
app/conversas/constantes.py                        # etapas e rótulos, limites
app/clientes/linha_do_tempo_ops.py                 # os marcos da ficha
app/api/conversas_funil.py                         # GET /api/conversas/funil e /api/conversas/funil/parados
app/api/__init__.py                                # registra o módulo novo
app/api/clientes_read.py                           # GET /api/clientes/<id>/linha-do-tempo
frontend/apps/internal/src/lib/funil.ts            # tipos e hooks do funil
frontend/apps/internal/src/lib/clientes.ts         # tipos e hook da linha do tempo
frontend/apps/internal/src/pages/FunilPage.tsx     # a tela
frontend/apps/internal/src/components/LinhaDoTempoDaFicha.tsx
frontend/apps/internal/src/pages/ClientDetailPage.tsx   # o cartão
frontend/apps/internal/src/App.tsx, lib/navigation.tsx  # rota /funil e item "Funil" no Comercial
specs/335-crm-linha-do-tempo/verify_335.py
```

**Reavaliação pós-design**: ✅.

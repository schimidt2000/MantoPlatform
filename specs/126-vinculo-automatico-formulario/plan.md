# Implementation Plan: Vínculo Automático de Formulário a Evento da Agenda (126)

**Branch**: `126-vinculo-automatico-formulario` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

## Summary

`FormResponse.event_id` hoje só é preenchido num único lugar (`/events/new`, quando
alguém cria o evento escolhendo a resposta na busca). Não existe caminho para o caso
mais comum relatado: o evento já existe na agenda ANTES da resposta chegar. Esta feature
adiciona um motor de casamento automático (`_attempt_auto_link`, em
`app/formularios/routes.py`) chamado em três momentos — no envio do formulário, no ciclo
de sincronização da agenda (cobre evento criado depois) e num backfill único — mais um
caminho manual completo (associar/desassociar evento numa resposta, com aviso de revisão
quando a automação não tem certeza), reaproveitando o endpoint de busca de eventos por
data que já existe em `/gastos/api/eventos`.

## Technical Context

**Stack**: o existente (Flask + SQLAlchemy; Jinja2 + JS vanilla para o picker).
**Storage**: PostgreSQL — 3 colunas novas em `form_responses`.

**Arquivos**:
- `app/models.py` — `FormResponse` ganha `event_link_source`, `event_link_ambiguous`,
  `event_link_locked`.
- `migrations/versions/<novo>_form_response_event_link.py` — 3 colunas nullable/default.
- `app/formularios/routes.py` — motor de casamento (`_attempt_auto_link`,
  `retry_auto_link_pending`) + rotas `vincular_evento`/`desvincular_evento` (manuais) +
  chamada em `_submit_public_form`.
- `app/calendar/sync.py` — `run_calendar_sync()` chama `retry_auto_link_pending()` após o
  laço de meses, best-effort (não pode derrubar o ciclo de sync).
- `app/cli.py` — comando `backfill-form-event-links` (rodar uma vez após o deploy —
  FR-007).
- `app/__init__.py` (home) — nova lista `form_responses_precisam_revisao`
  (`event_link_ambiguous=True`), somada ao contador comercial existente.
- `app/templates/home.html` — novo bloco de aviso, mesmo padrão visual do já existente
  "Pré-contrato · sem cliente".
- `app/templates/formularios/detail.html` — painel "Evento": estado atual + badge da
  origem do vínculo (automático por data/cliente/manual) + aviso quando ambíguo +
  buscador manual (reaproveita `/gastos/api/eventos?date=`) + botão desvincular.

**Testing**: verificação funcional contra `manto_local` — cenários de match único,
ambiguidade por 2 eventos no mesmo dia, desempate por cliente, contradição de telefone,
retry após criação tardia do evento, backfill, desvincular + trava contra re-auto-link.

## Motor de casamento — `_attempt_auto_link`

```
1. Já tem evento, ou já foi decidido por um humano (event_link_locked), ou não tem data
   informada → não faz nada (None).
2. Busca eventos "reais" (não ensaio — título não começa com "🟧 ENSAIO", não satélite —
   group_leader_id nulo) na data exata da resposta.
3. Exatamente 1 candidato:
   - Se esse evento já tem cliente(s) associado(s) E a resposta tem telefone E nenhum
     bate → "ambiguous" (contradição, não força).
   - Senão → vincula, source="auto_date".
4. Mais de 1 candidato:
   - Telefone da resposta bate com um cliente já associado a exatamente 1 dos
     candidatos → vincula a esse, source="auto_client".
   - Senão (0 ou >1 batem) → "ambiguous".
5. 0 candidatos na data:
   - Telefone da resposta bate com um cliente que tem exatamente 1 evento real futuro
     associado (qualquer data) → vincula, source="auto_client".
   - Mais de 1 evento futuro desse cliente → "ambiguous".
   - Nenhum cliente/nenhum evento → None (nada a fazer, sem sinal nenhum).
```

`"ambiguous"` marca `event_link_ambiguous=True` (aparece no aviso da home). Um vínculo
bem-sucedido (por qualquer via) sempre zera `event_link_ambiguous`.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ Busca de eventos por data reaproveita `/gastos/api/eventos` (não duplica endpoint); exclusão de ensaio/satélite usa o mesmo critério já usado no alerta "sem cliente" da home (`exclude_ensaios`, `group_leader_id`); rotas manuais espelham `associar`/`desassociar` já existentes. |
| II. Padrões Python | ✅ Funções pequenas e puras (`_real_event_candidates`, `_client_by_phone`, etc.), type hints, docstrings explicando o critério de decisão. |
| III. Camadas | ✅ Motor de casamento isolado em funções sem HTTP; rotas só chamam e persistem. |
| IV. Não quebrar | ✅ `event_link_locked` garante que uma decisão humana (associar manualmente OU desvincular) nunca é sobrescrita pela automação depois — sem isso, desfazer um vínculo errado (FR-008) seria inútil (o próximo ciclo de sync religaria ao mesmo evento errado). Fluxo manual de criação de evento (`/events/new`) e associação de cliente continuam intocados. |
| V. UI/UX | ✅ Nunca faz um vínculo silencioso arriscado — ambiguidade sempre vira aviso visível e acionável (busca manual disponível na hora); ações destrutivas (desvincular) não são "destrutivas" de dado (não apaga a resposta), mas ainda assim têm confirmação visual clara via flash. |
| VI. Planejar | ✅ Este plano, com o motor de decisão detalhado antes de qualquer código. |
| VII. Moeda BR | N/A. |
| VIII. Mobile-first | N/A — telas internas do painel. |

**Gate: PASS.**

## Decisões

1. **`event_link_locked` como trava permanente pós-decisão humana**: sem essa trava, um
   "desfazer" (FR-008) seria desfeito de novo pelo próximo ciclo de sync automático — a
   automação tem que respeitar quando um humano já decidiu, mesmo que a decisão seja
   "nenhum evento" (não force nunca mais essa resposta específica). Mesmo espírito de
   "automação nunca desliga o que humano ligou" já usado na feature 115.
2. **Contradição de telefone bloqueia o match de data única**: um evento já ter um
   cliente com telefone diferente do da resposta é sinal forte de evento errado — mais
   seguro recusar e pedir revisão do que arriscar (Assumption do spec: "muito robusto" =
   nunca adivinhar diante de sinais conflitantes).
3. **Reaproveitar `/gastos/api/eventos?date=`** para o buscador manual em vez de criar um
   endpoint próprio em `formularios` — mesmo formato de resposta (`[{id, label}]`), zero
   duplicação de query.
4. **Backfill como comando CLI, não dentro da migration**: migrations deste projeto são
   só schema (regra do CLAUDE.md); lógica de negócio (joins com `EventClient`, etc.) fica
   fora do Alembic, num comando `flask` explícito, no mesmo padrão de
   `import-kommo-clients`/`migrate-drive-to-volume` já existentes.

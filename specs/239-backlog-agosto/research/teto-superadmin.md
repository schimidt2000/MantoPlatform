# Limite do cache visivel para superadmin com explicacao da conta (vinda do orcamento)

## Resumo
Hoje o teto de cachê (`cache_cap`) é calculado do orçamento na criação do evento e gravado no `EventRole`, mas é deliberadamente escondido de todo mundo — inclusive superadmin — no CastingSection.tsx atual; só aparece um aviso textual quando o valor digitado ultrapassa o teto efetivo (feature 238). Não existe hoje nenhum campo/serialização com a "explicação da conta" (de onde veio o número) — a composição (base por duração + adicionais) é calculada em `_compute_performer_caches` mas descartada, só o número final vira `cache_cap`.

## Comportamento atual (evidencia)
`EventRole.cache_cap` (app/models.py:522) é gravado na criação do evento a partir do orçamento vinculado: `app/calendar/routes.py:3438-3454` chama `_compute_performer_caches(snap, horas_extra=...)` sobre o `OrcamentoHistory.form_snapshot`, e `_create_roles_from_input` (routes.py:3251) faz `cap = orc_caches[i].get(chave_cache)` (chave_cache = cache_1h..cache_4h para 1-4h, ou cache_custom para >4h pela régua da feature 236: base de 4h ÷4×horas + adicionais fixos sem escalar). O valor final por papel já soma: preço-base por tipo/subtipo (ator/cantor/especial/coordenador/técnico/maquiador), + adicional noturno (+R$50 se evento ≥19h), + adicional fora-SP (km_ida×2÷divisor), + adicional de show customizado (routes.py:2795-2911). Essa composição é calculada mas NUNCA persistida por componente — só o total final vira `cache_cap`.

O teto é servido ao frontend já hoje: `_serialize_role` em app/api/agenda_read.py:271-274 inclui `cache_cap` (e `cache_value`) sempre que `show_casting` é true (casting ou superadmin, agenda_read.py:146). O flag `is_superadmin` também já é computado e enviado (agenda_read.py:144,151) mas NÃO é passado para `_serialize_role` (call site em agenda_read.py:653) nem usado para decidir o que mostrar do teto.

No frontend, `CastingSection.tsx:156-169` calcula `tetoEfetivo = Math.max(role.cache_cap, role.cache_value ?? 0)` (regra da feature 238) mas por design **nunca renderiza esse número** — o comentário explícito (linhas 155-158) diz "o valor do teto é deliberadamente invisível — o casting não negocia contra um número exposto na tela". Só existe um aviso textual condicional (linhas 260-271): "Cachê autorizado acima do limite" / "Acima do limite... você pode salvar" / "...volta para o limite" — sem nunca citar o valor em R$, para NINGUÉM, nem superadmin.

Curiosidade: a tela Jinja legada (`app/templates/event_detail.html:3159-3200`, endpoint `/events/<id>` em app/calendar/routes.py:1645) FAZ o oposto — mostra o valor do cap em R$ tanto para superadmin quanto para não-superadmin num aviso JS (`⚠ Acima do calculado (R$ X). Autorizado para admin.` vs `⛔ Valor máximo: R$ X`). Essa tela parece legada/paralela à SPA React (que é onde a feature 238 e o CastingSection vivem hoje); não é o alvo natural da mudança pedida, mas é evidência de que expor o número já existiu no produto.

Não existe, em nenhum lugar do banco ou da API, um campo com a "explicação da conta" (breakdown de como o cap foi calculado) — isso teria que ser criado.

## Arquivos relevantes
- app/models.py (508-544 (EventRole), especialmente 522) — cache_cap já existe; precisa de coluna nova (ex.: cache_cap_note Text nullable) para guardar a explicação
- app/calendar/routes.py (2741-2911 (_compute_performer_caches), 3220-3271 (_create_roles_from_input), 3438-3454 (chamada com OrcamentoHistory)) — onde o cap é calculado do orçamento e onde o EventRole nasce; é aqui que a composição (base+adicionais) existe e é descartada — precisa passar a montar e persistir a explicação
- app/calendar/casting_ops.py (66-77 (teto_efetivo = max(cache_cap, old_cache_value))) — regra da feature 238 já calcula o teto efetivo no save; não precisa mudar — a explicação é sobre a origem do cache_cap, não do teto efetivo (que o front já deriva de cache_cap+cache_value)
- app/api/agenda_read.py (144-151 (is_superadmin/flags), 232-275 (_serialize_role), 653 (call site)) — is_superadmin já é calculado e enviado em flags mas não chega em _serialize_role; precisa passar o parâmetro e condicionar a nova serialização (cache_cap_note) a show_casting AND is_superadmin
- frontend/apps/internal/src/lib/agenda.ts (126-131 (tipo do Role)) — tipo TS do papel do elenco — precisa do novo campo opcional cache_cap_note
- frontend/apps/internal/src/components/EventDetail/CastingSection.tsx (140-271 (RoleCard, cálculo de tetoEfetivo, aviso textual)) — componente que hoje esconde deliberadamente o valor do teto; precisa renderizar o teto + explicação só quando data.flags.is_superadmin
- migrations/versions/ (novo arquivo, down_revision = b7e3a91d5c24 (head atual)) — migration para a coluna nova em event_roles
- specs/238-teto-autorizado/spec.md (todo) — spec da feature anterior (teto efetivo) — este item é uma extensão/nova spec, não está coberto por ela

## Abordagem proposta pela investigacao
1. Nova coluna em `EventRole` (app/models.py, perto da linha 522): `cache_cap_note = db.Column(db.Text, nullable=True)` — pequena explicação textual de como o `cache_cap` foi calculado. Migration nova (down_revision = head atual `b7e3a91d5c24`) só com `add_column`.

2. Em `_compute_performer_caches` (app/calendar/routes.py:2741-2911): ao montar cada `item`, além de `cache_1h..cache_4h`/`cache_custom`, montar também uma string curta descrevendo a composição usada para aquele papel — ex. tipo/subtipo (Ator cara-limpa, Cantor, Coordenador, Técnico de Som, Maquiador), a duração/régua aplicada, e quais adicionais entraram (noturno +R$50, fora-SP +R$X, show customizado +R$X, delta de maquiagem na régua >4h). Guardar em `item["cap_note"]`.

3. Em `_create_roles_from_input` (routes.py:3220-3271): junto com `cap = orc_caches[i].get(chave_cache)`, ler `note = orc_caches[i].get("cap_note")` e passar `cache_cap_note=note` ao criar o `EventRole` (linha ~3261-3267). Papéis do fluxo fallback (sem `orcamento_history_id`, `orc_caches` vindo direto do cliente) não têm como decompor a conta — `cap_note` fica `None` nesse caso (ver open question 2).

4. `_serialize_role` (app/api/agenda_read.py:232-275): adicionar parâmetro `is_superadmin: bool`; quando `show_casting and is_superadmin`, incluir `data["cache_cap_note"] = role.cache_cap_note`. Atualizar a chamada (linha 653) para `_serialize_role(r, flags["show_casting"], availability, show_pii, alertas_figurino, is_superadmin=flags["is_superadmin"])`.

5. `frontend/apps/internal/src/lib/agenda.ts` (linha ~130): adicionar `cache_cap_note?: string | null;` ao tipo do papel.

6. `CastingSection.tsx`: quando `data.flags.is_superadmin` for true e `role.cache_cap != null`, mostrar o teto efetivo (`tetoEfetivo`, já calculado na linha 166-167) e, se houver, `role.cache_cap_note`, como uma linha pequena e discreta (texto muted) perto do cachê atual — por exemplo logo abaixo da linha "Cachê: {brl(role.cache_value)}" (linha 203-205). Ajustar/reduzir o comentário de "deliberadamente invisível" (linhas 155-158) para deixar claro que agora é invisível só para não-superadmin. Não-superadmin continua vendo apenas o aviso textual atual, sem o número.

Nenhuma mudança é necessária em `casting_ops.py` — a regra do teto efetivo (feature 238) já existe e o front já deriva `tetoEfetivo` de `cache_cap`+`cache_value`, que já chegam pela API.

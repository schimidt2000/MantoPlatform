# Research — Feature 236: Cachê sugerido pela duração real do evento

Fatos verificados no código e no banco (14/08/2026) e decisões da Phase 0.

## Fatos verificados (a anatomia do bug)

- `_compute_performer_caches(snapshot)` (`app/calendar/routes.py:2741`) é a fonte única dos
  cachês por papel: tabela por variante + **noturno (+50 quando `event_time` ≥ 19h)** +
  adicional fora-SP por pessoa + acréscimo de show customizado. Produz só `cache_1h..cache_4h`.
- A criação (`_create_roles_from_input`, `routes.py:3178-3189`) indexa
  `cache_keys[dur_idx]` com `dur_idx = {"1":0,"2":1,"3":2,"4":3}.get(duracao, 0)`
  (`routes.py:3377`) — **duração fora de 1–4 cai no cachê de 1 HORA**.
- `EventCreatePage.tsx` só oferece botões 1–4h (`selectDuracao("1"|"2"|"3"|"4")`): um evento
  de 6h nem consegue declarar a duração — o caso real (evento 1235, 22h–4h) nasceu com teto de
  duração errada.
- O teto NÃO é só aviso: `casting_ops.py:68-70` **rebaixa** o cachê ao `cache_cap` para
  não-superadmin. Teto errado = casting travado no valor errado.
- O prefill do orçamento (`_build_orcamento_prefill`, `routes.py:2959`) envia `caches` ao
  cliente e a criação recebe `orc_caches` de volta do cliente (`agenda_write.py:632`), junto
  com `orcamento_history_id`.

## D1 — A régua de extrapolação vive dentro de `_compute_performer_caches`

**Decision**: a função ganha um parâmetro opcional `horas_extra: int | None`; quando presente
(> 4), cada papel de tabela ganha também `cache_custom` calculado como:

```
base_4h_sem_adicionais ÷ 4 × horas  +  adicionais fixos
```

- `base_4h_sem_adicionais`: o valor de 4h da variante **sem maquiagem** do papel
  (ex.: cara limpa 300; a régua do dono: "pega 300, divide por 4, vezes horas, adiciona 20").
- Adicionais fixos somados por fora, sem escalar: delta de maquiagem (variante com make −
  variante sem make, hoje 20), noturno (50), adicional fora-SP por pessoa e show customizado.
- Papéis com tabela de 4 valores escalam (performers, coordenador, técnico de som);
  **maquiador não escala** (é por make, não por hora) — permanece flat.
- Arredondamento: mesmo `round(int(...))` das chaves atuais.

**Rationale**: é a única fonte dos cachês por papel — prefill e criação enxergam o mesmo
número por construção. **Alternatives**: função separada de extrapolação — duplicaria a
montagem por variante (viola Princípio I).

## D2 — A criação recalcula os cachês no SERVIDOR pela duração real

**Decision**: quando a criação recebe `orcamento_history_id`, o backend recomputa os cachês
com `_compute_performer_caches(form_snapshot, horas_extra=duração se >4)` e usa esses valores
para `cache_value`/`cache_cap` — a lista `orc_caches` enviada pelo cliente vira fallback
apenas para criações SEM orçamento vinculado que já mandavam cachês (paridade). O `dur_idx`
passa a ser `int(duracao)` validado (≥1); durações 1–4 indexam a tabela; >4 usam
`cache_custom`; valor inválido é erro de validação (nunca mais fallback silencioso para 0).

**Rationale**: fonte única + integridade (mesma direção da feature 235: valores que valem
dinheiro não viajam pelo cliente). A paridade 1–4h é automática: o servidor usa a mesma
função que gerava a lista do cliente. **Alternatives**: estender o prefill para mandar
`cache_custom` de todas as durações possíveis ao cliente — o cliente não sabe a duração final
na hora do prefill; mandaria N variantes ou continuaria dessincronizado.

## D3 — Tela de criação: "Outra duração (h)"

**Decision**: ao lado dos botões 1–4h, um input numérico "Outra (h)" (min 5): selecionar um
botão limpa o input e vice-versa; quando o orçamento vinculado tem `duracao_custom`, o input
já vem preenchido com ela e mostra o `total_custom` como referência de preço (dado que o
prefill já entrega). A duração enviada é sempre o inteiro escolhido.

## D4 — Aviso "abaixo do sugerido" no casting

**Decision**: espelho do `acimaDoTeto` atual: `abaixoDoSugerido = cache_cap != null && cache <
cache_cap`, aviso informativo (sem bloqueio, sem expor o número do teto — o valor sugerido já
é visível porque nasce pré-preenchido no campo). Mantém a decisão de design registrada no
próprio componente ("o valor do teto é deliberadamente invisível").

## D5 — Sem migração e sem retroativo

**Decision**: nenhum campo novo (`cache_cap` existente é a referência); eventos já criados não
são recalculados. O conserto dos eventos reais 1205/1235 já foi feito à mão pelo dono — os
valores lançados servem de gabarito no `verify_236.py`, não de alvo de migração.

## Gabarito da régua (validação)

Com as tabelas vigentes (base cara limpa 300 em 4h, make 20, noturno 50):

| Caso | Conta | Sugerido |
|---|---|---|
| Ator make, 6h, 22h (Green) | 300÷4×6 + 20 + 50 | **520** |
| Ator sem make, 6h, 22h (Space) | 300÷4×6 + 50 | **500** |
| Coordenador sem show, 6h, 22h | 350÷4×6 + 50 | **575** |
| Ator make, 2h, 15h | tabela 270 | **270** (paridade) |
| Boneco show, 2h, 19h (mascote) | tabela 350 + 50 | **400** (paridade com o teto real do evento 1205) |

# Implementation Plan: Avaliações robustas (filtros, navegação e insights)

**Branch**: `038-avaliacoes-melhorias` | **Date**: 2026-06-12 | **Spec**: [spec.md](./spec.md)

## Summary

Reformular a página `/talents/avaliacoes` (035): filtros combináveis de **período**, **categoria** e
**evento** refletidos na URL; seletor de eventos **agrupado por mês**; comentários **de categoria**
visíveis com etiqueta; **ranking** de eventos (melhores/piores), **pontos de atenção** (notas 1–2) e
**tendência mensal**. Tudo leitura/agregação — **sem migration**.

## Constitution Check

- **I. Reutilizar** ✅ — mesma rota/template da 035; reusa `_RATING_CATEGORIES`, `_can_edit_talent`,
  macro `stars`, padrões de painel/KPI existentes.
- **IV. Não quebrar** ✅ — URL atual (`?event_id=`) continua funcionando; novos parâmetros são
  opcionais com fallback; sem mudança de banco.
- **V. UI/UX** ✅ — filtros com feedback imediato (auto-submit), estados vazios com "limpar filtros",
  contagens junto das médias, cores via variáveis CSS.
- **VII. Dinheiro BR** — n/a (sem valores monetários).

## Design Detalhado

### 1. Parâmetros de URL (GET, combináveis — FR-004)

| Param      | Valores                                   | Default | Inválido →    |
|------------|-------------------------------------------|---------|---------------|
| `event_id` | id numérico                               | —       | ignorado      |
| `cat`      | artista/som/figurino/texto/coordenacao/maquiagem | "" (todas) | ignorado |
| `period`   | `30d` / `90d` / `365d` / `all` / `custom` | `all`   | `all`         |
| `from`/`to`| datas ISO (só com `period=custom`)        | —       | ignorada      |

- Período filtra por **`CalendarEvent.start_at`** (data do evento, decisão da spec).
- Visão por evento: `period` é ignorado (evento já é o recorte); `cat` continua valendo.

### 2. Rota `avaliacoes()` — `app/talents/routes.py`

Refatorar em torno de um recorte único:

- `_parse_period(period, from, to) -> (date_start, date_end)|None` (helper pequeno).
- Base query de ratings **com join em CalendarEvent** para aplicar o período.
- **Recorte por categoria** (`cat` definido): scores/distribuição/comentários vêm de
  `EventSubRating` (da categoria) em vez de `EventRating`; KPI rotulado com a categoria.
  Sem `cat`: comportamento atual (geral) + seção "média por categoria" mantida.
- **Seletor de eventos**: eventos avaliados do período, agrupados por mês
  (`[{label: "Junho/2026", events: [...]}, ...]`, mais recente primeiro).
- **Comentários (FR-005)**: lista única com itens
  `{score, comment, author, event_id, event_title, submitted_at, cat_key, cat_label, subject_name}`:
  - geral (`EventRating.comment`) → etiqueta "Geral";
  - categoria (`EventSubRating.comment`) → etiqueta da categoria; se `subject_talent_id`,
    acrescenta o nome do avaliado ("Artista — Fulano");
  - com `cat` ativo: só os da categoria. Ordenado por data desc; geral limita a 30.
- **Ranking (FR-006)**: por evento do recorte, média (geral, ou da categoria se `cat`) + contagem;
  `best`/`worst` = até 3 de cada (só exibe "piores" se houver ≥ 2 eventos distintos).
- **Pontos de atenção (FR-007)**: notas ≤ 2 (gerais + sub-categorias; com `cat`, só a categoria),
  ordenadas por data desc, limite 10, com evento, etiqueta, autor e comentário.
- **Tendência (FR-008)**: agrupar por mês do evento (`start_at`), média + contagem, ordem
  cronológica; meses sem avaliação não aparecem (sem zero artificial).
- Tudo computado em Python sobre as queries já carregadas (volume baixo) — sem SQL extra complexo.

### 3. Template — `app/templates/talents/avaliacoes.html`

- **Barra de filtros** (um form GET, auto-submit no change):
  - chips/segmento de período (30 dias · 3 meses · 12 meses · Tudo · Personalizado → inputs de/até);
  - select de categoria (Todas + 6);
  - select de evento com `<optgroup>` por mês, cada option com `dd/mm — título`;
  - botão "✕ Limpar filtros" quando houver filtro ativo.
- **KPIs**: rótulos refletem o recorte ("Nota média — Figurino · últimos 30 dias").
- **Tendência**: barras CSS verticais (mês, média, contagem no title/abaixo) — sem lib JS.
- **Ranking**: dois mini-painéis "Melhores" / "Pontos a melhorar" com média + estrelas + contagem,
  linha clicável → `?event_id=…` (preservando `cat`).
- **Pontos de atenção**: painel com borda/acento vermelho, itens com nota, etiqueta de categoria,
  evento, autor, comentário; vazio → "✅ Nenhuma nota baixa no recorte".
- **Comentários**: chip de categoria por item (cor neutra; "Geral" mais discreto).
- **Estados vazios**: mensagem + botão limpar filtros (FR-009 / SC-004).

### 4. Acesso e portal

- `_can_edit_talent()` mantido (FR-010). Nenhuma alteração em templates do portal.

### 5. Verificação

- `ruff check app/`; boot da app.
- Teste funcional via test client (login staff): GET sem filtros; `?cat=figurino`; `?period=30d`;
  `?period=custom&from=…&to=…`; `?event_id=X&cat=coordenacao`; parâmetros inválidos
  (`cat=banana`, `from=xx`) → 200 com fallback; usuário sem permissão → 403.
- Conferir no HTML: optgroup por mês, etiquetas de categoria nos comentários, painéis novos.

## Project Structure

```text
app/talents/routes.py                    # avaliacoes() reformulada + helpers de recorte
app/templates/talents/avaliacoes.html    # barra de filtros, ranking, atenção, tendência, etiquetas
```

## Fora de escopo

- Ranking de pessoas avaliadas (artistas) — follow-up possível.
- Exportação (PDF/planilha) do resumo.
- Notificação automática de notas baixas.

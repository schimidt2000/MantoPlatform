# Tasks — Salvar talento e cachê do casting de forma confiável (138)

- [X] T001 [US1] `app/templates/event_detail.html` (`initSearch()`): variável
      `confirmedName` por instância do componente, inicializada com o nome atualmente
      selecionado; atualizada só dentro de `pick()` (nome escolhido) e `clear()` (string
      vazia) — fonte única de verdade sobre "seleção confirmada" vs "só digitado"
- [X] T002 [US1] `app/templates/event_detail.html`: listener `submit` no `<form>` de cada
      vaga (Elenco, Equipe de Apoio e Técnico de Som/Presença — 5 instâncias do
      componente) — bloqueia o envio quando `text.value.trim()` não corresponde a
      `confirmedName`; mostra mensagem inline (`.ts-error-msg` + `.ts-error`/`.ts-shake`,
      CSS local self-contido) específica para os dois casos; foca o campo; nunca apaga o
      que já foi digitado nos outros campos
- [X] T003 [US1] `app/calendar/routes.py` (`_handle_assign_casting`): `flash()` de
      sucesso após cada commit, reaproveitando a mesma mensagem já usada no `EventLog`
      (nome do talento + cachê); novo `else` para o caso "sem talento" (antes não gerava
      nenhum feedback, nem log)
- [X] T004 Verificação funcional vs `manto_local`: POST de `assign_casting` com
      talent_id+cache_value preenchidos salva os dois juntos; POST só com cache_value
      preserva o talento anterior; POST com talent_id vazio remove a associação mas
      preserva o cachê enviado junto; flash de sucesso aparece nos três casos. Todos os
      cenários passaram (`scripts/db/verify_138_casting_save.py`).
      Achado durante a verificação: `_handle_assign_casting` tinha o MESMO bug de
      `filter_by(id=request.form.get(...))` contra coluna Integer já documentado na
      memória do projeto (quebra em `manto_local`/psycopg3, não em produção/psycopg2) —
      corrigido com `int(...)` explícito após `.isdigit()`, igual ao padrão já aplicado
      na feature 136.
- [X] T005 Verificação do componente JS: `node --check` no trecho de `initSearch()`
      extraído (sintaxe OK) + simulação manual dos 4 cenários (texto sem seleção bloqueia;
      texto igual ao confirmado passa; texto vazio com hidden vazio passa; texto apagado
      com hidden preenchido bloqueia) — sem navegador automatizado no projeto, validação
      por leitura de código guiada pelos cenários do spec.
- [X] T006 `ruff check` nos arquivos tocados (mesma contagem do baseline, 12
      pré-existentes em `routes.py`, nenhum novo); changelog (`docs/changelog.html`,
      republicado no link já existente); pointer do plano em `CLAUDE.md` atualizado;
      commit, merge em `main`, push

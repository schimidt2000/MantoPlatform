# Tasks — 273 Orçamento → evento

Ordem de execução; cada item termina com a prova pedida. Nada de `db migrate` (sem migration).

## Backend

- [x] T1 `app/calendar/orcamento_evento_ops.py`: `snapshot_do_orcamento`, `_km_ida`,
      `resumo_do_orcamento`, `aplicar_fora_sp_do_orcamento`, `_chave` (NFD + casefold + espaços),
      `aplicar_equipe_do_orcamento` (relatório com `nao_casados`), `aplicar_valores_do_orcamento`
      (só sem venda; `sale_date` pela 267b; comissão por injeção), `outro_evento_vivo_do_orcamento`,
      `set_event_orcamento` (+ `OrcamentoJaVinculado`, `EventLog`, `frase`).
- [x] T2 `app/calendar/routes.py::_create_event_core`: `aplicar_fora_sp_do_orcamento(event, entry)`
      depois dos cachês do orçamento.
- [x] T3 `app/calendar/event_ops.py::reclassificar_fora_de_sp`: orçamento vinculado com `fora_sp`
      decide antes do Geocoding; busca a estimativa se não há km.
- [x] T4 `app/api/agenda_write.py`: `PATCH /api/events/<id>/orcamento` (gate `_can_manage_sale`,
      satélite 409, alheio 404, `OrcamentoJaVinculado` 409, resposta = detalhe + `relatorio_orcamento`).
- [x] T5 `app/api/agenda_read.py`: `venda.source` e `venda.orcamento` (resumo) quando visível.
- [x] T6 `app/api/orcamento_read.py`: `_entry_summary(e, evento)` com `event_id`/`event_title`;
      mapa `eventos_por_orc` numa consulta. `orcamento_write.py`: `DELETE` → 409 + `event_id`.

## Frontend (`apps/internal`)

- [x] T7 `lib/eventInline.ts` `useSetEventOrcamento`; `lib/agenda.ts` `OrcamentoResumo`,
      `RelatorioOrcamento`, `venda.orcamento`/`source`; `lib/orcamento.ts` `event_id`/`event_title`.
- [x] T8 `components/OrcamentoPicker.tsx` (busca `?q=`, 250 ms, estados explícitos).
- [x] T9 `ComercialSection.tsx`: `chipsDoOrcamento` + `OrcamentoPanel` (Aplicar ao evento / Trocar /
      Desvincular / picker + duração quando sem venda / aviso para evento do Google) no lugar da
      linha "Orçamento de origem".
- [x] T10 `pages/OrcamentoHistoricoPage.tsx`: "Ver evento".

## Prova

- [x] T11 `verify_273.py` 15/15 (`limiter.enabled = False` para os logins).
- [x] T11b Revisão adversarial (workflow, 4 lentes + 2 céticos por achado) e correções: retorno de
      `aplicar_fora_sp_do_orcamento` = "o orçamento diz" (edição/estimativa/sync não rebaixam);
      sync do Google consulta o orçamento; DELETE solta cancelados; cortesia conta como venda;
      duração 1..4 e bool/str → 400; vínculo alheio → 409 + `venda.tem_orcamento`; 1:1 no POST;
      acréscimos tipados copiados; data do orçamento por recorte; 409 com link; relatório em
      estado local; invalidação do histórico/agenda; erro do DELETE visível no histórico.
- [x] T12 Regressão `verify_239b` 7/7 · `verify_267b` 8/8 · `npm run typecheck` 0 · `ruff` baseline.
- [x] T13 Em tela (manto_local): evento 1323 (Google, RUMI + ZOEY + MIRA, sem venda) → buscar
      "Lizz" → orçamento 1786 → "Vincular e aplicar" → chips "Fora de SP · 115 km · 1 coordenador ·
      Show · técnico de som", frase "teto em 5 papel(is), fora de SP"; Produção mostra teto R$ 477 nos
      personagens e "Marcar transporte" em todos.
- [x] T14 Docs 01/02/03/04 + nota no plano das ondas.
- [ ] T15 Commit na branch `273-orcamento-para-evento` (sobre a 239b) e push (a pedido do dono).

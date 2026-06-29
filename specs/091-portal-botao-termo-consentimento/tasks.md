# Tasks: Botão termo de consentimento no portal (091)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Sem testes automatizados solicitados — verificação manual contra `manto_local`.

## Phase 1: US1 — Rever o termo (P1) 🎯 MVP

- [X] T001 [US1] `terms()` em `app/talent_portal/routes.py`: se o talento já aceitou (GET), renderizar
  `portal/terms.html` com `view_only=True` (não redirecionar para a home). POST/guards inalterados.
- [X] T002 [US1] `portal/terms.html`: em `view_only`, ocultar o rodapé de aceite e o "role até o fim";
  mostrar "Você aceitou em DD/MM/AAAA" + botão **Voltar ao portal**; o script só roda quando há o form.
- [X] T003 [US1] `portal/home.html`: botão pequeno **"📄 Termo"** no cabeçalho (ao lado de "Meu perfil").

## Phase 2: Verificação

- [X] T004 Verificar contra `manto_local`: já aceito → GET mostra leitura + data + voltar (sem
  redirect); não aceito → fluxo de aceite intacto; home mostra o botão. `ruff` sem erros novos.

## Dependencies

- T001 → T002 (modo leitura). T003 independente. T004 por último.

## MVP

US1 inteiro (modo leitura + botão).

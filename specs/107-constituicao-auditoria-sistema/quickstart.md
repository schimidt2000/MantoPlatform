# Quickstart — Feature 107

## Rodar

```powershell
.\scripts\db\run-local.ps1   # app contra manto_local — sem migration
```

## Verificação

### US1 — Constituição

1. Ler `.specify/memory/constitution.md` v1.3.0: executar cada comando dos portões no
   projeto — todos funcionam (nenhum cita pytest/tests/ ou mypy como obrigatório).
2. Conferir changelog datado e princípio VIII (mobile-first público).
3. CLAUDE.md sem instruções contraditórias (comandos e regra de testes alinhados).

### US2 — Auditoria

1. `specs/107-constituicao-auditoria-sistema/auditoria.md` cobre os 12 módulos.
2. Resumo executivo com contagens por severidade/status.
3. Achados "✅ corrigido" têm mudança correspondente no diff da feature.

### US3 — Correções (varredura automatizada + visual)

```powershell
# Varredura: deve retornar ZERO
grep -rn '{:,' app/templates          # moeda reinventada/americana
grep -rn 'print(' app --include=*.py  # (exceto blueprints/strings legítimas)
```

1. Telas com moeda: home (KPI), talent_detail, desempenho, event_create (orçamento),
   financeiro/dashboard → todos os valores "R$ 9.999,99" (BR, 2 casas).
2. Erros: conferir que os `except` tocados agora logam (inspeção de código) e os fluxos
   continuam (renderização das telas dos módulos tocados via test client).
3. Duplo envio: nos forms protegidos, clicar 2× rápido → 1 registro só (verificar criação de
   evento e um form do financeiro no app real).
4. alert() de erro substituído por mensagem inline nas telas listadas na auditoria.

### Regressão

Script test client (requests fora de app_context): renderização 200 das telas tocadas
(home, desempenho, talent_detail, event_create, financeiro/dashboard e telas com alert
alterado) + varreduras regex acima integradas ao script.

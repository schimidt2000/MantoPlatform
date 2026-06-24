# Implementation Plan: Trocar de plano sem reload (081)

**Branch**: `081-educamanto-switch-pacote` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

## Summary

Trocar de plano no seletor passa a ser **client-side** (sem recarregar), preservando dias/ensemble/
transporte/acréscimo e recalculando — fazendo o valor na tela bater com o do PDF. O cap do acréscimo
vira **por plano** (min com o valor original do plano), aplicado igual na tela e na geração; o input
não é mais reescrito ao trocar de plano. **Só template; sem backend/migration.**

## Technical Context

**Language/Version**: Jinja2 + JS vanilla (`app/templates/educamanto/index.html`).

**Testing**: contra **`manto_local`** — seletor usa `switchPackage` (sem reload); valor por plano
calculado com o mesmo `valoresPacote` + cap por plano da geração; render OK; JS balanceado.

**Constraints**: paridade tela/PDF; não perder dados ao trocar; pt-BR.

**Scale/Scope**: `app/templates/educamanto/index.html` (seletor → `switchPackage`; link Editar com
id; cap por plano sem reescrever input; geração capando por plano).

## Constitution Check

- **I. Reutilizar**: ✅ Usa `valoresPacote`/`calcular`/`loadConfig` já existentes; dados de planos já
  no cliente.
- **IV. Não quebrar**: ✅ Comportamento de cálculo idêntico; só a troca deixa de recarregar.

**Resultado**: PASS — sem migration.

## Project Structure

```text
app/templates/educamanto/index.html
  - seletor onchange -> switchPackage(id) (client-side; sem reload)
  - switchPackage: troca pkg, loadConfig, calcular, atualiza link Editar e URL (replaceState)
  - cap do acréscimo por plano (min com original) — sem reescrever o input
  - geração: cap por plano (mesma fórmula da tela) -> PDF bate com a tela
```

**Structure Decision**: Troca de plano no cliente + cálculo consistente. Sem migration.

## Complexity Tracking

> Sem violações.

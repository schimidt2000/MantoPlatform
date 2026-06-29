# Implementation Plan: Botão termo de consentimento no portal (091)

**Branch**: `091-portal-botao-termo-consentimento` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

## Summary

Permitir reler o Termo de Consentimento no Portal do Artista (`/portal/terms`) mesmo após o aceite, e
adicionar um botão pequeno e visível no cabeçalho da home do portal. Fluxo de primeiro aceite inalterado.
**Sem model novo, sem migration.**

## Technical Context

- `app/talent_portal/routes.py` — `terms()`: quando o talento **já aceitou** (GET), em vez de redirecionar
  para a home, renderiza `portal/terms.html` em **modo leitura** (`view_only=True`). Mantém guardas de
  login e troca de senha. POST de aceite inalterado.
- `app/templates/portal/terms.html` — quando `view_only`: ocultar o rodapé de aceite (checkbox + botão) e
  o "role até o fim"; mostrar "Você aceitou em DD/MM/AAAA" + botão **Voltar ao portal**; o script de
  scroll/checkbox só roda quando há o form (não-view_only).
- `app/templates/portal/home.html` — botão pequeno **"📄 Termo"** no cabeçalho (ao lado de "Meu perfil").

**Link para o usuário ver:** `https://portal.mantoproducoes.com.br/portal/terms`.

## Constitution Check

- **IV. Não quebrar**: fluxo de aceite (POST e primeira visita) intacto; só adiciona o modo leitura e um
  botão.

**Resultado**: PASS — sem migration.

## Testing

Contra **`manto_local`**: talento que já aceitou → GET `/portal/terms` mostra o texto em modo leitura com
a data de aceite e botão Voltar (não redireciona); talento que não aceitou → continua vendo o aceite; home
mostra o botão "Termo". `ruff` sem erros novos.

## Project Structure

```text
app/talent_portal/routes.py            — terms(): modo leitura quando já aceito
app/templates/portal/terms.html        — view_only (sem aceite) + data + voltar; script guard
app/templates/portal/home.html         — botão "📄 Termo" no cabeçalho
```

## Complexity Tracking

> Sem violações.

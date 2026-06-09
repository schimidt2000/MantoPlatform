# Implementation Plan: Anotações e warning do talento

**Branch**: `036-talento-notas-warning` (sobre `035`) | **Date**: 2026-06-09 | **Spec**: [spec.md](./spec.md)

## Summary

Adicionar dois campos ao talento — **anotações internas** e **nível de alerta** (nenhum/leve/moderado/
grave) — editáveis na página do talento (SUPERADMIN/CASTING) e exibir um **badge colorido ao lado do
nome** no banco de talentos. Internos (nunca no portal). Migration manual para os dois campos.

## Constitution Check
- **I. Reutilizar** ✅ — reusa `_can_edit_talent`, `talent_detail`, estilos de badge.
- **IV. Não quebrar** ✅ — campos nullable; talentos antigos intactos. Sem afetar portal.
- **V. UI/UX** ✅ — badges com cor via variáveis/cores consistentes; feedback de salvar.

## Design Detalhado

### 1. Banco (migration manual)
- `Talent.notes` (Text, nullable); `Talent.warning_level` (String(20), nullable) →
  valores: `leve`/`moderado`/`grave` (None/"" = nenhum).
- Migration `k7e8f9a0b1c2_talent_notes_warning.py` (down_revision `j6d7e8f9a0b1`): add 2 colunas em
  `talents`. up/down.

### 2. Salvar — rota
- `POST /talents/<id>/notes` (acesso `_can_edit_talent`): lê `notes` e `warning_level`
  (valida em {"", "leve", "moderado", "grave"}); salva; flash de sucesso; redireciona para o detalhe.

### 3. Página do talento — `talent_detail.html`
- Bloco "Anotações internas e alerta" (visível à equipe; editável se `can_edit`):
  - textarea `notes`;
  - select `warning_level` (Nenhum/Leve/Moderado/Grave) com a opção atual selecionada;
  - botão Salvar (form POST). Se `can_edit` for falso, exibe somente leitura.
- Mostra o badge do alerta atual no topo, ao lado do nome do talento (consistência com a lista).

### 4. Banco de talentos — `talents_list.html`
- Ao lado de `talent-card-name`, um badge colorido quando `p.warning_level` estiver definido
  (leve=amarelo, moderado=laranja, grave=vermelho). Sem alerta → nada.
- Helper de rótulo/cor inline no template (ou macro simples).

### 5. Garantir que NÃO vaza no portal
- Não referenciar `notes`/`warning_level` em nenhum template do portal do talento (apenas staff).

### 6. Verificação
- Migration up/down; boot + ruff; salvar nota + alerta e reabrir; badge na lista por nível; acesso
  negado a quem não edita; portal não mostra.

## Project Structure
```text
migrations/versions/k7e8f9a0b1c2_talent_notes_warning.py  # NOVO — notes + warning_level
app/models.py                       # Talent.notes, Talent.warning_level
app/talents/routes.py               # POST /talents/<id>/notes; passar can_edit (já passa)
app/templates/talent_detail.html    # bloco de anotações + alerta
app/templates/talents_list.html     # badge ao lado do nome
```

## Fora de escopo
- Histórico de alterações das anotações. Filtro por nível de alerta no banco (follow-up possível).
```

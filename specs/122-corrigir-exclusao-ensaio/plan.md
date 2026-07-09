# Implementation Plan: Corrigir Erro 500 ao Excluir Ensaio (122)

**Branch**: `122-corrigir-exclusao-ensaio` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

## Summary

Duas correções em `app/calendar/routes.py`, ambas no caminho de `delete_ensaio()`:

1. **Captura de exceção do Google ampliada**: `except RuntimeError` → `except Exception`,
   com `current_app.logger.exception(...)` (nunca engolir sem logar) e flash amigável —
   mesmo padrão já usado em `create_event()`. Qualquer falha do Google (evento já removido
   de lá, token expirado, timeout) deixa de travar a exclusão local.
2. **Limpeza manual das tabelas sem cascade**: extraída uma função `_clear_event_side_tables
   (event_id)` com as 4 linhas que `_delete_event()` já faz (`EventLog`, `EventContract`,
   `EventPayment`, `EventRating` — não têm `cascade="all, delete-orphan"` no relacionamento
   do `CalendarEvent`, confirmado em `app/models.py`), reaproveitada tanto por
   `_delete_event()` (refatoração, comportamento idêntico) quanto por `delete_ensaio()`
   (correção — hoje ausente ali, causa de violação de chave estrangeira sempre que o
   ensaio tem histórico de ações).

Aproveitando a "verificação" pedida, o mesmo problema de captura de exceção restrita em
`_delete_event()` (usado pela exclusão de evento comum) também é corrigido, já que é o
mesmo defeito, no mesmo arquivo, achado durante a auditoria.

## Technical Context

**Stack**: o existente. **Storage**: nenhuma mudança de schema.

**Arquivos**: `app/calendar/routes.py` — `_clear_event_side_tables()` nova (helper),
`_delete_event()` (usa o helper no lugar das 4 linhas inline; `except RuntimeError: pass`
→ `except Exception as exc:` com log + flash), `delete_ensaio()` (chama o helper antes de
`db.session.delete(ensaio)`; `except RuntimeError as exc:` → `except Exception as exc:`
com log mantendo o flash já existente).

**Testing**: reproduzir o bug relatado no manto_local — criar um ensaio, gerar um
`EventLog` para ele (ex.: via `link_ensaio_parent`), simular falha do Google (não
`RuntimeError`) na exclusão, chamar `delete_ensaio` e confirmar: (a) sem o fix, reproduz
500 (opcional, para validar o diagnóstico); (b) com o fix, a exclusão conclui na primeira
tentativa, sem tela de erro, com o ensaio e seus registros associados removidos. Repetir
para ensaio órfão (sem `parent_event_id`) e para ensaio sem histórico algum (garantir que
nada quebrou no caminho feliz). Conferir que `excluir_evento` (evento comum) continua
funcionando após a refatoração de `_delete_event()`.

## Constitution Check

| Princípio | Avaliação |
|---|---|
| I. Reutilizar | ✅ `_clear_event_side_tables()` elimina duplicação entre `_delete_event()` e `delete_ensaio()` — mesma limpeza, um lugar só. |
| II. Padrões Python | ✅ Nenhum `except` amplo sem logar (regra explícita do CLAUDE.md) — `current_app.logger.exception` em ambos os pontos corrigidos. |
| III. Camadas | ✅ Helper de limpeza isolado, sem lógica de HTTP; rotas continuam finas. |
| IV. Não quebrar | ✅ Comportamento de `_delete_event()` preservado (mesmas 4 tabelas, mesma ordem); `delete_ensaio()` ganha só a limpeza que faltava — nenhum campo/fluxo existente muda. |
| V. UI/UX | ✅ Elimina a tela de erro técnica; aviso amigável já era o padrão pedido pelo usuário nesta mesma sessão (feature 117/118) — consistente. |
| VI. Planejar | ✅ Este plano, com diagnóstico de causa raiz confirmado por leitura de código antes de qualquer alteração. |
| VII. Moeda BR | N/A. |

**Gate: PASS.**

## Decisões

1. **Corrigir também `_delete_event()`**, não só `delete_ensaio()`: é o mesmo defeito
   (captura de exceção restrita ao redor da mesma chamada `delete_event()`), encontrado
   durante a verificação pedida pelo usuário; deixá-lo sem correção seria saber de uma
   bomba-relógio idêntica e não desarmar.
2. **Não tocar em `edit_ensaio()`** (mesmo padrão de captura restrita, mas para
   atualização, não exclusão): fora do escopo relatado ("processo de exclusão"); registrado
   como recomendação de acompanhamento em vez de expandir o pedido original.
3. **Helper sem commit próprio**: `_clear_event_side_tables()` só executa os `.delete()`
   de query; quem chama decide quando commitar — mesma responsabilidade que `_delete_event()`
   já tinha, preservada.

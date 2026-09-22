# Modelo de dados (Phase 1) — Feature 301

**Spec**: [spec.md](./spec.md) · **Plano**: [plan.md](./plan.md) · **Data**: 2026-09-21

## Migration: nenhuma

Nenhuma tabela nova, nenhuma coluna nova, nenhum `down_revision` a encadear. A feature muda **quem
enxerga o que já está gravado** e **quem pode escrever por cima**, não o que se grava.

Isso não é detalhe de conveniência: é o que mantém a 301 fora do procedimento de migração
destrutiva (`DEVELOPMENT.md` §Migrations) e fora de qualquer passo manual no Shell do Render.

---

## Entidades envolvidas (todas já existentes)

### `OrcamentoHistory` — `app/models.py:1478`

O orçamento congelado. **Nada muda no modelo.** O que muda é o papel de um campo:

| Campo | Antes desta feature | Depois |
|---|---|---|
| `user_id` (FK → `users`) | **filtro de visibilidade** — decidia se a linha existia para você | **autoria**: informação exibida ("Vendedor"), critério de filtro opcional, e a única base da trava que sobra (excluir, e mexer em vínculo alheio) |

**Dependência declarada**: depois da 301, `user_id` é a **única** base das duas regras de
autorização que sobram — FR-006 (excluir) e FR-011 (trocar, desvincular ou re-aplicar sobre
vínculo alheio) — e ainda alimenta a coluna "Vendedor" e o filtro por vendedor. Não existe segundo
campo de autoria no modelo. Se esse campo passar a significar outra coisa que não "quem criou o
orçamento" (dono reatribuído, último editor, transferência de carteira), FR-006 e FR-011 **trocam
de sujeito em silêncio**, sem nenhum verify acusar: o novo titular ganha as duas travas e o autor
original perde. Qualquer feature futura que reatribua `user_id` tem de revisar os dois.

Campos lidos pela feature, sem alteração: `id`, `created_at`, `client_name`, `event_location`,
`event_date`, `total_1h`…`total_4h`, `has_show`, `form_snapshot`, `result_snapshot`.

**Regra de integridade que já existe e continua valendo**: `app/admin/user_ops.py:425` impede
apagar um usuário que tenha orçamento. Por isso `user_name` raramente é nulo — mas a coluna da tela
ainda precisa aguentar o caso (registro legado), sem quebrar a linha.

### `CalendarEvent` — vínculo com o orçamento

| Campo | Papel nesta feature |
|---|---|
| `orcamento_history_id` (FK, sem `ondelete`) | **passa a ser o sujeito da trava de escrita**: quem pode mexer no vínculo é o autor do orçamento que está *aqui*, não o autor do orçamento que se quer colocar (R2) |
| `sale_value`, `sale_date` | escritos por "aplicar valores"; `sale_date` decide o mês da comissão (hotfix 267b). São **o motivo** de re-aplicar ter virado ação restrita |
| `cancelled_at` | inalterado — evento cancelado já é ignorado pelo selo "Ver evento" e solto antes do DELETE (feature 273) |

### `AuditLog` — `app/models.py:584`

Reusada por FR-013, **sem coluna nova**. Escrita por `app/utils.py:audit()`.

| Coluna | O que recebe no reenvio de orçamento alheio |
|---|---|
| `actor_name` / `actor_role` | preenchidos por `audit()` a partir de `current_user` |
| `entity_type` | `"orcamento"` |
| `entity_id` | id do `OrcamentoHistory` reenviado |
| `entity_name` | nome do cliente do orçamento (legível, que é para o que a coluna serve) |
| `action` | verbo do reenvio, no padrão dos verbos já usados na tabela |
| `detail` | destinatário do e-mail **e** de quem é o orçamento — é o par que responde "quem mandou o quê para quem" |
| `created_at` | `audit()` carimba |

**Quando NÃO grava**: reenvio do próprio orçamento; abrir; baixar PDF; envio que falhou. A linha
nasce só depois de `send_quote_email` devolver sucesso.

**Persistência**: `audit()` só faz `db.session.add`. O endpoint de e-mail **não commita hoje** —
precisa passar a commitar. Sem isso a linha some no fim da requisição e um verify ingênuo,
conferindo na mesma sessão, veria o registro que não existe (hotfix 257).

---

## Estados e transições — o vínculo orçamento↔evento

A única "máquina de estados" desta feature. O que decide é **o autor do orçamento atualmente
vinculado**:

```text
                   ┌────────────────────────┐
                   │ evento SEM orçamento   │
                   └───────────┬────────────┘
                               │ vincular  (qualquer COMERCIAL — mudança da 301)
                               ▼
        ┌──────────────────────────────────────────────┐
        │ evento vinculado ao orçamento de <autor>      │
        └───────┬──────────────────────────────┬────────┘
                │                              │
     autor == eu  ou  SUPERADMIN        autor != eu  (e não sou SA)
                │                              │
                ▼                              ▼
     trocar · soltar · re-aplicar      409 `orcamento_de_outro`
          (permitido)                  nomeando <autor> — vale para
                                       os três verbos (mudança da 301)
```

Invariantes preservadas das features anteriores:

- **Um orçamento vivo por evento** — `OrcamentoJaVinculado` continua barrando vincular um orçamento
  que já está em outro evento não cancelado.
- **DELETE com evento vivo** — 409 + `event_id` (feature 273) continua valendo, mas vem **depois**
  da checagem de autoria (dono em `orcamento_write.py:115`, 409 em `:124`): quem não é o autor leva
  404 e nunca chega no 409. A ordem fica como está — antecipá-la confirmaria a existência do
  orçamento e do evento para quem não é autor (Princípio XIII).
- **Aplicar é idempotente** — `set_event_orcamento` não muda de comportamento; só muda quem chega
  até ele.

---

## O que NÃO entra no modelo

- **Registro de leitura**: abrir e baixar PDF não geram linha em lugar nenhum (decisão do dono).
- **Paginação / cursor**: o teto de 300 continua sendo um `LIMIT` fixo, sem estado de página.
- **Coluna de "compartilhado com"**: a visibilidade é do papel, não de uma lista por orçamento —
  não há nada a persistir.

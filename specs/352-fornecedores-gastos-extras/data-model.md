# Modelo de dados — 352

Migration à mão `f352a1b2c3d4_fornecedores.py`, `down_revision = "d334b2c4e6f8"`.

## `fornecedores` (novo — model `Fornecedor`)

| Coluna | Tipo | Regra |
|---|---|---|
| `id` | Integer PK | |
| `nome` | String(200) NOT NULL | como aparece na tela e é gravado no gasto |
| `nome_normalizado` | String(200) NOT NULL, **UNIQUE** (`uq_fornecedores_nome_normalizado`) | `fornecedor_ops.normalizar_nome(nome)`; recalculado a cada alteração de `nome` |
| `pix` | String(120) NULL | chave PIX como digitada |
| `categoria_padrao` | String(30) NULL | uma de `CATEGORIAS_DO_FORNECEDOR` |
| `ativo` | Boolean NOT NULL default true (`server_default true`) | arquivado = `false`: some das sugestões |
| `criado_por_id` | Integer FK `users.id` ON DELETE SET NULL, NULL | `NULL` = veio da importação |
| `created_at` | DateTime NOT NULL | UTC (`datetime.utcnow`), como `special_expenses.created_at` |
| `updated_at` | DateTime NOT NULL | UTC; muda em alterar/arquivar/juntar |

Relações: `criado_por` → `User`; `gastos` → `SpecialExpense` (backref, `lazy=True`).

## `special_expenses` (existente)

| Coluna nova | Tipo | Regra |
|---|---|---|
| `fornecedor_id` | Integer FK `fornecedores.id` **ON DELETE SET NULL**, NULL, índice `ix_special_expenses_fornecedor_id` | preenchida só quando `disbursement_type = 'fornecedor'`; apagar fornecedor nunca apaga gasto |

`supplier_name` passa a guardar o `nome` do fornecedor ligado (reescrito ao renomear e ao juntar);
`supplier_pix` nunca é reescrito pelo cadastro.

## Invariantes

1. Gasto com `fornecedor_id` não nulo ⇒ `disbursement_type = 'fornecedor'` e
   `supplier_name = fornecedores.nome`.
2. Gasto com `disbursement_type = 'fornecedor'` salvo depois da 352 ⇒ `fornecedor_id` não nulo —
   **exceto** a categoria "Multa de cancelamento" (306: paga o artista da escala; nunca tem vínculo).
3. Depois da migration: nenhum gasto `fornecedor` (fora a multa) sem `fornecedor_id`; nenhum gasto
   `cliente` nem multa com.
4. Dois fornecedores nunca têm o mesmo `nome_normalizado` (banco).

## Transições

- **Ativo → arquivado → ativo**: só Financeiro/Superadmin (`PATCH ativo`). Gasto salvo com o nome de
  um arquivado liga a ele sem reativar.
- **Juntar (origem → destino)**: gastos da origem passam ao destino; destino herda `pix` e
  `categoria_padrao` que não tinha; origem é apagada.

## Downgrade

Remove índice, FK, coluna e tabela. Os nomes reescritos nos gastos antigos ficam como estão (a grafia
original sobrevive só nos dumps noturnos) — registrado no `docs/03`.

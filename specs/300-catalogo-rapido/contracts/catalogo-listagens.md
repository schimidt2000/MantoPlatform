# Contrato — listagens do catálogo (Feature 300)

## A cláusula principal: o contrato NÃO muda

Esta feature altera **como** os dados são buscados, nunca **o que** é devolvido. Para os cinco
endpoints abaixo, a resposta depois da mudança é **byte a byte idêntica** à de antes: mesmas
chaves, mesmos valores, mesma ordem, mesmos nulos.

Isso não é uma promessa de comentário — é o critério do cenário 1 e do cenário 3 do
`verify_300.py`, que captura a resposta de referência **antes** da alteração e compara campo a
campo depois.

| Endpoint | Gate | O que garante |
|---|---|---|
| `GET /api/admin/catalogo` | SUPERADMIN | `items[]` (com `characters[]` embutido) + `categories[]`, idênticos |
| `GET /api/admin/catalogo/personagens` | SUPERADMIN | `personagens[]` + `totais{}`, idênticos |
| `GET /api/catalogo` | público | `items[]` + `total` + `categories[]` + `whatsapp_number`, idênticos |
| `GET /api/catalogo/categorias` | público | `categories[]`, idêntico |
| `GET /api/catalogo/categoria/<slug>` | público | `category{}` + `items[]` (+ `og_image` sob `?og=1`), idênticos |

**Consequência para o frontend**: nenhum tipo TypeScript muda, nenhuma tela precisa tratar campo
novo, e não existe a janela de incompatibilidade entre backend e bundle que a constituição alerta
(campo novo opcional no React). Backend e frontend desta feature são independentes e podem ser
conferidos em qualquer ordem.

## O único acréscimo: categorias sem o catálogo junto

```http
GET /api/admin/catalogo/categorias
```

**Gate**: SUPERADMIN — o mesmo `_require_superadmin()` que já protege o `POST` no mesmo caminho e a
listagem vizinha. Sem o papel: `403` com o envelope padrão de `json_error`.

**Resposta 200**:

```json
{
  "categories": [
    { "id": 12, "name": "Filmes e Séries" },
    { "id": 3,  "name": "Princesas" }
  ]
}
```

- Ordenadas por nome, como na listagem de hoje.
- **Todas** as categorias, inclusive as sem produto ativo — o formulário precisa poder escolher
  qualquer uma (é o que distingue este endpoint do público `/api/catalogo/categorias`, que filtra
  por categoria com item ativo).
- A chave é `categories` e o formato do item é `{id, name}` **de propósito**: é exatamente o que a
  listagem já devolve, então o tipo `CatalogCategoryOption` (`lib/adminCatalogo.ts:37`) é reusado
  sem alteração.

**Por que existe** (detalhe em `research.md` R4): hoje a tela de edição chama a listagem inteira —
458 produtos com todos os personagens, 199 KB — para desenhar um seletor de 39 opções.

**Registro obrigatório**: linha na tabela de gates de `docs/01` §4.3.

## O que continua fora do contrato

- **A escolha da miniatura é do cliente.** O backend continua devolvendo o caminho do arquivo
  original (`/catalogo/midia/<arquivo>`); quem conhece o tamanho da caixa é o componente que
  desenha, e é ele que pede `/catalogo/midia/t/<largura>/<arquivo>`. Nenhum campo de miniatura entra
  na resposta.
- **A allowlist de largura permanece fechada** em `(128, 320, 480, 640)`. Largura fora dela responde
  404 e não grava nada em disco.
- **A rota de variante não muda**, nem os cabeçalhos de cache dela.

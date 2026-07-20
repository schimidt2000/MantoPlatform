# Implementation Plan: Melhorias na criação de produtos do catálogo

**Branch**: `141-melhorias-form-produto-catalogo` | **Date**: 2026-07-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/141-melhorias-form-produto-catalogo/spec.md`

## Summary

Três ajustes pontuais sobre a área de gestão do catálogo (feature 139):

1. **Escolher capa ao criar produto** — hoje só é possível escolher a capa entre fotos já
   salvas (editando); ao criar um produto novo com várias fotos de uma vez, nenhuma pode
   ser marcada. Estende o mesmo padrão de rádio "Capa" já usado na edição para uma prévia
   client-side das fotos recém-selecionadas (antes do upload).
2. **Compressão garantida** — investigação confirmou que a compressão (`app/storage.py`)
   já funciona para os formatos aceitos; a lacuna real é a ausência de validação de
   formato antes de processar — um arquivo que a biblioteca de imagem não consiga abrir é
   salvo cru, sem compressão nem aviso. Fecha essa lacuna validando a extensão antes de
   aceitar o upload (mesmo padrão já usado em `app/figurino/routes.py`).
3. **Remover botão do WordPress** — tira o link de `admin_catalogo_list.html` e
   `admin_importar_catalogo.html`'s ponto de entrada da navegação normal; a rota e o
   importador (`app/catalogo/importer.py`) continuam existindo no código, só deixam de
   estar alcançáveis pela interface (decisão documentada no spec — reversível, sem excluir
   funcionalidade que já funcionou).

## Technical Context

**Language/Version**: Python 3.11, Flask + SQLAlchemy + Jinja2; JavaScript vanilla nos
templates admin

**Primary Dependencies**: nenhuma nova — reaproveita `app/storage.py::save_file`/
`delete_file` (compressão já existente), o padrão de rádio "Capa" já usado em
`admin_catalogo_form.html` (feature 139) e o padrão `_ALLOWED_PHOTO_EXTENSIONS` já usado em
`app/figurino/routes.py`

**Storage**: PostgreSQL — nenhuma migration nova

**Testing**: script de verificação funcional com Flask test client contra `manto_local`
(padrão do projeto): criar produto com múltiplas fotos escolhendo capa não-primeira;
upload de arquivo com extensão não suportada é recusado sem criar nada; foto grande
enviada resulta em arquivo salvo muito menor (mesmo teste de compressão já validado
manualmente nesta investigação); botão de importar não aparece mais na listagem

**Target Platform**: aplicação web server-side (Flask + Jinja2), área administrativa
autenticada

**Project Type**: web application (monolito Flask existente)

**Performance Goals**: N/A — mudança é validação + uma pequena peça de UI client-side,
sem impacto de performance além do que a compressão já existente já faz

**Constraints**: não pode mudar a estrutura de dados (`CatalogItemImage`); não pode
remover a funcionalidade de importação do WordPress do código, só da navegação (decisão
de escopo do spec)

**Scale/Scope**: `app/admin/routes.py` (`_apply_catalog_photos`, `catalogo_admin_new`,
`catalogo_admin_edit`) e dois templates (`admin_catalogo_form.html`,
`admin_catalogo_list.html`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reutilizar antes de criar**: os três itens são extensões de padrões já existentes
  no próprio módulo (rádio de capa da edição, `_ALLOWED_PHOTO_EXTENSIONS` do Figurino,
  `save_file`/compressão já existente) — nada novo é inventado.
- **II. Padrões de código Python**: mudanças pequenas e localizadas em funções já
  existentes, com type hints/docstring mantidos.
- **III. Arquitetura em camadas**: validação de extensão é a mesma checagem simples já
  usada em outro lugar do sistema — não introduz regra de negócio nova.
- **IV. Não quebrar o que funciona**: comportamento padrão (primeira foto = capa quando
  nada é marcado) é preservado (FR-002); verificação funcional cobre esse caminho sem
  regressão, além dos casos novos.
- **V. UI/UX consistente e com feedback**: recusa de arquivo inválido (FR-005) usa o mesmo
  padrão de erro com preservação de campos já usado no restante do formulário (feature
  139/134) — nunca falha em silêncio.

Nenhuma violação. Gate passa sem exceções.

## Project Structure

### Documentation (this feature)

```text
specs/141-melhorias-form-produto-catalogo/
├── plan.md              # This file
├── spec.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

Sem `research.md`/`data-model.md`/`contracts/`: investigação já feita durante a
especificação (compressão testada manualmente, causa raiz identificada); sem entidade
nova; sem interface externa nova.

### Source Code (repository root)

```text
app/
├── admin/
│   └── routes.py        # _apply_catalog_photos: valida extensão antes de processar +
│                         #   resolve capa também a partir de um índice indicado para
│                         #   fotos recém-enviadas; catalogo_admin_new/edit tratam o erro
│                         #   de arquivo inválido como os demais erros de validação
└── templates/
    ├── admin_catalogo_form.html  # prévia client-side das fotos selecionadas + rádio de
    │                              #   capa (novas fotos); hidden field com o índice
    │                              #   escolhido
    └── admin_catalogo_list.html  # remove o link "Importar do WordPress"
```

## Design Decisions

1. **Validação de extensão (`_apply_catalog_photos`)**: antes de chamar `save_file` para
   cada arquivo de `new_photos`, checa a extensão contra um conjunto
   `{".jpg", ".jpeg", ".png", ".webp"}` (mesmo valor de `_ALLOWED_PHOTO_EXTENSIONS` do
   Figurino, definido localmente aqui — não importa entre módulos por serem domínios
   diferentes). Arquivo fora dessa lista faz a função levantar um erro específico
   (`ValueError` com a lista de nomes rejeitados) capturado pela rota chamadora, que
   re-renderiza o formulário com a mensagem e os campos preservados — nada é criado/
   commitado parcialmente.

2. **Prévia + escolha de capa nas fotos recém-selecionadas**: `admin_catalogo_form.html`
   ganha um listener no `change` do `<input type="file" name="new_photos" multiple>` que:
   - gera uma URL local (`URL.createObjectURL`) por arquivo selecionado, para prévia sem
     round-trip ao servidor;
   - renderiza um card por arquivo (miniatura + rádio "Capa", mesmo componente visual já
     usado nas fotos existentes da edição);
   - ao escolher um rádio, grava o índice (posição do arquivo dentro do `FileList`) num
     `<input type="hidden" name="new_photo_cover_index">`.
   Isso não altera o `<input type="file">` em si (a ordem de envio ao servidor continua a
   ordem original do `FileList`) — só comunica qual posição deve virar capa.

3. **Resolução de capa no backend**: `_apply_catalog_photos` já tem a lógica
   `cover_raw` (id de foto existente) → `new_images[0]` (padrão). Passa a checar, entre os
   dois: se `new_photo_cover_index` foi enviado e é um índice válido dentro dos arquivos
   novos processados com sucesso, usa `new_images[esse índice]` como capa antes de cair no
   padrão "primeira foto nova". Mantém FR-002 (padrão quando nada foi marcado).

4. **Remover o botão do WordPress**: exclui o link/botão de
   `admin_catalogo_list.html` (`page_actions`) e do próprio
   `admin_importar_catalogo.html` (que tinha um link recíproco pra gestão) — a rota
   `/admin/importar-catalogo` e `app/catalogo/importer.py` continuam existindo no código
   (decisão documentada no spec.md), só sem nenhum ponto de entrada visível.

5. **Verificação funcional (T00x)**: script novo (`scripts/db/verify_141_*.py`,
   gitignored) cobrindo: criar produto com 3 fotos marcando a 2ª como capa e conferir que
   ela vira `position=0`; criar sem marcar nenhuma e conferir que a 1ª vira capa (sem
   regressão); tentar subir um arquivo com extensão inválida e conferir que nada é criado
   e a mensagem de erro aparece; conferir que uma foto grande enviada resulta em arquivo
   salvo muito menor (mesmo teste já validado manualmente); conferir que
   `/admin/catalogo` não tem mais link para `/admin/importar-catalogo`.

"""Módulo Core de Impressões e Acervo 3D (feature 200).

Sem blueprint Jinja: o módulo nasceu já na arquitetura desacoplada (Princípio III), então só
existe o núcleo de negócio (`impressoes3d_ops.py`), consumido pelos endpoints JSON em
`app/api/impressoes3d_read.py` e `app/api/impressoes3d_write.py`.

Nota de nomenclatura: a spec pedia `app/3d_impressions/3d_ops.py`, mas identificadores Python não
podem começar com dígito (`import app.3d_impressions` é erro de sintaxe) — daí `impressoes3d`.
As URLs públicas seguem exatamente o pedido: `/api/3d/acervo`, `/api/3d/fila`,
`/api/events/<id>/3d-gifts`.
"""

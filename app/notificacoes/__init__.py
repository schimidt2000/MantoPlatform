"""Notificações internas (feature 272) — o aviso deixa de ser e-mail e passa a morar no ERP.

Só `notificacoes_ops` mora aqui: emissão (catálogo de `kind`, destinatários por papel, dedupe no
banco), leitura da caixa do usuário e retenção. Endpoints em `app/api/notificacoes_read.py` e
`app/api/notificacoes_write.py`.
"""

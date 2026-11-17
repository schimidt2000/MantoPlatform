"""A recusa do núcleo das Conversas, com o código que a tela compara (features 325 e 328).

Mora fora de `envio_ops` para `equipe_ops` e `respostas_ops` recusarem do mesmo jeito sem importar o
envio (o envio é que importa a equipe). `EnvioRecusado` herda daqui, e o endpoint converte qualquer
`Recusa` no envelope de `json_error`.
"""

from __future__ import annotations


class Recusa(Exception):
    """Recusa do núcleo, com o código que a tela compara e o status HTTP."""

    def __init__(
        self, codigo: str, mensagem: str, status: int, fields: dict[str, str] | None = None
    ) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status
        self.fields = fields or {}


def campo(nome: str, mensagem: str) -> Recusa:
    """A recusa 422 ``invalido`` apontada num campo do formulário."""
    return Recusa("invalido", mensagem, 422, {nome: mensagem})

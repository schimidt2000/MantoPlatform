"""Compatibilidade do link de avaliação da cliente (features 130, 164 e 241).

Sobrou uma rota só, e ela **não some nunca**: `/avaliar/<token>` é o endereço que a comercial
copia e cola no WhatsApp desde a feature 130, o token não expira e não há como recolher um link já
enviado. Todo link em circulação continua entrando por aqui.

A avaliação em si é React (`/catalogo/avaliar/:token`, feature 164) sobre `/api/avaliar/<token>`.
As etiquetas e a regra de qual conjunto aparece por nota vivem em `feedback_ops` — é de lá que a
API e o CRM de clientes importam, e é o que permitiu esta superfície Jinja ser desmontada sem
tocar em regra de negócio.
"""

from __future__ import annotations

from flask import Blueprint, redirect

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/avaliar/<token>", methods=["GET"])
def avaliar(token: str):
    """Manda a cliente para a página React de avaliação, preservando o token.

    Redirect **relativo** de propósito: sai pelo mesmo host público, o browser reentra em
    `frontend/server.js` e `/catalogo/*` cai no bundle da vitrine — que roda com
    `basename="/catalogo"` (`apps/public/src/App.tsx`), daí o caminho ter esse prefixo. Uma URL
    absoluta montada aqui pegaria o Host do serviço backend, porque o proxy usa `changeOrigin`.

    302 e não 301: o navegador não memoriza, então o destino continua sendo nosso para mudar.
    """
    return redirect(f"/catalogo/avaliar/{token}", code=302)

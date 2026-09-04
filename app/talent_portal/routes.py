"""Única superfície do Portal do Artista que ainda vive no Flask: servir foto.

O portal é React (`frontend/apps/portal`) consumindo `/api/portal/*`. As 20 rotas Jinja que
existiam aqui (login, primeiro acesso, troca e recuperação de senha, termos, home, histórico,
perfil, mídia, convites, figurino e avaliação) foram removidas na fase 2 da remoção do Jinja
legado — ver `docs/PLANO_REMOCAO_JINJA.md`. Elas já eram inalcançáveis pela porta pública, porque
`frontend/server.js` só repassa `/portal/photo` ao Flask; seguiam respondendo apenas pelo domínio
direto do serviço backend, e com validação **mais fraca** que a da API (o upload de foto do perfil
Jinja conferia só a extensão, sem limite de tamanho).

`/portal/photo/<caminho>` **fica**, e não é legado: é como toda imagem do portal chega ao talento.
A rota `/uploads/<caminho>` exige sessão de *staff* (`@login_required`), então para o talento ela
vira 302 e ícone quebrado — por isso `portal_ops.figurino_sheets_for_event` reescreve `/uploads/...`
para cá, e o filtro `/portal/photo` no `server.js` é casado ANTES do mount do bundle do portal.

A sessão é a mesma dos dois lados: `app/api/portal_auth.py` grava `session["talent_id"]`, a chave
que esta rota confere.
"""

from flask import Blueprint, abort, current_app, send_from_directory, session

from app.catalogo.og_ops import SUBPASTAS_COM_VARIANTE
from app.storage import is_inline_safe

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")

#: Um ano, o mesmo teto de `/uploads` (`app/__init__.py:_CACHE_FOTOS_TALENTO`).
_CACHE_FOTOS = 31_536_000

# Subpastas de `uploads/` que `/portal/photo/<caminho>` pode servir. A rota só checa se existe
# uma sessão de talento — sem esta lista ela entregava a árvore INTEIRA de uploads (documento de
# identidade de OUTRO talento, contrato, comprovante, nota fiscal) ao usuário de menor privilégio
# do sistema. São as origens que o portal renderiza: a foto da ficha de figurino
# (`portal_ops.figurino_sheets_for_event` reescreve `/uploads/...` para cá) e a foto do talento.
PORTAL_PHOTO_SUBFOLDERS = ("figurino_photos", "figurino_thumbs", "talent_photos")


def _is_portal_photo_path(filename: str) -> bool:
    """True se `filename` aponta para uma foto que o portal tem permissão de servir.

    Args:
        filename: Caminho pedido, relativo à raiz de `UPLOAD_FOLDER`
            (ex.: ``figurino_photos/abc.jpg``).

    Returns:
        True apenas para `<subpasta liberada>/<arquivo>`. Rejeita caminho na raiz, travessia
        (``..``) e qualquer outra subpasta.
    """
    parts = [p for p in filename.replace("\\", "/").split("/") if p]
    if len(parts) != 2 or ".." in parts:
        return False
    return parts[0].lower() in PORTAL_PHOTO_SUBFOLDERS


@portal_bp.route("/photo/<path:filename>")
def portal_photo(filename: str):
    """Serve uma foto de figurino ou do talento para quem tem sessão de talento aberta.

    Args:
        filename: Caminho relativo à raiz de uploads, restrito a `PORTAL_PHOTO_SUBFOLDERS`.
    """
    if not session.get("talent_id"):
        abort(403)
    # 404 (e não 403) para não confirmar a existência de um arquivo fora do escopo do portal.
    if not _is_portal_photo_path(filename):
        abort(404)
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    # Mesmo endurecimento de `/uploads` (app/__init__.py): o portal é servido no mesmo domínio
    # da SPA, então arquivo de tipo perigoso sai como anexo e nunca é renderizado inline.
    inline = is_inline_safe(filename)
    resp = send_from_directory(upload_dir, filename, as_attachment=not inline)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    if not inline:
        resp.headers["Content-Type"] = "application/octet-stream"
    if filename.replace("\\", "/").split("/", 1)[0].lower() in SUBPASTAS_COM_VARIANTE:
        # O portal é aberto no celular, em 4G, e sem isto revalidava TODA foto a cada visita —
        # o mesmo defeito que a 268 corrigiu no catálogo e a 270 nas fotos de talento, aqui
        # ainda de pé. `immutable` é seguro pelo mesmo motivo: o nome é o UUID de `save_file`,
        # então trocar a foto troca a URL. `figurino_thumbs` (legado do Drive) fica fora — lá o
        # arquivo pode ser regravado no mesmo caminho pelo sync.
        resp.headers["Cache-Control"] = f"private, max-age={_CACHE_FOTOS}, immutable"
    return resp

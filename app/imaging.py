"""Decodificação de imagem — o único lugar que abre um arquivo de imagem no sistema.

Antes deste módulo havia **quatro** decodificadores independentes (`storage._compress_image`,
`og_ops._decode_opaque`, `cli._compress_bytes` e `figurino_ops.rotate_figurino_photo`), cada um com
o seu `Image.open` e o seu `exif_transpose`. Registrar o opener do HEIF em três deles e esquecer o
quarto é o tipo de erro que só aparece meses depois, quando alguém sobe uma foto de iPhone numa tela
e ela fica invisível — que foi exatamente o furo da feature 292.

Puro de propósito: **não importa `flask`**. `og_ops` se declara sem dependência do app e os scripts
de recuperação nem sempre criam um contexto — este módulo precisa servir aos dois.
"""
from __future__ import annotations

import io
import logging
from typing import Any, BinaryIO

logger = logging.getLogger(__name__)

#: Formatos que o navegador NÃO renderiza: aceitá-los sem converter é gravar um arquivo invisível.
#: Quando a conversão de um destes falha, o certo é recusar o upload — nunca guardar o original.
EXTS_QUE_EXIGEM_CONVERSAO: frozenset[str] = frozenset(
    {".heic", ".heif", ".avif", ".bmp", ".tif", ".tiff"}
)

#: `None` = ainda não tentamos registrar. Depois vira `True`/`False` e não se tenta de novo.
_HEIF_REGISTRADO: bool | None = None


def suporte_heif() -> bool:
    """Registra o opener do `pillow-heif` (uma vez) e diz se HEIC/HEIF podem ser abertos.

    Returns:
        ``True`` quando a biblioteca está no ambiente e o opener foi registrado; ``False`` quando
        ela não está instalada — caso em que `abrir()` devolve ``None`` para arquivos HEIC.
    """
    global _HEIF_REGISTRADO
    if _HEIF_REGISTRADO is None:
        try:
            from pillow_heif import register_heif_opener

            register_heif_opener()
            _HEIF_REGISTRADO = True
        except ImportError:
            logger.warning("pillow-heif ausente: fotos .heic/.heif não serão convertidas")
            _HEIF_REGISTRADO = False
    return _HEIF_REGISTRADO


def abrir(origem: BinaryIO | bytes) -> Any:
    """Abre uma imagem já com a rotação EXIF corrigida (foto de celular chega deitada).

    Args:
        origem: Objeto de arquivo posicionável ou os bytes crus.

    Returns:
        Um ``PIL.Image.Image``, ou ``None`` quando os bytes não são uma imagem que este ambiente
        consegue decodificar. **Nunca levanta** — quem chama decide se isso é um erro do usuário
        (formato que exige conversão) ou apenas uma otimização que não rolou (JPEG corrompido).
    """
    suporte_heif()
    try:
        from PIL import Image, ImageOps

        fp = io.BytesIO(origem) if isinstance(origem, bytes) else origem
        if not isinstance(origem, bytes):
            fp.seek(0)
        return ImageOps.exif_transpose(Image.open(fp))
    except Exception as exc:  # noqa: BLE001 — imagem ilegível não pode derrubar quem chamou
        logger.warning("imaging: falha ao decodificar (%s)", exc)
        return None


def para_rgb(img: Any) -> Any:
    """Achata transparência sobre branco e devolve a imagem em RGB (JPEG não tem canal alfa)."""
    from PIL import Image

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        flat = Image.new("RGB", img.size, (255, 255, 255))
        flat.paste(img, mask=img.getchannel("A"))
        return flat
    return img if img.mode == "RGB" else img.convert("RGB")


def tem_transparencia_real(img: Any) -> bool:
    """True se a imagem tem pixel de fato transparente — e não só um canal alfa todo opaco."""
    if img.mode != "RGBA":
        return False
    return img.getchannel("A").getextrema()[0] < 255

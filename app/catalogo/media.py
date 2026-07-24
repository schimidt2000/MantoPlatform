"""Classificação e normalização de URLs de vídeo externo do catálogo (feature 185).

Função pura (sem `request`/`render_template`), reusada por `app/admin/catalog_ops.py` e
`app/admin/catalog_character_ops.py` para validar `video_url` antes de salvar, e pelo frontend
via o campo `video_kind` retornado pela API (nunca reimplementado no cliente).
"""

from __future__ import annotations

import re
from typing import Literal

VideoKind = Literal["mp4", "drive", "vimeo"]

_DRIVE_PATTERN = re.compile(
    r"^https://drive\.google\.com/(file/d/[\w-]+|open\?id=[\w-]+|uc\?.*id=[\w-]+)", re.IGNORECASE
)
_VIMEO_PATTERN = re.compile(
    r"^https://(player\.)?vimeo\.com/(video/)?\d+", re.IGNORECASE
)
_MP4_PATTERN = re.compile(r"^https://\S+\.mp4(\?\S*)?$", re.IGNORECASE)


def classify_video_url(url: str | None) -> VideoKind | None:
    """Classifica uma URL de vídeo externo em `"mp4"`, `"drive"`, `"vimeo"` ou `None`.

    `None` cobre tanto URL vazia/ausente quanto formato não reconhecido — quem chama decide se
    isso é um erro de validação (cadastro) ou uma mídia a ignorar silenciosamente (vitrine
    pública, ver Edge Cases de `specs/185-catalogo-vitrine-completo/spec.md`).

    Args:
        url: URL de vídeo informada pelo staff, ou `None`/string vazia.

    Returns:
        O tipo de mídia reconhecido, ou `None` se vazia ou não reconhecida.
    """
    clean = (url or "").strip()
    if not clean:
        return None
    if _DRIVE_PATTERN.match(clean):
        return "drive"
    if _VIMEO_PATTERN.match(clean):
        return "vimeo"
    if _MP4_PATTERN.match(clean):
        return "mp4"
    return None


def normalize_video_url(url: str | None) -> str | None:
    """Normaliza uma URL de vídeo do Google Drive para o formato de conteúdo direto.

    Links de compartilhamento (`/file/d/<ID>/view`) viram `uc?export=download&id=<ID>`, único
    formato que funciona como `src` de um elemento `<video>` nativo (ver
    `specs/185-catalogo-vitrine-completo/research.md` §1). URLs de outros provedores, ou já no
    formato normalizado, retornam inalteradas.

    Args:
        url: URL de vídeo já validada por `classify_video_url`.

    Returns:
        A URL normalizada, ou a URL original se não for do Google Drive / já normalizada.
    """
    clean = (url or "").strip()
    if not clean:
        return None
    match = re.match(r"^https://drive\.google\.com/file/d/([\w-]+)", clean, re.IGNORECASE)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    match = re.match(r"^https://drive\.google\.com/open\?id=([\w-]+)", clean, re.IGNORECASE)
    if match:
        file_id = match.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return clean

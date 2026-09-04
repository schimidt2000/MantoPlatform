"""Guarda de regressão: nenhuma foto de talento ou figurino pode ser um `<img>` cru (feature 292).

O `<img>` do navegador não tem estado de erro visível — quando o `src` responde 404 ele desenha o
ícone de imagem quebrada e pronto. Depois da migração para o Render isso deixou de ser teórico:
centenas de linhas do banco apontam para arquivos que não voltaram do volume antigo, e cada uma
virava um quadrado cinza numa tela de trabalho.

O conserto foi o componente `<Foto>` (`@manto/ui`), que cai para um fallback no `onError`. Este
script existe para o 43º `<img>` do repositório não nascer sem ele.

Rodar:
    python specs/292-fotos-que-somem/check_img_sem_fallback.py

Sai com código 1 quando encontra um `<img>` cru nas superfícies vigiadas — é isso que faz dele um
portão de CI, e não um relatório.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / "frontend"

#: Superfícies onde uma foto que sumiu tem de virar iniciais, e não quadrado quebrado. O catálogo
#: público, a Revisão de Mídia e a produção de figurino ficam de fora **por escopo da 292**, não
#: por serem imunes — quando entrarem, basta acrescentar o caminho aqui.
VIGIADOS = (
    "apps/internal/src/components/TalentMosaic.tsx",
    "apps/internal/src/components/EventDetail/CastingSection.tsx",
    "apps/internal/src/components/EventDetail/FigurinoSection.tsx",
    "apps/internal/src/components/EventDetail/TalentPicker.tsx",
    "apps/internal/src/components/EventFormBlocks/ElencoBlock.tsx",
    "apps/internal/src/components/FigurinoPicker.tsx",
    "apps/internal/src/pages/TalentDetailPage.tsx",
    "apps/internal/src/pages/FigurinoListPage.tsx",
    "apps/internal/src/pages/FigurinoFormPage.tsx",
    "apps/internal/src/pages/Fila3DPage.tsx",
    "apps/portal/src",
    "packages/ui/src/components/avatar-thumb.tsx",
)

#: `<img>` cujo `src` é um blob local (`URL.createObjectURL`) não pode 404 — é o arquivo que a
#: pessoa acabou de escolher, ainda na memória do navegador.
ISENTOS = re.compile(r"src=\{preview\}")

IMG = re.compile(r"<img\b")


def arquivos() -> list[Path]:
    """Todos os `.tsx` sob os caminhos vigiados."""
    encontrados: list[Path] = []
    for alvo in VIGIADOS:
        caminho = RAIZ / alvo
        if caminho.is_dir():
            encontrados.extend(sorted(caminho.rglob("*.tsx")))
        elif caminho.is_file():
            encontrados.append(caminho)
    return encontrados


def main() -> int:
    problemas: list[str] = []
    for arquivo in arquivos():
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if IMG.search(linha) and not ISENTOS.search(linha):
                relativo = arquivo.relative_to(RAIZ).as_posix()
                problemas.append(f"  {relativo}:{numero}  {linha.strip()[:80]}")

    if problemas:
        print("<img> sem fallback em superfície de foto de talento/figurino:\n")
        print("\n".join(problemas))
        print(
            "\nUse <Foto src=... fallback={...}> de @manto/ui — ele cai no fallback quando a\n"
            "imagem responde 404, que é o estado de centenas de fotos desde a migração."
        )
        return 1

    print(f"ok: {len(arquivos())} arquivos vigiados, nenhum <img> cru.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

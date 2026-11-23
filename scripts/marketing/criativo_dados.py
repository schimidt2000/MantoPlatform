"""Dados reais para o diretor criativo (feature 357): temas com foto, o que vende e as próximas festas.

Lê a produção em modo somente leitura (a mesma URL do `financeiro`: `.railway-db-url` na raiz do
checkout, ou a variável `MANTO_DB_LEITURA`) e imprime JSON no stdout. Nunca escreve no banco.

Não sai nome de cliente, telefone nem endereço: das festas só a data, a hora, o tipo, os personagens,
o bairro/cidade (fim do endereço) e se há Foto/Vídeo escalado. O pedido de peça vai para um card que a
equipe inteira vê.

Uso (a partir de `scripts/marketing/`):
    ..\\..\\.venv\\Scripts\\python.exe criativo_dados.py --dias 21
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import psycopg

BASE = "https://app.mantoproducoes.com.br"
# Papéis de equipe que aparecem como "personagem" na escala, mas não são tema.
EQUIPE = {
    "coordenador",
    "tecnico de som",
    "tecnico de som (presenca)",
    "maquiador",
    "maquiadora",
    "foto/video",
    "transporte",
    "apresentadora humana",
    "apresentador humano",
    "apresentador disney humano",
}
FOTO_VIDEO = "foto/video"


def _sem_acento(s: str) -> str:
    return (
        "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")
        .lower()
        .strip()
    )


def _url_banco() -> str:
    if os.getenv("MANTO_DB_LEITURA"):
        return os.environ["MANTO_DB_LEITURA"].strip()
    raiz = Path(__file__).resolve().parents[2]
    for candidato in (
        raiz / ".railway-db-url",
        Path(r"C:\Users\schim\Desktop\Manto_Platform\.railway-db-url"),
    ):
        if candidato.exists():
            return candidato.read_text(encoding="utf-8").strip()
    sys.exit("Sem URL de leitura da produção (.railway-db-url ou MANTO_DB_LEITURA).")


def _cidade(local: str | None) -> str:
    """Só bairro/cidade: a rua, o número e o CEP da cliente não vão para o card.

    O `location` vem do Google em formatos variados ("Rua X, 300 - Bairro, Cidade - SP, Brasil",
    "AV ..., 2650. BAIRRO: BOA VISTA - SOROCABA", "01455-040, Brasil", nome de buffet). Fica o que vem
    depois do último número de porta, sem CEP; sobrando nada, fica vazio.
    """
    texto = local or ""
    if "BAIRRO:" in texto.upper():
        texto = texto[texto.upper().rindex("BAIRRO:") + len("BAIRRO:") :]
    else:
        partes = [p.strip() for p in texto.split(",") if p.strip()]
        texto = ", ".join(partes[-2:]) if len(partes) > 1 else (partes[0] if partes else "")
    texto = re.sub(r"\b\d{5}-?\d{3}\b", "", texto)  # CEP
    texto = re.sub(r"^\s*\d+[\w.\-]*\s*[-–.]?\s*", "", texto)  # número de porta no começo
    if re.search(r"\b(rua|r\.|av\.?|avenida|alameda|estrada|rodovia)\b", texto, re.IGNORECASE):
        return ""
    return texto.strip(" ,.-")[:60]


def _situacao(origem: str, liberado: str, sugestao: str | None) -> str:
    """Em que pé está o tema para anúncio. Só "liberado" entra em peça sem depender de ninguém."""
    if liberado == "sim":
        return "liberado"
    if origem == "autoral":
        return "autoral, falta liberar"
    if sugestao == "autoral":
        return "sugestão autoral, falta confirmar e liberar"
    return "sem classificação, falta classificar e liberar"


def temas(cur) -> list[dict]:
    """Todo tema que não é licenciado (nem sugerido como licenciado), com a situação e as fotos."""
    cur.execute(
        """
        SELECT c.id, c.name, c.slug, c.licenca_origem, c.liberado_anuncio, c.licenca_sugestao,
               array_remove(array_agg(i.url ORDER BY i.position, i.id), NULL)
        FROM catalog_items c LEFT JOIN catalog_item_images i ON i.item_id = c.id
        WHERE c.is_active
          AND (c.liberado_anuncio = 'sim'
               OR (c.licenca_origem <> 'licenciado' AND coalesce(c.licenca_sugestao, '') <> 'licenciado'))
        GROUP BY c.id ORDER BY (c.liberado_anuncio = 'sim') DESC, c.name
        """
    )
    saida = []
    for id_, nome, slug, origem, liberado, sugestao, fotos in cur.fetchall():
        saida.append(
            {
                "id": id_,
                "nome": nome,
                "situacao": _situacao(origem, liberado, sugestao),
                "pagina": f"{BASE}/catalogo/{slug}",
                "fotos": [f"{BASE}{u}" if u.startswith("/") else u for u in (fotos or [])][:8],
            }
        )
    return saida


def vendidos(cur, dias: int = 120) -> list[dict]:
    """Personagens mais escalados nos eventos dos últimos `dias` (sem papéis de equipe).

    Mostra o que a cliente pede; boa parte é licenciado e não vai para anúncio — serve para saber
    o que a vendedora vai oferecer na conversa, não o que a peça mostra.
    """
    cur.execute(
        """
        SELECT er.character_name, count(DISTINCT e.id)
        FROM event_roles er JOIN calendar_events e ON e.id = er.event_id
        WHERE e.start_at >= now() - make_interval(days => %s) AND e.start_at < now()
          AND e.cancelled_at IS NULL AND coalesce(e.event_type, '') <> 'ENSAIO'
        GROUP BY 1 ORDER BY 2 DESC
        """,
        (dias,),
    )
    return [
        {"personagem": nome, "eventos": n}
        for nome, n in cur.fetchall()
        if _sem_acento(nome) not in EQUIPE
    ][:40]


def proximas(cur, dias: int, nomes_de_tema: list[str]) -> list[dict]:
    """Próximas festas: quando, onde (cidade) e com quem — para captar material novo."""
    cur.execute(
        """
        SELECT e.id, e.start_at, e.event_type, coalesce(e.frente, ''), e.location,
               array_remove(array_agg(DISTINCT er.character_name), NULL)
        FROM calendar_events e LEFT JOIN event_roles er ON er.event_id = e.id
        WHERE e.start_at >= now() AND e.start_at < now() + make_interval(days => %s)
          AND e.cancelled_at IS NULL AND coalesce(e.event_type, '') <> 'ENSAIO'
        GROUP BY e.id ORDER BY e.start_at
        """,
        (dias,),
    )
    temas_sa = [(t, _sem_acento(t)) for t in nomes_de_tema]
    saida = []
    for id_, inicio, tipo, frente, local, papeis in cur.fetchall():
        papeis = papeis or []
        personagens = [p for p in papeis if _sem_acento(p) not in EQUIPE]
        # Casamento por nome é só pista: "Angel" casa com "Angel Drink", mas a Angel da festa pode ser a
        # do Stitch (Disney). Quem decide é o diretor criativo, olhando os outros personagens da festa.
        parecidos = sorted(
            {
                t
                for t, tsa in temas_sa
                for p in personagens
                if len(_sem_acento(p)) >= 5 and _sem_acento(p) in tsa
            }
        )
        saida.append(
            {
                "evento_id": id_,
                "quando": inicio.strftime("%d/%m %a %H:%M") if inicio else None,
                "tipo": tipo,
                "frente": frente or None,
                "cidade": _cidade(local),
                "personagens": personagens,
                "foto_video_escalado": any(_sem_acento(p) == FOTO_VIDEO for p in papeis),
                "temas_parecidos_conferir": parecidos,
            }
        )
    return saida


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dias", type=int, default=21, help="janela das próximas festas")
    args = parser.parse_args()
    with psycopg.connect(_url_banco(), autocommit=True) as conn:
        cur = conn.cursor()
        cur.execute("SET default_transaction_read_only = on")
        lista_temas = temas(cur)
        dados = {
            "temas": lista_temas,
            "mais_vendidos_120_dias": vendidos(cur),
            "proximas_festas": proximas(cur, args.dias, [t["nome"] for t in lista_temas]),
        }
    json.dump(dados, sys.stdout, ensure_ascii=False, indent=1, default=str)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Integração com o Google Maps — fonte única (features 076 e 195).

Reutilizado pela calculadora de orçamento, pelo EducaManto e pelo formulário de eventos, evitando
duplicar a integração com a Distance Matrix API (`distance_km_ida`) e com a Places Autocomplete API
(`address_autocomplete`). A chave nunca sai do servidor: o frontend só fala com os endpoints
`/api/*` que chamam estas funções.
"""
import logging
import math
import os

logger = logging.getLogger(__name__)

#: Mínimo de caracteres antes de consultar o Places — evita queimar quota com 1–2 letras.
AUTOCOMPLETE_MIN_CHARS = 3
#: Teto de sugestões devolvidas ao frontend (o Places já devolve no máximo 5).
AUTOCOMPLETE_MAX_RESULTS = 5


def _api_key() -> str:
    """Chave do Google Maps: ``SiteSetting.google_maps_api_key`` ou ``GOOGLE_MAPS_API_KEY``."""
    from app.models import SiteSetting

    setting = SiteSetting.query.get(1)
    return (setting.google_maps_api_key if setting else "") or os.getenv("GOOGLE_MAPS_API_KEY", "")


def distance_km_ida(endereco: str):
    """Distância de carro (só ida) do endereço-base da Manto até ``endereco``.

    Origem = ``SiteSetting.manto_address``; chave da API = ``SiteSetting.google_maps_api_key`` ou
    a variável de ambiente ``GOOGLE_MAPS_API_KEY``. O valor é arredondado para cima (km inteiro).

    Args:
        endereco: Endereço de destino informado pelo usuário.

    Returns:
        Tupla ``(km_ida, error, http_status)``. Em sucesso: ``(int, None, 200)``. Em erro:
        ``(None, "mensagem amigável", status_http)``.
    """
    from app.models import SiteSetting

    setting = SiteSetting.query.get(1)
    api_key = _api_key()
    if not api_key:
        return None, "Google Maps não configurado. Configure a API Key em Admin → Configurações.", 503

    origin = setting.manto_address if setting and setting.manto_address else ""
    if not origin:
        return None, "Endereço da Manto não configurado em Configurações.", 503

    endereco = (endereco or "").strip()
    if not endereco:
        return None, "Endereço não informado.", 400

    try:
        import googlemaps

        gmaps = googlemaps.Client(key=api_key)
        result = gmaps.distance_matrix(origin, endereco, mode="driving")
        element = result["rows"][0]["elements"][0]
        if element["status"] != "OK":
            return None, "Endereço não encontrado pelo Google Maps.", 400
        km_ida = math.ceil(element["distance"]["value"] / 1000)
        return km_ida, None, 200
    except ImportError:
        return None, "Biblioteca googlemaps não instalada.", 503
    except Exception as exc:  # noqa: BLE001 — vira mensagem amigável; erro real fica no retorno
        return None, f"Erro ao consultar Google Maps: {exc}", 500


def address_autocomplete(
    query: str,
    session_token: str | None = None,
) -> tuple[list[dict[str, str]] | None, str | None, int]:
    """Sugestões de endereço do Google Places Autocomplete, restritas ao Brasil (feature 195).

    Proxy de servidor: a ``google_maps_api_key`` fica no backend e o frontend só recebe a lista
    simplificada — nunca a chave. Consultas com menos de ``AUTOCOMPLETE_MIN_CHARS`` caracteres
    devolvem lista vazia sem chamar o Google (economia de quota), o que é sucesso, não erro.

    Args:
        query: Texto digitado pelo usuário.
        session_token: Token de sessão do Places (opcional), que agrupa as teclas digitadas de uma
            mesma busca em uma única cobrança no billing do Google.

    Returns:
        Tupla ``(sugestoes, error, http_status)``. Em sucesso:
        ``([{"description": ..., "place_id": ...}], None, 200)``. Em erro:
        ``(None, "mensagem amigável", status_http)``.
    """
    termo = (query or "").strip()
    if len(termo) < AUTOCOMPLETE_MIN_CHARS:
        return [], None, 200

    api_key = _api_key()
    if not api_key:
        return None, "Google Maps não configurado. Configure a API Key em Admin → Configurações.", 503

    try:
        import googlemaps

        gmaps = googlemaps.Client(key=api_key)
        predictions = gmaps.places_autocomplete(
            termo,
            session_token=session_token,
            language="pt-BR",
            components={"country": ["br"]},
        )
    except ImportError:
        return None, "Biblioteca googlemaps não instalada.", 503
    except Exception as exc:  # noqa: BLE001 — vira mensagem amigável; o erro real vai para o log
        logger.warning("Falha no Places Autocomplete para %r: %s", termo, exc)
        return None, "Não foi possível buscar endereços no Google Maps agora.", 502

    sugestoes = [
        {
            "description": p.get("description", ""),
            "place_id": p.get("place_id", ""),
        }
        for p in (predictions or [])
        if p.get("description")
    ]
    return sugestoes[:AUTOCOMPLETE_MAX_RESULTS], None, 200

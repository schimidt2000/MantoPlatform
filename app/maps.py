"""Cálculo de distância via Google Maps — fonte única (feature 076).

Reutilizado pela calculadora de orçamento e pelo EducaManto, evitando duplicar a integração com a
Distance Matrix API.
"""
import math
import os


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
    api_key = (setting.google_maps_api_key if setting else "") or os.getenv("GOOGLE_MAPS_API_KEY", "")
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

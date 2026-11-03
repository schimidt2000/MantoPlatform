"""Web Push sem biblioteca de Web Push: cifra RFC 8291 (``aes128gcm``) e assinatura VAPID RFC 8292 (feature 332).

Usa só o ``cryptography`` (fixado no ``requirements.txt``) e o ``requests``. A cifra é provada no verify pelo vetor de teste
oficial do RFC 8291 (apêndice A): uma cifra errada não dá erro em lugar nenhum — o aviso simplesmente
não aparece no celular —, então o vetor é a única prova de que ela está certa.

Sem Flask: quem chama passa as chaves e o contato. Não comita nada e não sabe de usuário.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TAMANHO_DO_REGISTRO = 4096
VALIDADE_DO_TOKEN_S = 12 * 3600
TIMEOUT_S = (5, 10)


class AparelhoSumiu(Exception):
    """O serviço de avisos diz que o aparelho não existe mais (404/410): apagar o registro."""


class AvisoFalhou(Exception):
    """O serviço de avisos recusou ou não respondeu. O aviso se perde para este aparelho."""


@dataclass(frozen=True)
class ChavesVapid:
    """O par VAPID da Plataforma (base64url: a privada é o escalar de 32 bytes; a pública, o ponto)."""

    publica: str
    privada: str
    contato: str


def b64_decodificar(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def b64_codificar(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _hmac(chave: bytes, dados: bytes) -> bytes:
    return hmac.new(chave, dados, hashlib.sha256).digest()


def _ponto(chave: ec.EllipticCurvePublicKey) -> bytes:
    return chave.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def ponto_valido(p256dh: str) -> bool:
    """A chave do aparelho é um ponto P-256 de verdade? 65 bytes que não estão na curva quebrariam a
    cifra só na hora do aviso."""
    try:
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64_decodificar(p256dh))
    except (ValueError, TypeError):
        return False
    return True


def par_valido(publica: str, privada: str) -> bool:
    """A chave pública é a da privada? Par colado errado no painel = todo aviso recusado (401/403)."""
    try:
        escalar = int.from_bytes(b64_decodificar(privada), "big")
        derivada = ec.derive_private_key(escalar, ec.SECP256R1()).public_key()
    except (ValueError, TypeError):
        return False
    return b64_codificar(_ponto(derivada)) == publica


def gerar_chaves() -> tuple[str, str]:
    """Um par VAPID novo: (pública, privada), em base64url."""
    privada = ec.generate_private_key(ec.SECP256R1())
    escalar = privada.private_numbers().private_value.to_bytes(32, "big")
    return b64_codificar(_ponto(privada.public_key())), b64_codificar(escalar)


def cifrar(
    dados: bytes,
    p256dh: str,
    auth: str,
    *,
    privada_efemera: ec.EllipticCurvePrivateKey | None = None,
    sal: bytes | None = None,
) -> bytes:
    """O corpo cifrado do aviso (RFC 8291 sobre o RFC 8188, um registro só).

    ``privada_efemera`` e ``sal`` só são passados pelo verify (vetor de teste); no uso real, são novos
    a cada aviso.
    """
    publica_do_aparelho = b64_decodificar(p256dh)
    efemera = privada_efemera or ec.generate_private_key(ec.SECP256R1())
    publica_efemera = _ponto(efemera.public_key())
    aparelho = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), publica_do_aparelho)
    segredo = efemera.exchange(ec.ECDH(), aparelho)
    prk_da_chave = _hmac(b64_decodificar(auth), segredo)
    info = b"WebPush: info\x00" + publica_do_aparelho + publica_efemera
    ikm = _hmac(prk_da_chave, info + b"\x01")
    sal = sal or os.urandom(16)
    prk = _hmac(sal, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    cifrado = AESGCM(cek).encrypt(nonce, dados + b"\x02", None)  # \x02 = último registro
    cabecalho = sal + TAMANHO_DO_REGISTRO.to_bytes(4, "big") + bytes([len(publica_efemera)])
    return cabecalho + publica_efemera + cifrado


def _token_vapid(endpoint: str, chaves: ChavesVapid) -> str:
    """O JWT ES256 do RFC 8292: ``aud`` = origem do serviço de avisos, ``exp`` em 12 h, ``sub`` = contato."""
    partes = urlsplit(endpoint)
    cabecalho = b64_codificar(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    corpo = {
        "aud": f"{partes.scheme}://{partes.netloc}",
        "exp": int(time.time()) + VALIDADE_DO_TOKEN_S,
        "sub": chaves.contato,
    }
    assinado = f"{cabecalho}.{b64_codificar(json.dumps(corpo).encode())}".encode()
    privada = ec.derive_private_key(
        int.from_bytes(b64_decodificar(chaves.privada), "big"), ec.SECP256R1()
    )
    r, s = decode_dss_signature(privada.sign(assinado, ec.ECDSA(hashes.SHA256())))
    return f"{assinado.decode()}.{b64_codificar(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"


def enviar(
    aparelho: dict[str, str], corpo: dict, chaves: ChavesVapid, *, ttl: int, urgencia: str
) -> None:
    """Cifra e entrega o aviso a um aparelho (``{"endpoint", "p256dh", "auth"}``).

    Raises:
        AparelhoSumiu: 404/410 — o registro deve ser apagado.
        AvisoFalhou: outra recusa ou falha de rede.
    """
    dados = cifrar(json.dumps(corpo).encode("utf-8"), aparelho["p256dh"], aparelho["auth"])
    cabecalhos = {
        "Authorization": f"vapid t={_token_vapid(aparelho['endpoint'], chaves)}, k={chaves.publica}",
        "Content-Encoding": "aes128gcm",
        "Content-Type": "application/octet-stream",
        "TTL": str(ttl),
        "Urgency": urgencia,
    }
    try:
        resposta = requests.post(
            aparelho["endpoint"], data=dados, headers=cabecalhos, timeout=TIMEOUT_S
        )
    except requests.RequestException as exc:
        raise AvisoFalhou(f"rede: {exc}") from exc
    if resposta.status_code in (404, 410):
        raise AparelhoSumiu(f"HTTP {resposta.status_code}")
    if resposta.status_code >= 300:
        raise AvisoFalhou(f"HTTP {resposta.status_code}: {resposta.text[:200]}")

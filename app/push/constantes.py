"""Constantes dos avisos no celular (feature 332). Textos para a equipe pelo Princípio XV."""

# O serviço de avisos guarda o aviso até 1 dia se o celular estiver desligado.
TTL_S = 24 * 3600
URGENCIA_MENSAGEM = "high"
URGENCIA_AVISO = "normal"
NAVEGADOR_MAXIMO = 255
ERRO_MAXIMO = 300
ENDPOINT_MAXIMO = 2048

# O endereço do aparelho vem do navegador e a Plataforma faz POST nele: só os serviços de aviso
# conhecidos (Chrome/Android, Firefox, Edge/Windows, Safari/iPhone), para o registro não virar um
# jeito de o servidor chamar um endereço qualquer (SSRF).
SERVICOS_DE_AVISO = (
    "fcm.googleapis.com",
    ".push.services.mozilla.com",
    ".notify.windows.com",
    ".push.apple.com",
)

TEXTO_DESLIGADO = "Os avisos no celular ainda não foram configurados."
TEXTO_APARELHO_INVALIDO = "Não foi possível registrar este aparelho. Tente novamente."


def tag_da_conversa(conversa_id: int) -> str:
    """Avisos da mesma conversa se substituem no celular em vez de empilhar."""
    return f"conversa-{conversa_id}"


def tag_da_espera(conversa_id: int) -> str:
    return f"espera-{conversa_id}"


def tag_da_transferencia(conversa_id: int) -> str:
    return f"transferida-{conversa_id}"


def tag_do_lembrete(conversa_id: int) -> str:
    """Feature 349: o "Lembrar amanhã" e a régua do orçamento parado da mesma conversa se substituem."""
    return f"lembrete-{conversa_id}"

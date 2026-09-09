"""Conversão de vídeo para a web e aplicação da moldura (feature 297).

Núcleo puro: recebe caminhos de arquivo e devolve informação sobre vídeo. Não sabe o que é uma tag
NFC, não toca no banco, não conhece `flask.request`. Fica separado de `nfc_ops.py` justamente por
isso — a Loja de Interações Virtuais (feature 205) tem exatamente o mesmo problema de peso e pode
reusar este módulo sem arrastar nada de tags junto.

POR QUE ESTE MÓDULO EXISTE. Até 09/09/2026 o byte que a equipe subia era o byte que ficava no
disco. Como a equipe grava no celular, isso significava arquivos crus de câmera: 4K, até 76 Mbps,
147 MB para 16 segundos. Nenhum deles estava corrompido; eles apenas não cabem numa rede móvel, e
a cliente que encostava o telefone na luminária ficava olhando uma barra de carregamento parada.

O `ffmpeg` NÃO é dependência declarada. Ele vem da imagem base do runtime Python do Render
(`/usr/bin/ffmpeg`, versão 5.1.9, com `libx264`, `aac`, `scale`, `overlay` e `scale2ref`) e não
está no `render.yaml`. Se um dia sumir, `ffmpeg_disponivel()` devolve False e quem chama entrega o
vídeo como veio, com o motivo registrado — nunca se perde o arquivo por falta de conversor.
Dívida registrada em `docs/05`.
"""

import json
import os
import shutil
import subprocess

from flask import current_app

from app.constants import (
    NFC_VIDEO_AUDIO_BITRATE,
    NFC_VIDEO_BUFSIZE,
    NFC_VIDEO_CRF,
    NFC_VIDEO_LARGURA_MAXIMA,
    NFC_VIDEO_MAXRATE,
    NFC_VIDEO_TIMEOUT_SEGUNDOS,
)

#: Prioridade mínima do escalonador. O contêiner do Render tem UMA CPU, compartilhada com os três
#: workers do gunicorn que atendem o ERP: sem isto, uma conversão deixa o sistema inteiro lento
#: enquanto dura. Com isto, o worker web ganha a CPU sempre que acorda e o ffmpeg usa o que sobra.
_NICE = 19
#: Uma linha de execução só, pelo mesmo motivo.
_THREADS = 1


class VideoIndisponivel(Exception):
    """Não foi possível sondar ou converter o vídeo.

    Quem chama decide o que fazer: no fluxo da tag NFC, o vídeo é entregue como veio e a entrega
    guarda a mensagem em `processing_error`.
    """


class InfoVideo:
    """O que se sabe de um arquivo de vídeo depois de sondá-lo."""

    def __init__(
        self, largura: int, altura: int, duracao_segundos: float, tamanho_bytes: int
    ) -> None:
        self.largura = largura
        self.altura = altura
        self.duracao_segundos = duracao_segundos
        self.tamanho_bytes = tamanho_bytes

    @property
    def em_pe(self) -> bool:
        """True quando o vídeo é mais alto que largo (retrato)."""
        return self.altura > self.largura

    def __repr__(self) -> str:  # pragma: no cover — só para log e depuração
        mb = self.tamanho_bytes / (1024 * 1024)
        return (
            f"<InfoVideo {self.largura}x{self.altura} "
            f"{self.duracao_segundos:.1f}s {mb:.1f}MB>"
        )


def _caminho_binario(nome: str) -> str | None:
    """Onde está o `ffmpeg`/`ffprobe`, ou None se não houver.

    Aceita sobreposição por config (`FFMPEG_BIN`/`FFPROBE_BIN`) para a máquina de desenvolvimento,
    onde o binário pode estar num caminho do WinGet fora do PATH do serviço.
    """
    chave = f"{nome.upper()}_BIN"
    try:
        configurado = current_app.config.get(chave)
    except RuntimeError:  # fora de contexto de aplicação (uso do módulo em script solto)
        configurado = None
    if configurado and os.path.exists(configurado):
        return configurado
    return shutil.which(nome)


def ffmpeg_disponivel() -> bool:
    """True quando dá para converter vídeo nesta máquina."""
    return bool(_caminho_binario("ffmpeg") and _caminho_binario("ffprobe"))


def encoder_disponivel() -> str:
    """Qual encoder H.264 usar.

    A produção tem `libx264`. Esta máquina de desenvolvimento tem um ffmpeg LGPL que **não** tem
    `libx264` — só `libopenh264` (pegadinha registrada na feature 265). O código escolhe sozinho
    em vez de fixar um dos dois, senão o verify não roda aqui ou a produção fica com o encoder pior.
    """
    ffmpeg = _caminho_binario("ffmpeg")
    if not ffmpeg:
        raise VideoIndisponivel("O ffmpeg não está disponível nesta máquina.")
    try:
        saida = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise VideoIndisponivel(f"Não foi possível consultar o ffmpeg: {exc}") from exc
    if " libx264 " in saida:
        return "libx264"
    if " libopenh264 " in saida:
        return "libopenh264"
    raise VideoIndisponivel("O ffmpeg desta máquina não tem encoder H.264.")


def _prefixo_de_prioridade() -> list[str]:
    """`nice -n 19` no Linux do Render; nada no Windows.

    O teste de `os.name` é deliberado e não é redundante com o `which`: o Git para Windows instala
    um `nice.EXE` do MSYS que o `shutil.which` encontra, e ele **embaralha os argumentos** ao
    repassá-los — a cadeia de filtros chega quebrada e o ffmpeg responde "Filter not found". Levou
    uma hora para achar isso; não troque por um `which` solto.
    """
    if os.name != "posix":
        return []
    nice = shutil.which("nice")
    return [nice, "-n", str(_NICE)] if nice else []


def sondar(caminho: str) -> InfoVideo:
    """Lê dimensões, duração e peso de um arquivo de vídeo, sem decodificá-lo."""
    ffprobe = _caminho_binario("ffprobe")
    if not ffprobe:
        raise VideoIndisponivel("O ffprobe não está disponível nesta máquina.")
    if not os.path.exists(caminho):
        raise VideoIndisponivel("O arquivo de vídeo não existe.")
    try:
        proc = subprocess.run(
            [
                ffprobe, "-v", "error", "-print_format", "json",
                "-show_streams", "-show_format", caminho,
            ],
            capture_output=True, text=True, timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise VideoIndisponivel(f"Não foi possível sondar o vídeo: {exc}") from exc
    if proc.returncode != 0:
        raise VideoIndisponivel("O arquivo não parece ser um vídeo válido.")
    try:
        dados = json.loads(proc.stdout)
        video = next(s for s in dados["streams"] if s.get("codec_type") == "video")
    except (ValueError, KeyError, StopIteration) as exc:
        raise VideoIndisponivel("O arquivo não tem faixa de vídeo.") from exc

    largura = int(video.get("width") or 0)
    altura = int(video.get("height") or 0)
    # Vídeo de celular costuma vir com matriz de rotação: 1920x1080 gravado em pé é ANUNCIADO
    # deitado, e só a tag de rotação diz a verdade. O ffmpeg gira sozinho na conversão, então aqui
    # as dimensões precisam ser trocadas para descrever o que a pessoa vê.
    if _rotacao_de(video) in (90, 270):
        largura, altura = altura, largura
    try:
        duracao = float(dados.get("format", {}).get("duration") or 0.0)
    except (TypeError, ValueError):
        duracao = 0.0
    return InfoVideo(largura, altura, duracao, os.path.getsize(caminho))


def _rotacao_de(stream: dict) -> int:
    """Ângulo de rotação declarado na faixa de vídeo, normalizado para 0/90/180/270."""
    bruto = (stream.get("tags") or {}).get("rotate")
    if bruto is None:
        for lado in stream.get("side_data_list") or []:
            if "rotation" in lado:
                bruto = lado["rotation"]
                break
    try:
        return int(abs(float(bruto))) % 360 if bruto is not None else 0
    except (TypeError, ValueError):
        return 0


def montar_filtro(com_moldura: bool, largura_maxima: int) -> list[str]:
    """Os argumentos de filtro do ffmpeg, com ou sem moldura.

    Sem moldura é um `-vf` simples. Com moldura entra o `scale2ref`, que redimensiona a moldura ao
    tamanho EXATO do vídeo já normalizado — é isso que faz uma única moldura servir a qualquer
    vídeo, que era o pedido literal do dono ("ela precisaria se adaptar ao tamanho do vídeo pra
    sempre ficar na borda").

    `setsar=1` normaliza pixel não quadrado (sem ele, vídeo com SAR estranho sai deformado); o
    `-2` na altura garante número par, exigência do `yuv420p`; `format=auto` no `overlay` preserva
    o canal alfa do PNG.
    """
    escala = f"scale='if(gt(iw,{largura_maxima}),{largura_maxima},iw)':-2,setsar=1"
    if not com_moldura:
        return ["-vf", escala]
    cadeia = (
        f"[0:v]{escala}[v0];"
        "[1:v][v0]scale2ref=w=iw:h=ih[mold][v1];"
        "[v1][mold]overlay=0:0:format=auto[vout]"
    )
    return ["-filter_complex", cadeia, "-map", "[vout]", "-map", "0:a?"]


def converter(
    origem: str,
    destino: str,
    *,
    moldura: str | None = None,
    largura_maxima: int = NFC_VIDEO_LARGURA_MAXIMA,
) -> InfoVideo:
    """Converte um vídeo para o formato que qualquer celular toca, opcionalmente com moldura.

    Escreve num arquivo temporário ao lado do destino e só renomeia no fim: se o processo morrer no
    meio (um deploy troca o contêiner sem avisar), o destino nunca fica com um arquivo pela metade.

    O temporário fica na pasta do destino, ou seja, no disco persistente — **nunca** em `/tmp`, que
    no Render é memória RAM e já matou o serviço inteiro por estouro (incidente de 28/08/2026,
    `app/backup_drive.py`).

    Args:
        origem: caminho do arquivo a converter.
        destino: caminho final do arquivo convertido (`.mp4`).
        moldura: caminho de um PNG com transparência, ou None para não aplicar moldura.
        largura_maxima: teto de largura da saída; a altura acompanha a proporção.

    Returns:
        `InfoVideo` do arquivo produzido.

    Raises:
        VideoIndisponivel: sem ffmpeg, com entrada inválida ou com falha na conversão.
    """
    ffmpeg = _caminho_binario("ffmpeg")
    if not ffmpeg:
        raise VideoIndisponivel("O ffmpeg não está disponível nesta máquina.")
    if not os.path.exists(origem):
        raise VideoIndisponivel("O arquivo de origem não existe.")
    com_moldura = bool(moldura and os.path.exists(moldura))

    # Consultado UMA vez: cada chamada roda `ffmpeg -encoders`, e três consultas por conversão
    # seriam três processos a mais disputando a única CPU do contêiner.
    encoder = encoder_disponivel()
    parcial = f"{destino}.parcial"
    comando = [
        *_prefixo_de_prioridade(), ffmpeg, "-hide_banner", "-v", "error", "-y",
        "-i", origem,
    ]
    if com_moldura:
        comando += ["-i", moldura]
    comando += montar_filtro(com_moldura, largura_maxima)
    comando += [
        "-c:v", encoder,
        *_argumentos_de_qualidade(encoder),
        "-pix_fmt", "yuv420p",
        "-threads", str(_THREADS),
        "-c:a", "aac", "-b:a", NFC_VIDEO_AUDIO_BITRATE,
        "-movflags", "+faststart",
        # O contêiner vai explícito porque a saída é um `.parcial`: o ffmpeg deduz o formato pela
        # extensão do arquivo e, sem esta linha, responde "Error opening output files".
        "-f", "mp4",
        parcial,
    ]

    try:
        proc = subprocess.run(
            comando, capture_output=True, text=True,
            timeout=NFC_VIDEO_TIMEOUT_SEGUNDOS, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _apagar(parcial)
        raise VideoIndisponivel("A conversão passou do tempo limite.") from exc
    except OSError as exc:
        _apagar(parcial)
        raise VideoIndisponivel(f"Não foi possível rodar o ffmpeg: {exc}") from exc

    if proc.returncode != 0 or not os.path.exists(parcial) or os.path.getsize(parcial) == 0:
        detalhe = (proc.stderr or "").strip().splitlines()
        motivo = detalhe[-1][:300] if detalhe else "motivo não informado pelo ffmpeg"
        _apagar(parcial)
        raise VideoIndisponivel(f"A conversão falhou: {motivo}")

    # Sonda ANTES de renomear: um arquivo que o ffprobe não lê não pode virar o arquivo entregue.
    info = sondar(parcial)
    os.replace(parcial, destino)
    return InfoVideo(info.largura, info.altura, info.duracao_segundos, os.path.getsize(destino))


def _argumentos_de_qualidade(encoder: str) -> list[str]:
    """Controle de qualidade da saída, conforme o encoder disponível.

    `libx264` aceita `crf` com teto de taxa — o alvo medido é ~15 MB por 30 s de vídeo em pé.
    `libopenh264` (só na máquina de desenvolvimento) não tem `crf`; usa taxa fixa equivalente.
    """
    if encoder == "libx264":
        return [
            "-preset", "veryfast",
            "-crf", str(NFC_VIDEO_CRF),
            "-maxrate", NFC_VIDEO_MAXRATE,
            "-bufsize", NFC_VIDEO_BUFSIZE,
        ]
    return ["-b:v", "4M"]


def _apagar(caminho: str) -> None:
    """Remove um arquivo temporário sem deixar a falha de limpeza mascarar a falha real."""
    try:
        if caminho and os.path.exists(caminho):
            os.remove(caminho)
    except OSError as exc:  # noqa: BLE001 — limpeza é melhor-esforço
        try:
            current_app.logger.warning(f"[video] não removeu o temporário {caminho}: {exc}")
        except RuntimeError:
            pass

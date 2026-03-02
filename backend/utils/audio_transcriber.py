"""
Transcrição de áudio usando OpenAI Whisper.
Baixa áudios do WAHA e converte em texto.
"""
import requests
import tempfile
import os
import sys

from openai import OpenAI
from config import OPENAI_API_KEY, WAHA_API_URL, WAHA_API_KEY


def _corrigir_url_waha(media_url):
    """Converte URL local do WAHA para a URL real do servidor."""
    from urllib.parse import urlparse
    waha_base = WAHA_API_URL.replace('/api', '')

    parsed = urlparse(media_url)
    if parsed.hostname in ('localhost', '127.0.0.1') or parsed.port in (3000, 3001):
        path = parsed.path
        return f"{waha_base}{path}"
    return media_url


def baixar_audio_waha(media_url):
    """Baixa o arquivo de áudio do WAHA e retorna o caminho temporário."""
    try:
        headers = {"X-Api-Key": WAHA_API_KEY}

        if not media_url.startswith("http"):
            media_url = f"{WAHA_API_URL.rstrip('/api')}{media_url}"

        media_url = _corrigir_url_waha(media_url)
        print(f"[audio] Baixando áudio: {media_url[:100]}...", file=sys.stderr)

        response = requests.get(media_url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"[audio] Erro ao baixar: status {response.status_code}", file=sys.stderr)
            return None

        content_type = response.headers.get("Content-Type", "")
        if "ogg" in content_type or "opus" in content_type:
            ext = ".ogg"
        elif "mp4" in content_type or "m4a" in content_type:
            ext = ".m4a"
        elif "mpeg" in content_type or "mp3" in content_type:
            ext = ".mp3"
        elif "webm" in content_type:
            ext = ".webm"
        elif "wav" in content_type:
            ext = ".wav"
        else:
            ext = ".ogg"

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(response.content)
        tmp.close()

        print(f"[audio] Áudio salvo: {tmp.name} ({len(response.content)} bytes, {ext})", file=sys.stderr)
        return tmp.name

    except Exception as e:
        print(f"[audio] Erro ao baixar áudio: {e}", file=sys.stderr)
        return None


def transcrever_audio(caminho_arquivo):
    """Transcreve áudio usando OpenAI Whisper API."""
    try:
        if not OPENAI_API_KEY:
            print("[audio] OPENAI_API_KEY não configurada", file=sys.stderr)
            return None

        client = OpenAI(api_key=OPENAI_API_KEY)

        with open(caminho_arquivo, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt",
                response_format="text"
            )

        texto = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        print(f"[audio] Transcrição: {texto[:100]}...", file=sys.stderr)
        return texto

    except Exception as e:
        print(f"[audio] Erro na transcrição: {e}", file=sys.stderr)
        return None

    finally:
        try:
            os.unlink(caminho_arquivo)
        except OSError:
            pass


def processar_audio_mensagem(media_url):
    """Pipeline completo: baixar áudio → transcrever → retornar texto."""
    caminho = baixar_audio_waha(media_url)
    if not caminho:
        return None

    texto = transcrever_audio(caminho)
    return texto

"""Petit client Wyoming (STT/TTS) pour les mesures : synthese Piper et transcription Whisper, avec chronometrage."""
import asyncio, io, time, wave
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize
from wyoming.audio import AudioStart, AudioChunk, AudioStop
from wyoming.asr import Transcribe, Transcript


async def synth(host, port, text, timeout=120):
    """-> (pcm int16 mono, rate, temps jusqu au 1er son, temps total)"""
    t0 = time.time(); first = None; pcm = bytearray(); rate = 22050
    async with AsyncTcpClient(host, port) as c:
        await c.write_event(Synthesize(text=text).event())
        while True:
            ev = await asyncio.wait_for(c.read_event(), timeout)
            if ev is None: break
            if AudioStart.is_type(ev.type): rate = AudioStart.from_event(ev).rate
            elif AudioChunk.is_type(ev.type):
                if first is None: first = time.time() - t0
                pcm += AudioChunk.from_event(ev).audio
            elif AudioStop.is_type(ev.type): break
    return bytes(pcm), rate, first or 0.0, time.time() - t0


async def transcribe(host, port, pcm16k, lang="fr", timeout=300):
    """pcm int16 mono 16 kHz -> (texte, latence apres la fin de la parole, temps total)"""
    t0 = time.time()
    async with AsyncTcpClient(host, port) as c:
        await c.write_event(Transcribe(language=lang).event())
        await c.write_event(AudioStart(rate=16000, width=2, channels=1).event())
        step = 2048
        for i in range(0, len(pcm16k), step):
            await c.write_event(AudioChunk(rate=16000, width=2, channels=1, audio=pcm16k[i:i + step]).event())
        await c.write_event(AudioStop().event()); t1 = time.time()
        while True:
            ev = await asyncio.wait_for(c.read_event(), timeout)
            if ev is None: return "", time.time() - t1, time.time() - t0
            if Transcript.is_type(ev.type): return Transcript.from_event(ev).text, time.time() - t1, time.time() - t0


def wav_bytes(pcm, rate):
    b = io.BytesIO()
    with wave.open(b, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
    return b.getvalue()

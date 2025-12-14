import os
import json
from vosk import KaldiRecognizer, Model
from pydub import AudioSegment


model = Model("models/vosk/model")


async def convert_ogg_to_wav(input_path: str, output_path: str):
    """Конвертация OGG в WAV формата 16kHz mono"""
    audio = AudioSegment.from_ogg(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_path, format="wav")


async def recognize_speech(audio_path: str) -> str:
    """Распознавание речи с помощью Vosk"""
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(True)

    result = []
    # Используем wave для корректной обработки WAV
    import wave
    with wave.open(audio_path, "rb") as wf:
        # Проверяем параметры аудио
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            raise ValueError("Аудиофайл должен быть в формате WAV: моно, 16 бит, без сжатия.")

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result.append(rec.Result())

    result.append(rec.FinalResult())

    # Собираем все результаты
    texts = []
    for res in result:
        if res:
            jres = json.loads(res)
            if 'text' in jres:
                texts.append(jres['text'])

    return " ".join(texts)


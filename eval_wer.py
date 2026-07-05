"""
eCast — Evaluasi WER (Word Error Rate) via Whisper ASR
Mengukur kualitas pelafalan Edge-TTS dengan cara:
1. TTS men-generate audio dari teks referensi
2. Whisper ASR mentranskripsi audio tersebut
3. Jiwer menghitung WER antara teks referensi dan transkrip Whisper
"""

import os
import sys
import io

# Fix encoding untuk terminal Windows (cp1252)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import re
import csv
import time
import unicodedata
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import whisper
from whisper.normalizers import BasicTextNormalizer, EnglishTextNormalizer
import jiwer
from app.tts_engine import TTSEngine

basic_normalizer = BasicTextNormalizer()
english_normalizer = EnglishTextNormalizer()

# ============================================
# Parameter Pengujian
# ============================================
WHISPER_MODEL = "small"   # ~2GB VRAM, cocok untuk GPU 4GB
CSV_FILENAME = "wer_evaluation_results.csv"

# Dataset pengujian: teks referensi yang akan disuarakan oleh Edge-TTS
# Sengaja dibuat bervariasi (nama daerah, istilah teknis, angka) untuk menguji keakuratan pelafalan
DATASET = {
    "ar": [
        "السلام عليكم ورحمة الله وبركاته",
        "بسم الله الرحمن الرحيم",
        "إن العلم نور والجهل ظلام",
        "المسجد الحرام يقع في مكة المكرمة",
        "قال رسول الله صلى الله عليه وسلم",
    ],
    "id": [
        "Selamat datang di podcast eCast",
        "Ilmu pengetahuan adalah cahaya bagi kehidupan manusia",
        "Universitas Indonesia terletak di kota Depok Jawa Barat",
        "Teknologi kecerdasan buatan berkembang sangat pesat",
        "Buku ini membahas tentang sejarah peradaban Islam",
    ],
    "en": [
        "Welcome to the eCast podcast",
        "Artificial intelligence is transforming the world",
        "The University of Oxford was founded in the year twelve hundred",
        "Machine learning models require large amounts of training data",
        "This book discusses the history of Islamic civilization",
    ],
}


def normalize_text(text: str, lang: str) -> str:
    """
    Normalisasi teks sebelum perbandingan WER.
    Menggunakan rule spesifik untuk Arab, dan normalizer bawaan Whisper untuk Inggris dan lainnya.
    """
    if lang == "ar":
        text = text.lower()
        # Untuk bahasa Arab, hapus harakat/tashkeel (diacritics) terlebih dahulu
        text = re.sub(r'[\u0617-\u061A\u064B-\u0652\u0670]', '', text)
        # Hapus tanda baca Arab dan umum, pertahankan huruf Arab + spasi
        text = re.sub(r'[^\u0600-\u06FF\s]', '', text)
        # Hapus spasi berlebih
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    elif lang == "en":
        return english_normalizer(text)
    else:
        return basic_normalizer(text)


def evaluate_wer():
    results = []

    print("=== Memulai Evaluasi WER (Word Error Rate) via Whisper ASR ===")
    print(f"Model Whisper: {WHISPER_MODEL}")
    print("Memuat model Whisper (mungkin butuh waktu untuk download pertama kali)...")

    # Muat model Whisper
    model = whisper.load_model(WHISPER_MODEL)
    print("Model Whisper berhasil dimuat.\n")

    # Inisiasi TTS Engine
    engine = TTSEngine()
    temp_dir = Path("outputs/temp_wer")
    temp_dir.mkdir(parents=True, exist_ok=True)

    for lang, sentences in DATASET.items():
        print(f"\n--- Bahasa: {lang.upper()} ---")

        for idx, reference_text in enumerate(sentences):
            label = f"  [{idx+1}/{len(sentences)}] Teks #{idx+1}"
            print(label)

            audio_path = temp_dir / f"wer_{lang}_{idx}.mp3"

            try:
                # Tahap 1: Generate audio dari teks referensi menggunakan Edge-TTS
                engine.synthesize_segment(text=reference_text, lang=lang, output_path=audio_path)

                # Tahap 2: Transkripsi audio menggunakan Whisper
                whisper_result = model.transcribe(
                    str(audio_path),
                    language=lang,
                    fp16=False  # Gunakan fp32 agar kompatibel dengan GPU 4GB
                )
                hypothesis_text = whisper_result["text"]

                # Tahap 3: Normalisasi kedua teks
                ref_normalized = normalize_text(reference_text, lang)
                hyp_normalized = normalize_text(hypothesis_text, lang)

                # Tahap 4: Hitung WER (dengan pengaman string kosong)
                if not ref_normalized or not hyp_normalized:
                    print(f"    [SKIP] Teks normalisasi kosong, melewati...")
                    continue
                wer_score = jiwer.wer(ref_normalized, hyp_normalized)

                try:
                    print(f"    Ref : {ref_normalized}")
                    print(f"    Hyp : {hyp_normalized}")
                except Exception:
                    print(f"    Ref : [teks {lang}]")
                    print(f"    Hyp : [transkrip {lang}]")
                print(f"    WER : {wer_score:.2%}")

                results.append({
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Language": lang,
                    "Reference": ref_normalized,
                    "Hypothesis": hyp_normalized,
                    "WER": round(wer_score, 4),
                })

            except Exception as e:
                print(f"    Gagal: {e}")

    # Bersihkan file temporary
    try:
        for f in temp_dir.glob("*.mp3"):
            f.unlink()
        temp_dir.rmdir()
    except Exception as e:
        print(f"Warning: Gagal membersihkan temporary file - {e}")

    # Ringkasan rata-rata WER per bahasa
    print("\n=== Ringkasan Hasil Evaluasi WER ===")
    summary = {}
    for res in results:
        lang = res["Language"]
        if lang not in summary:
            summary[lang] = []
        summary[lang].append(res["WER"])

    for lang, wer_list in summary.items():
        avg_wer = sum(wer_list) / len(wer_list) if wer_list else 0
        print(f"[{lang.upper()}] Rata-rata WER: {avg_wer:.2%}")

    # Ekspor ke CSV
    if results:
        csv_path = os.path.join(os.getcwd(), CSV_FILENAME)
        keys = results[0].keys()
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print(f"\n[OK] Hasil evaluasi berhasil diekspor ke: {csv_path}")


if __name__ == "__main__":
    evaluate_wer()

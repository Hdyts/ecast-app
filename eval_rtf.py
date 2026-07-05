import os
import sys
import time
import csv
from pathlib import Path
from datetime import datetime

# Impor dari eCast
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from pydub import AudioSegment
    from app.tts_engine import TTSEngine
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

NUM_ITERATIONS = 3
CSV_FILENAME = "rtf_evaluation_results.csv"

# Dataset
DATASET = {
    "ar": {
        "Pendek": ["السلام عليكم ورحمة الله وبركاته."],
        "Sedang": ["السلام عليكم.", "كيف حالكم اليوم؟", "أتمنى أن تكونوا بخير."],
        "Panjang": ["الثقافة الإسلامية إرث عظيم.", "العلماء المسلمون ساهموا في مجالات كثيرة.", "ومن أهمها الطب والفلك.", "وأيضاً الرياضيات والفلسفة.", "التسامح هو أساس هذه الثقافة."]
    },
    "id": {
        "Pendek": ["Halo, selamat datang di podcast eCast."],
        "Sedang": ["Halo, selamat datang di podcast eCast.", "Hari ini kita akan membahas sesuatu yang menarik.", "Mari kita dengarkan bersama."],
        "Panjang": ["Halo, selamat datang di podcast eCast.", "Hari ini kita akan membahas sesuatu yang menarik.", "Mari kita dengarkan bersama.", "Banyak hal baru yang bisa kita pelajari.", "Jangan lupa untuk membagikan episode ini."]
    },
    "en": {
        "Pendek": ["Hello, welcome to the eCast podcast."],
        "Sedang": ["Hello, welcome to the eCast podcast.", "Today we are discussing an interesting topic.", "Let's listen together."],
        "Panjang": ["Hello, welcome to the eCast podcast.", "Today we are discussing an interesting topic.", "Let's listen together.", "There are many new things to learn.", "Do not forget to share this episode."]
    }
}

def evaluate_rtf():
    results = []
    
    print("=== Memulai Evaluasi RTF (Real-Time Factor) TTS ===")
    print(f"Iterasi per pengujian: {NUM_ITERATIONS}\n")

    engine = TTSEngine()
    temp_dir = Path("outputs/temp_rtf")
    temp_dir.mkdir(parents=True, exist_ok=True)

    for lang in ["ar", "id", "en"]:
        print(f"\n--- Bahasa: {lang.upper()} ---")
        for size_type, sentences in DATASET[lang].items():
            print(f"  Tingkat Teks: [{size_type}] ({len(sentences)} kalimat)")
            
            for i in range(1, NUM_ITERATIONS + 1):
                print(f"    Iterasi {i}/{NUM_ITERATIONS}...", end="", flush=True)
                
                output_file = temp_dir / f"test_{lang}_{size_type}_{i}.mp3"
                
                t_start = time.time()
                try:
                    # Menggunakan sinkron wrapper dari tts_engine
                    engine.synthesize_podcast(sentences=sentences, lang=lang, output_path=output_file)
                    t_end = time.time()
                    
                    t_processing = t_end - t_start
                    
                    # Cek durasi audio yang dihasilkan
                    audio = AudioSegment.from_file(str(output_file))
                    t_audio = len(audio) / 1000.0  # ms ke detik
                    
                    rtf = t_processing / t_audio if t_audio > 0 else 0
                    
                    print(f" t_proc: {t_processing:.2f}s | t_audio: {t_audio:.2f}s | RTF: {rtf:.3f}")
                    
                    results.append({
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Language": lang,
                        "Text_Size": size_type,
                        "Iteration": i,
                        "Processing_Time_s": round(t_processing, 3),
                        "Audio_Duration_s": round(t_audio, 3),
                        "RTF": round(rtf, 4)
                    })
                    
                except Exception as e:
                    print(f" Gagal: {e}")

    # Menghapus file temporary
    try:
        for f in temp_dir.glob("*.mp3"):
            f.unlink()
        temp_dir.rmdir()
    except Exception as e:
        print(f"Warning: Gagal membersihkan temporary file - {e}")

    # Rata-rata
    print("\n=== Ringkasan Hasil Evaluasi RTF ===")
    summary = {}
    for res in results:
        key = f"{res['Language']}-{res['Text_Size']}"
        if key not in summary:
            summary[key] = []
        summary[key].append(res["RTF"])

    for key, vals in summary.items():
        avg_rtf = sum(vals) / len(vals) if vals else 0
        print(f"[{key}] Rata-rata RTF: {avg_rtf:.4f}")

    # CSV
    if results:
        csv_path = os.path.join(os.getcwd(), CSV_FILENAME)
        keys = results[0].keys()
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print(f"\n[OK] Hasil evaluasi berhasil diekspor ke: {csv_path}")

if __name__ == "__main__":
    evaluate_rtf()

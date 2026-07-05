import os
import sys
import time
import json
import csv
import requests
from datetime import datetime

# Impor konfigurasi proyek eCast (pastikan dijalankan dari root direktori)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.config import OLLAMA_MODEL, OLLAMA_CHAT_URL

# Parameter Pengujian
NUM_ITERATIONS = 5
CSV_FILENAME = "ttft_evaluation_results.csv"

# Variasi Prompt Pengujian
PROMPTS = {
    "Pendek": "Terjemahkan ke bahasa Indonesia: السلام عليكم",
    "Sedang": "Terjemahkan ke bahasa Indonesia: الحمد لله رب العالمين، الرحمن الرحيم، مالك يوم الدين. إياك نعبد وإياك نستعين.",
    "Panjang": "Terjemahkan ke bahasa Indonesia secara profesional: إن الثقافة الإسلامية هي إرث عظيم يتجلى في الفنون والعلوم والأدب. لقد ساهم العلماء المسلمون في تطوير الكثير من المجالات مثل الطب والفلك والرياضيات. ومن أهم ما يميز هذه الثقافة هو التسامح والتعايش مع الثقافات الأخرى."
}

def evaluate_ttft_tps():
    results = []
    
    print(f"=== Memulai Evaluasi TTFT & TPS ===")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Iterasi per prompt: {NUM_ITERATIONS}\n")

    for prompt_type, prompt_text in PROMPTS.items():
        print(f"Menguji Prompt [{prompt_type}]...")
        
        for i in range(1, NUM_ITERATIONS + 1):
            payload = {
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt_text}],
                "stream": True,
                "options": {
                    "temperature": 0.1 # Suhu rendah agar stabil untuk evaluasi throughput
                }
            }

            print(f"  Iterasi {i}/{NUM_ITERATIONS}...", end="", flush=True)
            
            t_start = time.time()
            t_first_token = None
            total_tokens = 0
            
            try:
                response = requests.post(OLLAMA_CHAT_URL, json=payload, stream=True, timeout=120)
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        if t_first_token is None:
                            # Catat waktu persis ketika serpihan data pertama masuk (TTFT)
                            t_first_token = time.time()
                            
                        data = json.loads(line)
                        if data.get("done"):
                            # Mengambil jumlah total kata (token) yang di-generate dari metrik bawaan Ollama
                            total_tokens = data.get("eval_count", 0)
                
                t_end = time.time()
                
                # Kalkulasi Metrik
                if t_first_token:
                    ttft_ms = (t_first_token - t_start) * 1000
                    # Durasi generasi adalah waktu dari token pertama hingga seluruh proses selesai
                    generation_time = t_end - t_first_token
                    
                    if generation_time > 0 and total_tokens > 0:
                        # Dikurang 1 karena token pertama dihitung pada ttft
                        tps = (total_tokens - 1) / generation_time
                    else:
                        tps = 0
                else:
                    ttft_ms = 0
                    tps = 0
                
                print(f" TTFT: {ttft_ms:.2f} ms | TPS: {tps:.2f} tokens/s")
                
                results.append({
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Prompt_Type": prompt_type,
                    "Iteration": i,
                    "TTFT_ms": round(ttft_ms, 2),
                    "Total_Tokens": total_tokens,
                    "TPS": round(tps, 2)
                })
                
            except Exception as e:
                print(f" Gagal terhubung/proses: {e}")
                
    # Menghitung Rata-rata per tipe prompt
    print("\n=== Ringkasan Hasil Evaluasi ===")
    summary = {}
    for res in results:
        ptype = res["Prompt_Type"]
        if ptype not in summary:
            summary[ptype] = {"ttft": [], "tps": []}
        summary[ptype]["ttft"].append(res["TTFT_ms"])
        summary[ptype]["tps"].append(res["TPS"])

    for ptype, vals in summary.items():
        avg_ttft = sum(vals["ttft"]) / len(vals["ttft"]) if vals["ttft"] else 0
        avg_tps = sum(vals["tps"]) / len(vals["tps"]) if vals["tps"] else 0
        print(f"[{ptype}] Rata-rata TTFT: {avg_ttft:.2f} ms | Rata-rata TPS: {avg_tps:.2f} tokens/s")

    # Ekspor ke CSV sesuai permintaan
    if results:
        csv_path = os.path.join(os.getcwd(), CSV_FILENAME)
        keys = results[0].keys()
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
        print(f"\n[OK] Hasil evaluasi berhasil diekspor ke: {csv_path}")

if __name__ == "__main__":
    evaluate_ttft_tps()

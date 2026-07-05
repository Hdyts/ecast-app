# eCast - Sistem Konversi ePub Arab menjadi Podcast Audio Multi-bahasa

eCast adalah sistem web-based otomatis yang mampu mengonversi buku teks berbahasa Arab berekstensi `.epub` menjadi bentuk *podcast* audio multi-bahasa. Sistem ini memanfaatkan LLM lokal (Ollama dengan `qwen2.5:3b`) untuk terjemahan presisi tinggi dan peringkasan, serta Edge-TTS untuk sintesis suara yang natural layaknya *podcast*.

## Fitur Utama
1. **Ekstraksi dan Parsing ePub:** Mengekstrak teks per bab dan membersihkan HTML dari file `.epub`.
2. **Preprocessing Teks Arab:** Membersihkan karakter non-standar, normalisasi huruf/tashkeel, serta segmentasi kalimat pendek.
3. **Penerjemahan Leksikal (LLM-based):** Menerjemahkan bahasa Arab secara akurat menggunakan LLM lokal (Ollama).
4. **Peringkasan Teks:** Meringkas teks panjang menjadi narasi singkat otomatis.
5. **Sintesis Audio Podcast (TTS):** Mengonversi teks menjadi berkas `.mp3` lengkap dengan jeda napas (*silence*) dan normalisasi volume.
6. **Chatbot QA Interaktif:** Fitur tanya jawab seputar materi buku berbasis *System Prompt* dengan LLM.

## Arsitektur Sistem
Arsitektur eCast berlandaskan pada model **Client-Server**:
- **Frontend (Web Client):** Antarmuka berbasis web (HTML, CSS, JavaScript) untuk mengunggah buku, memilih bahasa, mendengarkan audio, dan interaksi *chatbot*.
- **Backend (API Server):** Dibangun dengan **FastAPI** (Python) untuk menangani *endpoint* REST API, unggahan file, dan mendelegasikan alur pemrosesan.
- **AI Engine:** Menggunakan **Ollama (`qwen2.5:3b`)** untuk NLP (Penerjemahan & Peringkasan) dan **Edge-TTS** untuk sintesis audio.
- **Ketergantungan Audio:** Menggunakan library Pydub dan dependensi absolut terhadap FFmpeg dan FFprobe untuk manipulasi audio.

## Prasyarat
- Python 3.8+
- [Ollama](https://ollama.com/) dan model `qwen2.5:3b` yang diunduh lokal.
- [FFmpeg & FFprobe](https://ffmpeg.org/download.html) (Harus terdaftar di Environment Variables/PATH).

## Instalasi
1. Clone repositori ini:
   ```bash
   git clone <repository_url>
   cd ecast
   ```
2. Buat Virtual Environment (opsional namun disarankan):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Untuk Linux/Mac
   venv\Scripts\activate     # Untuk Windows
   ```
3. Install dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```
4. Pastikan layanan Ollama berjalan di latar belakang:
   ```bash
   ollama run qwen2.5:3b
   ```

## Menjalankan Aplikasi
Jalankan server backend FastAPI dengan uvicorn:
```bash
uvicorn app.main:app --reload
```
Atau jalankan skrip utama secara langsung jika tersedia. Server akan berjalan secara *default* di port `8000`.
Akses antarmuka web di browser pada `http://localhost:8000`.

## Alur Kerja (Pipeline)
1. **Upload File:** Pengguna mengunggah buku berformat `.epub` (maksimal 10 MB).
2. **Parsing & Preprocessing:** Dokumen dibersihkan dari tag HTML dan karakter berlebih, lalu disegmentasi.
3. **Pemrosesan Teks:** Sistem memanggil LLM lokal (via Ollama) untuk menerjemahkan atau meringkas teks Arab ke target bahasa.
4. **Sintesis TTS & Audio Assembly:** Hasil terjemahan/ringkasan disuarakan oleh Edge-TTS, lalu disatukan dan diberikan jeda per kalimat beserta normalisasi volume menggunakan FFmpeg & Pydub.
5. **Playback/Download Output:** File akhir berektensi `.mp3` dapat didengarkan atau diunduh oleh pengguna.

## Batasan
- Batas maksimal unggahan `.epub`: 10 MB.
- Kecepatan pemrosesan bergantung penuh pada kekuatan komputasi (CPU/GPU) mesin lokal untuk inferensi Ollama.
- Kapasitas *context window* LLM dibatasi pada ~6000 karakter, yang berakibat pada batasan *chunking* pemrosesan memori saat menggunakan Chatbot atau Summarization.

# Project Scope: eCast

## Latar Belakang & Tujuan
**Latar Belakang:** 
Aksesibilitas buku-buku berbahasa Arab, khususnya bagi non-penutur asli atau mereka yang lebih menyukai format audio, masih terbatas. Proses konversi manual dari teks bahasa Arab ke audio multi-bahasa memakan waktu dan biaya. Diperlukan sebuah sistem otomatis yang dapat mengubah buku teks (ePub) menjadi format audio podcast yang dinamis, natural, dan dapat diakses dalam berbagai bahasa.

**Tujuan:**
Sistem **eCast** bertujuan untuk menyediakan sebuah *pipeline* otomatis yang mampu mengonversi buku berbahasa Arab berekstensi `.epub` menjadi bentuk *podcast* audio multi-bahasa. Sistem ini memanfaatkan model LLM lokal untuk terjemahan presisi tinggi dan peringkasan, serta Edge-TTS untuk menghasilkan sintesis suara yang natural layaknya sebuah podcast.

## Fitur Utama
1. **Ekstraksi dan Parsing ePub:** Mampu membaca file `.epub`, mengekstrak teks per bab, dan membersihkan elemen HTML yang tidak diperlukan.
2. **Preprocessing Teks Arab:** Membersihkan karakter non-standar, menormalisasi teks (seperti standarisasi huruf Arab dan *tashkeel*), serta menyegmentasi teks panjang menjadi kalimat pendek agar aman diproses oleh memori.
3. **Penerjemahan Leksikal (LLM-based):** Menerjemahkan teks bahasa Arab ke bahasa tujuan (seperti Indonesia atau Inggris) secara akurat menggunakan LLM lokal (Ollama dengan model `qwen2.5:3b`).
4. **Peringkasan Teks (*Abstractive Summarization*):** Meringkas teks atau bab buku yang panjang menjadi poin-poin ringkasan menggunakan LLM.
5. **Sintesis Audio Podcast (TTS):** Mengonversi teks terjemahan/ringkasan ke file audio `.mp3` dengan Edge-TTS, yang dilengkapi dengan injeksi jeda (*silence*) antar kalimat dan normalisasi volume suara agar menyerupai ritme pernapasan manusia dalam *podcast*.
6. **Integrasi REST API:** Menyediakan layanan *backend* berbasis FastAPI untuk orkestrasi pemrosesan *file*, terjemahan, pembuatan audio, hingga fitur *chatbot* (tanya jawab berdasarkan konteks dokumen buku).
7. **Pipeline Evaluasi (Opsional):** Dukungan skrip untuk melakukan *fine-tuning* model bahasa dan mengukur evaluasi akurasi metrik terjemahan/suara (seperti BLEU, METEOR, LaBSE, dan WER).

## Target Pengguna
- **Pelajar dan Mahasiswa:** Yang mempelajari literatur bahasa Arab dan ingin memahami materi lewat terjemahan atau ringkasan audio.
- **Penikmat Podcast dan Buku Audio:** Pengguna umum yang lebih suka mendengarkan konten buku secara *multitasking* dalam bahasa ibu mereka.
- **Penyandang Disabilitas Tunanetra:** Yang memerlukan aksesibilitas untuk "membaca" e-book bahasa Arab melalui konversi ke format suara (*audiobook*).
- **Peneliti atau Pengajar:** Yang membutuhkan pemrosesan dokumen bahasa Arab menjadi draf ringkasan atau media dengar secara cepat.

## Batasan Scope
- **Format Input & Output:** Sistem hanya menerima dokumen masukan dengan format `.epub` dan menghasilkan format luaran `.mp3`.
- **Ukuran File:** Maksimal ukuran unggahan dokumen ePub dibatasi sebesar 10 MB.
- **Limitasi Pemrosesan Real-time:** Untuk menghindari beban server atau *timeout*, pemrosesan terjemahan dibatasi (contoh: 50 kalimat per *request*), dan limitasi TTS pada respons *chatbot* dibatasi hingga 20 kalimat.
- **Kapasitas Context Window:** Rangkuman dan fitur *chatbot* sangat bergantung pada batas *context window* LLM (diatur pada ~6000 karakter/token).
- **Ketergantungan Hardware:** Performa terjemahan dan peringkasan menggunakan LLM lokal (Ollama) sangat bergantung pada spesifikasi perangkat keras (CPU/GPU) mesin yang menjalankan sistem.

## Ringkasan Scope
Berikut adalah tabel ringkasan *scope* dari pengembangan proyek eCast:

| Kategori | Keterangan |
| :--- | :--- |
| **Fokus Proyek** | *Pipeline* otomatis konversi ePub Arab ke Podcast Audio multi-bahasa. |
| **Input Sistem** | File `.epub` (Buku berbahasa Arab), maksimal ukuran 10 MB. |
| **Output Sistem** | File `.mp3` (Audio podcast natural dengan jeda dan normalisasi volume). |
| **Teknologi Utama** | Python, FastAPI, Ollama (LLM lokal `qwen2.5:3b`), Edge-TTS, Pydub, FFmpeg. |
| **Fungsi Utama** | Parsing ePub, Preprocessing teks Arab, Penerjemahan teks, Peringkasan (*Summarization*), Text-To-Speech (TTS), API Endpoint. |
| **Batasan (*Constraints*)** | Bergantung spesifikasi perangkat keras lokal untuk memori LLM, pemrosesan kalimat dibatasi per *batch* agar memori aman. |
| **Pengguna** | Siswa/akademisi, penikmat *audiobook*, penyandang tunanetra. |

# Kebutuhan Sistem Web-Based: eCast

Dokumen ini mendeskripsikan spesifikasi dan kebutuhan sistem berbasis web untuk aplikasi **eCast** (Sistem Konversi ePub Arab menjadi Podcast Audio Multi-bahasa).

## 1. Arsitektur Sistem
Arsitektur eCast mengadopsi model **Client-Server** dengan memisahkan antarmuka pengguna (*Frontend*) dan logika pemrosesan data (*Backend*).
- **Frontend (Web Client):** Antarmuka berbasis web (HTML, CSS, JavaScript) yang menyajikan tampilan visual bagi pengguna untuk mengunggah buku ePub, memilih bahasa target, mendengarkan hasil *podcast*, dan berinteraksi dengan fitur *chatbot*.
- **Backend (API Server):** Dibangun menggunakan kerangka kerja **FastAPI** (Python). Bertindak sebagai orkestrator utama yang menangani seluruh *endpoint* REST API, mengatur *file upload*, dan mendelegasikan pemrosesan teks dan audio ke berbagai modul internal.
- **AI Engine (Language & TTS Models):**
  - **Ollama (`qwen2.5:3b`):** Dimanfaatkan sebagai *Large Language Model* (LLM) lokal yang menangani tugas pemrosesan natural leksikal, yakni penerjemahan bahasa (*translation*) presisi tinggi dan pembuatan ringkasan abstrak (*summarization*).
  - **Edge-TTS:** Layanan yang menangani sintesis teks-ke-suara (*Text-To-Speech*) untuk mengonversi hasil teks terjemahan/ringkasan ke dalam bentuk ucapan audio.
- **Data & Storage:** Menggunakan sistem penyimpanan *file* lokal untuk menyimpan unggahan sementara(`.epub` masuk ke direktori `uploads/`), menyimpan *cache* teks sesi pengguna pada memori *runtime* RAM (`_uploaded_files`), dan menyimpan produk konversi akhir `.mp3` (ke dalam direktori `outputs/`).

## 2. Alur Kerja End-to-End (Pipeline)
Berikut adalah alur *pipeline* dari sisi hulu (pengguna mengunggah file) ke hilir (keluaran audio):
1. **Upload File:** Pengguna mengunggah *file* buku berbahasa Arab (`.epub`) melalui peramban web (*browser*) yang menembak *endpoint* `/api/upload`.
2. **Parsing & Preprocessing:** 
   - `EpubParser` membuka kerangka file ePub, memecahnya per bab, mengekstrak isi teks di tiap sub-dokumen, dan membuang tag HTML.
   - `Preprocessor` lalu membersihkan karakter non-standar Arab, menormalisasi huruf/tashkeel, membuang tanda baca berlebih, dan mensegmentasi satu teks utuh menjadi kalimat-kalimat pendek.
3. **Pemrosesan Teks Generatif:** Pengguna dapat memicu aksi via web:
   - **Penerjemahan (Translate):** Kalimat-kalimat dikirimkan ke `Translator` yang menyematkan *prompt* khusus agar model Ollama memberikan hasil terjemahan lurus (*strict*).
   - **Peringkasan (Summarization):** Teks buku yang sangat panjang dipotong-potong (*chunking*) dan dikirim ke `Summarizer` agar diringkas menjadi draf abstrak poin-poin oleh Ollama.
4. **Sintesis Audio Podcast (TTS):** Teks berbahasa target diteruskan menuju `TTSEngine`.
   - Modul mengubah teks per-kalimat menjadi berkas klip audio individual.
   - Pydub menyisipkan jeda napas (*silence*) statis (500 ms) di sela-sela tiap pergantian kalimat.
   - Sistem melakukan *audio normalization* (*Target dBFS*) untuk memastikan tinggi rendahnya volume suara rata di seluruh menit audio.
5. **Penyampaian Output:** *File* `.mp3` utuh yang telah dirakit dan dinormalisasi disimpan ke *storage*, kemudian peladen (*server*) membalas respons API kepada *Frontend* URL untuk dapat memutarnya di *Audio Player*.
6. **Sesi Chatbot Kontekstual (Opsional):** Pengguna masuk ke modul Chat `/api/chat`, sistem menyuntikkan hasil teks buku sebagai *System Prompt*, sehingga LLM bisa menjawab pertanyaan (*Q&A*) seputar buku tersebut. Jawaban LLM tersebut juga dapat dilanjutkan ke sintesis TTS.

## 3. Kebutuhan Fungsional
Kebutuhan fungsional (*Functional Requirements*) mendefinisikan apa saja yang secara fungsional **harus bisa dikerjakan** oleh sistem eCast:
- **FR-01 (Upload ePub):** Sistem web harus menyediakan form unggahan bagi pengguna untuk memasukkan dokumen *e-book* berformat `.epub` (maksimal 10 MB).
- **FR-02 (Parsing & Ekstraksi Teks):** Sistem harus mampu membedah kerangka struktur bab ePub dan mengekstrak materi teks dengan akurat.
- **FR-03 (Pembersihan Teks Arab):** Sistem wajib membersihkan *noise* teks Arab dan menormalisasi *tashkeel* (harakat).
- **FR-04 (Penerjemahan Otomatis):** Sistem harus mampu menerjemahkan bab buku bahasa Arab ke bahasa target yang di-dukung (misal: ID, EN) melalui model AI lokal.
- **FR-05 (Auto-Summarization):** Sistem harus menyediakan fitur untuk mengonversi bab buku teks panjang menjadi *summary* berbentuk narasi singkat secara otomatis.
- **FR-06 (Konversi Audio Podcast):** Sistem harus dapat membacakan teks (*Text-to-Speech*) menjadi berkas `.mp3` dengan konfigurasi penyisipan jeda napas agar terdengar seperti ritme *podcast* natural.
- **FR-07 (Playback & Unduhan):** Antarmuka UI/UX di *browser* wajib memberikan *audio player component* terintegrasi untuk mendengarkan hasil *podcast* dan fungsionalitas unduh berkas.
- **FR-08 (Chatbot QA Interaktif):** Sistem harus memiliki jendela ruang *chat* (bot) di mana pengguna dapat melemparkan kueri pertanyaan mengenai materi dalam buku, dan menerima balasan berlandaskan isi buku tersebut.

## 4. Kebutuhan Non-Fungsional
Kebutuhan non-fungsional (*Non-Functional Requirements*) mengukur spesifikasi, batasan, ketahanan, kualitas, standar operasional (*QoS*), serta performa sistem:
- **NFR-01 (Manajemen Kinerja & Rate Limit):** Menghindari server lumpuh (*Out of Memory* atau *Timeout*), penerjemahan tidak boleh memproses 1 buku penuh secara brutal sekaligus; melainkan diatur menjadi *batching* kecil (contoh: maksimal terjemahan 50 kalimat per-API Call). Proses ringkasan menggunakan *chunking* berlapis (max 600 kata).
- **NFR-02 (Kapasitas Token LLM):** Sistem dirancang agar interaksi *chatbot* memiliki keterbatasan membaca memori konteks buku di titik *Context Window* terbatas (misalnya, teks sumber akan dipotong maksimum di ~6000 karakter sebelum dipasok ke Ollama).
- **NFR-03 (Batasan Format Masukan):** Arsitektur masukan ketat *hanya* menolerir ekstensi `.epub` yang sah; berkas seperti PDF, Mobi, dan Word tidak disokong.
- **NFR-04 (Dependensi Perangkat Lunak Tihang):** Lingkungan sistem di belakang layar bersandar mutlak pada pustaka FFmpeg dan FFprobe untuk fungsionalitas penggabungan audio (*concatenation* Pydub) dan normalisasi desibel. Ketiadaan *binary* ini akan membuat server gagal beroperasi.
- **NFR-05 (Kualitas Pengalaman Audio):** Kecepatan tempo audio yang dihasilkan direndahkan (*default* rasio 0.9 / `-10%`) dari tempo bawaan TTS *bot* biasa, untuk memacu ketenangan intonasi diksi, agar nyaman dalam jangka waktu panjang (*podcast style*). Pengaturan puncak sinyal *dBFS* dikalibrasi di kisaran angka konstan `-20.0` *dB*.
- **NFR-06 (Isolasi File & State RAM):** Dokumen dan proses antar pengguna di web harus terisolasi berlandaskan UUID unik agar teks asli maupun objek terjemahan yang menetap sementara (*ephemeral*) pada *dictionary/RAM* tidak tertukar atau bertabrakan antar-klien (*thread safety* dasar).

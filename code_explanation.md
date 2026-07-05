# Analisis Alur Eksekusi eCast (Awal Hingga Akhir)

Sistem **eCast** merupakan sebuah *pipeline* yang mengonversi buku berbahasa Arab (.epub) menjadi bentuk *podcast* multi-bahasa dengan memanfaatkan Model LLM (Ollama) dan Edge-TTS. Berikut adalah penjelasan berurutan dari proses awal hingga akhir beserta rincian variabel pada setiap file.

---

## 1. Tahap Konfigurasi & Persiapan

### `app/config.py`
**Fungsi:** Mengatur seluruh variabel lingkungan (*environment variables*) dan path yang akan digunakan oleh seluruh komponen di dalam sistem eCast.
*   **`BASE_DIR`** (line 14): Menentukan lokasi root proyek.
*   **`UPLOAD_DIR`, `OUTPUT_DIR`, `MODEL_CACHE_DIR`** (line 15-17): Mendefinisikan dan membuat folder untuk menampung file upload epub, output audio, dan cache model.
*   **`MAX_FILE_SIZE_MB`, `MAX_FILE_SIZE_BYTES`** (line 25-26): Membatasi ukuran maksimal file yang bisa diunggah (default 10 MB).
*   **`BATCH_SIZE_TRANSLATION`, `MAX_INPUT_TOKENS`, `NUM_BEAMS`** (line 29-31): Parameter terkait limitasi teks saat menerjemahkan, memengaruhi seberapa besar teks diproses sekaligus.
*   **`OLLAMA_MODEL`** (line 34): Bernilai `"qwen2.5:3b"`, mendefinisikan model LLM lokal yang dipakai.
*   **`OLLAMA_CHAT_URL`** (line 35): Endpoint API untuk melakukan request ke service Ollama lokal.
*   **`TTS_SPEED`, `TTS_SAMPLE_RATE`, `PODCAST_SILENCE_MS`** (line 39-41): Parameter audio. Kecepatan bacaan (0.9), *sample rate*, dan jeda antar kalimat (500ms) untuk memberi kesan *podcast* yang natural.
*   **`EDGE_TTS_VOICES`** (line 44): *Dictionary* pemetaan kode bahasa ("ar", "id", "en") dengan ID suara di sistem Edge-TTS.
*   **`CHAPTER_LIMIT`, `OUTPUT_FORMAT`** (line 51-52): Format keluaran (default "mp3").
*   **`DEVICE`** (line 55): CPU atau GPU (cuda) untuk deteksi hardware.
*   **`FFMPEG_PATH`, `FFPROBE_PATH`** (line 72-87): Lokasi binary FFmpeg yang mutlak diperlukan modul Pydub untuk manipulasi audio.

### `download_models.py`
**Fungsi:** Script ini dijalankan pada awal instalasi untuk mengunduh model LLM ke dalam Ollama secara otomatis.
*   **`response`** (line 14, 30): Objek *requests* untuk memanggil API `/api/pull` Ollama.
*   **`msg`, `status`, `completed`, `total`, `percent`** (line 45-50): Variabel yang mendecode JSON *streaming response* untuk menampilkan persentase *progress* unduhan model `qwen2.5:3b` ke konsol.

---

## 2. Tahap Backend & API Orchestration

### `app/main.py`
**Fungsi:** Titik masuk utama aplikasi (FastAPI) yang mengatur alur masuknya file, meneruskannya ke Parser, Translator, hingga mengembalikan Audio.
*   **`app`** (line 48): Objek instansiasi utama FastAPI.
*   **`_uploaded_files`** (line 72): *Dictionary* global yang bertugas menyimpan metadata file di RAM (sementara) berdasarkan ID, berisi teks asli dan terjemahannya.
*   **`ext`** (line 146) & **`content`** (line 153): Saat user upload di `/api/upload`, `ext` mengecek ekstensi `.epub`, dan `content` membaca isi *bytes* file.
*   **`file_id`, `safe_filename`, `file_path`** (line 160-162): Men-generate UUID unik dan path penyimpanan sementara untuk ePub.
*   **Proses Parsing (line 170-182):** Menggunakan `EpubParser` untuk mengambil `metadata` dan memanggil `get_preprocessor().clean_text(raw_text)` untuk membersihkan teks ePub.
*   **`lang`** (line 218): Parameter di `/api/file/{file_id}/content` untuk mengetahui target bahasa. Jika belum ada *cache*, API memanggil `translator.translate_batch`.
*   **`max_sentences = 50`** (line 239): Pembatasan sementara agar API tidak *timeout* apabila mencoba menerjemahkan buku penuh secara *real-time*.
*   **`req.history`, `req.message`** (line 121-122): Input user pada fitur Chatbot di `/api/chat`.
*   **`max_context = 6000`** (line 267): Memotong `context_text` buku agar tidak melebih batas *Context Window* LLM Ollama.
*   **`system_prompt`** (line 271): Konteks *prompt* sistem (aturan main) yang ditugaskan ke LLM agar LLM menjawab berdasarkan dokumen.
*   **`req.text`, `req.lang`** (line 125-126): Teks spesifik untuk request pembuatan audio.
*   **`sentences`** (line 308) & **`max_sentences = 20`** (line 312): Membatasi kalimat maksimal yang disintesis ke Audio (TTS) demi mencegah server kelebihan beban saat menjawab chat *real-time*.

---

## 3. Tahap Pemrosesan File & Teks

### `app/epub_parser.py`
**Fungsi:** Mengekstrak teks dari buku ePub secara per Bab (*Chapter*) sekaligus membuang kode-kode HTML kotor.
*   **`self.file_path`** (line 19): Path dari buku yang ingin di parse.
*   **`self.book`** (line 25): Objek EbookLib yang menyimpan isi buku epub.
*   **`self._chapters`** (line 26): *List of dictionary* penyimpan *index*, *title*, *text*, dan hitungan *word_count* tiap bab (line 64).
*   **`items`** (line 43): Daftar seluruh sub-dokumen di dalam buku ePub.
*   **`soup`** (line 51): Objek BeautifulSoup4. Ia mendekomposisi tag `<script>`, `<style>` (line 76), dan menarik teks utuh dari tag `p`, `h1`, dll menjadi **`text_parts`** (line 80).
*   **`chapter_index`** (line 45): ID perulangan bab.

### `app/preprocessor.py`
**Fungsi:** Membersihkan karakter non-standar Arab, mensegmentasi paragraf menjadi kalimat-kalimat pendek, dan mengadaptasi *formatting* teks untuk *Text-To-Speech* (TTS).
*   **`TASHKEEL_PATTERN`** (line 16): Regex Unicode (0617-0652) untuk mendeteksi *harakat/tashkeel* Arab.
*   **`NORMALIZATION_MAP`** (line 19): Pemetaan standarisasi huruf Arab (misal: "أ" menjadi "ا").
*   **`SENTENCE_SPLITTER`** (line 31): Regex pembelah kalimat berdasarkan tanda baca (".", "!", "?", dsb).
*   **`self.glossary`** (line 40): Penyimpan kamus istilah-istilah khusus Islam dari JSON.
*   Di metode `clean_text`: Regex `re.sub(r"[^\w\s...]", "")` (line 79) membuang semua karakter aneh yang bukan bahasa Arab atau bahasa umum.
*   **`max_length = 500`** (line 100): Pada fungsi `segment_sentences`, jika 1 kalimat melewati 500 huruf, akan dipaksa pecah (line 124) dengan memotong `words = part.split()` agar tidak terjadi *Memory Error* di model translasi.
*   Fungsi `preprocess_for_tts`: Mengubah ganti baris (`\n`) menjadi jeda (". ") pada line 200 agar TTS mengerti ia harus mengambil nafas / memberi jeda baca.

---

## 4. Tahap Modul Generatif & AI (LLM)

### `app/llm_manager.py`
**Fungsi:** Mengatur *routing* ke Ollama API secara Singleton (satu *instance*).
*   **`_instance`, `_lock`** (line 18-19): Pola singleton *Thread-safe*, menjaga agar manajer ini tidak diinisiasi berulang kali secara paralel.
*   **`payload`** (line 42): *Dictionary* request ke Ollama berisi: `model` (berasal dari config), `messages`, `stream: False`, dan opsi `temperature`, `num_predict` (Max Token).
*   **`data`** (line 55): Output balikan JSON dari API Ollama. Respons diambil dari `data.get("message").get("content")`.

### `app/translator.py`
**Fungsi:** Merakit *prompt* khusus dan mengirimkannya ke `LLMManager` untuk tugas terjemahan secara leksikal.
*   **`target_lang`** (line 41): Bahasa tujuan (contoh: "id").
*   **`system_prompt`** (line 72): Aturan emas untuk model: `"You are a professional translator... Output only the translated text..."`. Sangat vital agar AI tidak banyak bicara di luar konteks menerjemahkan.
*   **`max_tokens = 1024`, `temperature = 0.1`** (line 91-92): Parameter LLM ini diset khusus (0.1) untuk memastikan LLM memberikan respons terjemahan yang *Kaku / Presisi tinggi / Akurat*, tidak berhalusinasi atau kreatif. Menghasilkan *output* variabel `translated_text` (line 89).

### `app/summarizer.py`
**Fungsi:** Menyusutkan teks panjang menjadi poin ringkasan abstrak (*abstractive summarization*).
*   **`max_words = 600`** (line 86): Pembatasan jumlah kata per satu kali lempar ke model LLM. Menghasilkan *list* `chunks` agar memori LLM tidak kewalahan.
*   **`system_prompt`** (line 92): Memerintahkan AI untuk menjadi `"expert summarizer"`.
*   **`max_tokens = 300`, `temperature = 0.3`** (line 108-109): LLM dibatasi menghasilkan maksimal 300 token dan *temperature* dibuat sedikit longgar (0.3) agar model bisa sedikit lebih luas membuat bahasa rangkuman yang lebih elegan ketimbang terjemahan kaku.
*   **`final_summary`** (line 123): Penggabungan hasil *chunk*. Jika panjang total kata di atas 1000 kata (line 126), kode akan memanggil dirinya sendiri (Rekursi) untuk meringkas lagi (*Recursive Summarization*).

---

## 5. Tahap Sintesis Audio (TTS)

### `app/tts_engine.py`
**Fungsi:** Mengubah hasil terjemahan/rangkuman teks ke dalam bentuk berkas audio dengan format *Podcast*.
*   **`AudioSegment.converter`** (line 29): Menyuntikkan rute `FFMPEG_PATH` untuk Pydub.
*   **`self._voices`** (line 48): Pemetaan suara AI berdasarkan bahasa.
*   **`rate`** (line 61): Di fungsi `_calculate_rate`, ia mengubah format angka *float* `TTS_SPEED` (contoh: 0.9) menjadi persentase format Edge-TTS (contoh: `"-10%"`).
*   **`sentences`** (line 124): List kalimat. Di fungsi `synthesize_podcast_async` (line 157), ia me-*loop* tiap kalimat secara terpisah dan disimpan di dalam folder penampungan `temp_dir` bernama **`segment_path`** (line 161).
*   **`segment_files`** (line 154): List path yang berisi file-file potongan *mp3* kalimat individual.
*   **`silence`** (line 210): AudioSegment kosong berdurasikan `PODCAST_SILENCE_MS` (500ms).
*   **`combined`** (line 213-228): Fungsi `_combine_segments_with_silence` bertugas menggabungkan (*concatenate*) `segment_files` dan menyisipkan variabel `silence` di sela-sela kalimat untuk memberi sensasi orang bernapas di Podcast.
*   **`target_dbfs = -20.0`** (line 235): Fungsi `_normalize_volume` menggunakan selisih desibel (`change_in_dbfs`) untuk meratakan tingkat kekencangan suara agar di seluruh podcast konstan dan nyaman didengar (Audio Normalization).
*   Kemudian diekspor via `combined.export()` (line 182) berdasarkan ekstensi di `OUTPUT_FORMAT`.

---

## Tahap Tambahan: Pipeline AI Ops (*Fine-tuning* & Evaluasi)

*(Catatan: File-file ini adalah script independen untuk melatih ulang (Finetune) model lama (MarianMT) dan mengevaluasinya, diluar dari pipeline Ollama utama yang sedang aktif)*

### `prepare_dataset.py`
**Fungsi:** Menyalin data JSON dari OPUS (dataset Arab-Indonesia) menjadi format CSV untuk pelatihan.
*   **`input_file`** (line 16), **`output_file`** (line 17): Jalur berkas JSON ke CSV.
*   **`data`** (line 24), **`writer.writerow`** (line 33): Mengekstraksi key `source` dan `target` lalu menyimpannya.

### `finetune_translation.py`
**Fungsi:** Melakukan *Training/Fine-tuning* model *Helsinki-NLP/opus-mt-en-id* (atau varian sejenis).
*   **`model_inputs`, `labels`** (line 43-52): Hasil dari `MarianTokenizer` berupa array tensor Pytorch.
*   **`training_args`** (line 110): Pengaturan pelatihan, misalnya `num_train_epochs=3` (jumlah pengulangan melatih data), `learning_rate=5e-5` (seberapa cepat mesin merevisi kesalahannya), `per_device_train_batch_size=4`.
*   **`trainer`** (line 127): Objek HuggingFace Seq2SeqTrainer yang mengeksekusi model (`trainer.train()`).

### `run_evaluation.py`
**Fungsi:** Menguji hasil terjemahan dari aplikasi dengan tolok ukur skor akurasi mesin.
*   **`refs`, `bleu`** (line 26-27): Menghitung persentase irisan kata/gram menggunakan SacreBLEU (skor akurasi penerjemahan kasar).
*   **`scores`** menggunakan `nltk_meteor` (line 54): Menghitung presisi terjemahan berdasar sinonim / WordNet (METEOR Score).
*   **`model.encode`** dengan LaBSE (line 77-78): Menghitung *Semantic Similarity* dengan mengonversi teks ke dalam bentuk matrik *Embedding Vector*, lalu menghitung kedekatan vektornya secara *Cosine Similarity* (`util.cos_sim` di line 80). Makin dekat angkanya ke 1, semakin mirip maknanya.
*   **`wer`** (line 101): *Word Error Rate*, menghitung seberapa melenceng tulisan berdasar *edit distance*. Biasa juga digunakan untuk uji ASR/TTS.

---
**Kesimpulan:**
Sistem bekerja dengan membaca ePub (*epub_parser*), membuang *noise* dan menormalisasi *string* bahasa Arab (*preprocessor*). Kemudian *Endpoint API* FastAPI (di *main*) mengirimnya sebagai pesan ke Ollama API (*llm_manager*, *translator*, *summarizer*). Setelah AI selesai, Pydub + Edge-TTS (*tts_engine*) merendernya menjadi kepingan kalimat suara (*segment_path*), merakitnya dengan jeda napas (*silence*), menormalisasi suaranya, dan mereturn audio komplit kepada pengguna akhir. Variabel seperti `max_sentences`, `temperature=0.1`, dan `PODCAST_SILENCE_MS` punya efek paling vital dalam memastikan stabilitas memori API dan kesan "manusia" di hasil *podcast*.

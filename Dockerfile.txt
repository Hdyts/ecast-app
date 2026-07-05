# Gunakan OS Linux ringan dengan Python 3.10
FROM python:3.10-slim

# Set folder kerja di dalam server
WORKDIR /app

# Install ffmpeg (wajib untuk pydub/audio processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Salin file requirements dan install dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh file aplikasi Anda
COPY . .

# Buat folder yang dibutuhkan agar tidak error saat aplikasi berjalan
RUN mkdir -p uploads outputs models

# Jalankan server FastAPI menggunakan uvicorn
# (Render akan memberikan port melalui variabel environment $PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
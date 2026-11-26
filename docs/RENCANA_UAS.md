# Rencana Pengembangan untuk UAS

Rencana ini melanjutkan MVP v1.0. Urutan mengikuti prioritas: keamanan dan kebenaran data dahulu, baru fitur dan kenyamanan.

## 1. Autentikasi dan otorisasi (JWT)
- Endpoint `POST /auth/login` (verifikasi `password_hash`) yang mengeluarkan access token JWT berumur pendek dan refresh token.
- Library: Flask-JWT-Extended.
- Role yang sudah ada di tabel `users` dipakai sebagai RBAC: `admin` (semua), `operator` (hanya perangkat miliknya), `viewer` (baca saja).
- Menggantikan proteksi sementara `X-API-Key` pada request tulis.

## 2. Autentikasi perangkat dan integritas telemetri
- Setiap perangkat memiliki API key / secret sendiri (disimpan sebagai hash) untuk `POST /telemetry`.
- Opsional: tanda tangan HMAC pada payload agar data tidak bisa dipalsukan atau di-replay.
- Rate limiting per perangkat dan per IP (Flask-Limiter) untuk mencegah banjir data.

## 3. Penguatan keamanan (cybersecurity)
- Tabel `audit_logs` (siapa, aksi, resource, waktu, IP) untuk semua request tulis.
- Pencatatan upaya login gagal dan penguncian sementara akun.
- HTTPS di deployment, CORS terbatas, header keamanan tambahan (HSTS).
- Pemindaian dependency berkala (`pip-audit`) dan pin versi di `requirements.txt`.
- Validasi lanjutan: batas ukuran batch, pembersihan field teks.

## 4. Dokumentasi API
- OpenAPI sudah ada (`docs/openapi.yaml`, Swagger UI di `/docs`); tambahkan skema autentikasi JWT dan contoh per skenario.
- Menjaga spesifikasi tetap sinkron dengan kode lewat test otomatis (sudah ada: `tests/test_docs.py`).

## 5. Deployment
- Gunicorn di balik reverse proxy (Nginx) pada VPS atau layanan PaaS (Render/Railway).
- Pindah ke MySQL/MariaDB atau PostgreSQL untuk produksi; konfigurasi lewat `DATABASE_URL`.
- Docker + docker-compose (app + database), CI GitHub Actions (jalankan test + lint pada setiap push).

## 6. Synthetic data
- Generator data simulasi skala besar (puluhan ribu pembacaan, banyak perangkat) dengan pola harian dan anomali terkontrol, untuk menguji performa dan aturan alert.
- Simulator perangkat (skrip yang mengirim telemetri berkala ke API) sebagai pengganti perangkat fisik.

## 7. Optimasi query
- Ukur dengan `EXPLAIN` dan profiling; indeks `(sensor_id, recorded_at)` sudah ada, tambahkan bila perlu pada filter yang sering dipakai.
- Endpoint agregasi (rata-rata per jam/hari) dan retensi data (arsip/hapus telemetri lama).
- Pagination berbasis cursor untuk tabel telemetri yang besar.

## 8. Frontend / client API
- Dashboard web sederhana: daftar perangkat, grafik time-series per sensor, daftar alert dengan aksi acknowledge/resolve.
- Alternatif: klien ringan (skrip ESP32/MicroPython) yang memakai endpoint telemetri.

## 9. Fitur domain tambahan
- Notifikasi alert (email/Telegram/webhook), aturan dengan durasi (mis. di atas ambang selama 5 menit), deteksi perangkat offline berdasarkan `last_seen_at`.
- Ingestion lewat MQTT sebagai jalur alternatif selain HTTP.

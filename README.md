# IoT Monitor API

MVP REST API untuk **monitoring perangkat IoT**: registrasi perangkat, sensor, penerimaan telemetri, aturan ambang batas, dan alert otomatis.
Dibuat dengan **Python Flask**, **SQLAlchemy (ORM)**, arsitektur **MVC**, dan **SQLite** (bisa diganti MySQL/MariaDB).

- Versi: **v1.0**
- Dokumentasi interaktif (Swagger UI): `GET /docs` | Spesifikasi OpenAPI: [`docs/openapi.yaml`](docs/openapi.yaml)
- ERD: [`docs/ERD.md`](docs/ERD.md) | Collection Postman: [`docs/postman_collection.json`](docs/postman_collection.json)
- Rencana pengembangan UAS: [`docs/RENCANA_UAS.md`](docs/RENCANA_UAS.md)
- Link demo: **(isi URL demo di sini setelah deploy)**

## 1. Masalah, pengguna, fitur, dan batasan

**Masalah.** Perangkat IoT (mis. ESP32 di gudang atau ruang server) terus mengirim data sensor. Tanpa sistem pusat, data tersebar, tidak ada riwayat, dan kondisi berbahaya (suhu server naik, gas bocor, tegangan UPS turun) baru diketahui setelah terlambat. API ini menyediakan tempat terpusat untuk menyimpan telemetri, mengevaluasi aturan ambang batas, dan melacak penanganan alert.

**Pengguna (aktor).**

| Aktor | Peran di sistem |
| --- | --- |
| Admin | mengelola seluruh data dan user |
| Operator | pemilik perangkat; mendaftarkan perangkat/sensor/aturan, menangani alert |
| Viewer | memantau data dan alert |
| Perangkat IoT | klien yang mengirim telemetri lewat `POST /telemetry` |

**Fitur utama.**
1. Manajemen user, perangkat, sensor, dan aturan alert (CRUD lengkap, PUT/PATCH).
2. Penerimaan telemetri dengan validasi rentang fisik sensor dan status perangkat.
3. Evaluasi aturan otomatis: pembacaan yang melanggar ambang langsung menghasilkan alert.
4. Siklus penanganan alert: `open` -> `acknowledged` -> `resolved`.
5. Pencarian, filter, sorting, dan pagination pada semua endpoint daftar; statistik per sensor.

**Batasan sistem (MVP).**
- Belum ada login/JWT. Proteksi sementara: header `X-API-Key` opsional untuk request tulis (lihat bagian Keamanan). JWT direncanakan untuk UAS.
- Hanya satu pembacaan per request (belum ada batch/MQTT).
- Pengguna tidak dibatasi per kepemilikan (belum ada otorisasi per resource).
- Seluruh data bersifat **simulasi**; tidak ada scanning atau koneksi ke perangkat/sistem pihak lain.
- SQLite cocok untuk pengembangan/demo; untuk beban nyata gunakan MySQL/MariaDB.

## 2. Domain IoT: perangkat, sensor, telemetri, dan alur data

- **Perangkat** (`devices`): mikrokontroler/gateway fisik (ESP32, ESP8266, Raspberry Pi) dengan `serial_number` unik dan status `active/inactive/maintenance`.
- **Sensor** (`sensors`): komponen pengukur pada perangkat (suhu, kelembapan, gas, tegangan, cahaya) dengan satuan dan rentang fisik `min_value`..`max_value`.
- **Telemetri** (`telemetry_readings`): satu pembacaan nilai sensor pada waktu tertentu (time-series).
- **Aturan & alert** (`alert_rules`, `alerts`): aturan `nilai <operator> ambang` per sensor; pelanggaran menghasilkan alert.

**Alur data:**

```
Perangkat --POST /telemetry--> validasi (sensor ada? perangkat active? nilai dalam rentang? waktu wajar?)
      --> simpan pembacaan + perbarui devices.last_seen_at
      --> evaluasi alert_rules aktif milik sensor
      --> bila dilanggar & belum ada alert aktif untuk aturan itu --> buat alert (status open)
      --> response 201 berisi pembacaan + triggered_alerts
Operator --PATCH /alerts/{id}--> acknowledged --> resolved
```

Satu aturan hanya memiliki **satu alert aktif** (`open`/`acknowledged`) pada satu waktu, sehingga sensor yang terus melewati ambang tidak membanjiri tabel alert. Setelah alert `resolved`, pelanggaran berikutnya membuat alert baru.

## 3. Arsitektur MVC dan struktur folder

| Lapisan | Folder | Tugas |
| --- | --- | --- |
| Model | `app/models/` | entitas ORM (SQLAlchemy), constraint database |
| View | `app/schemas/` | validasi input & serialisasi output JSON (marshmallow) |
| Controller | `app/controllers/` | blueprint per resource: menerima request, memanggil schema/model/service |
| Service | `app/services/` | logika bisnis (evaluasi alert, penerimaan telemetri) |

```
iot-monitor-api/
├── app/
│   ├── __init__.py          # application factory create_app()
│   ├── config.py            # Development / Testing / Production
│   ├── constants.py         # enum & batas (status, tipe, pagination)
│   ├── extensions.py        # db, migrate, PRAGMA foreign_keys SQLite
│   ├── cli.py               # perintah `flask seed`
│   ├── models/              # user, device, sensor, telemetry, alert_rule, alert
│   ├── schemas/             # schema validasi & serialisasi
│   ├── controllers/         # blueprint endpoint (+ docs_controller untuk /docs)
│   ├── services/            # alert_service, telemetry_service
│   └── utils/               # errors, responses, pagination, validation, security
├── migrations/              # Flask-Migrate / Alembic (migration awal sudah ada)
├── seeds/seed.py            # data simulasi deterministik
├── tests/                   # pytest (95 test)
├── docs/                    # openapi.yaml, postman_collection.json, ERD, rencana UAS
├── requirements.txt
├── .env.example
├── Procfile
└── run.py
```

## 4. ERD

![ERD](docs/erd.png)

Enam tabel: `users`, `devices`, `sensors`, `telemetry_readings`, `alert_rules`, `alerts`.
Atribut, primary key, foreign key, kardinalitas, dan aksi cascade lengkap di [`docs/ERD.md`](docs/ERD.md).

## 5. Instalasi

Prasyarat: Python 3.10+ dan Git.

```bash
git clone <url-repo-anda> iot-monitor-api
cd iot-monitor-api

python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (cmd)
venv\Scripts\activate.bat

pip install -r requirements.txt
```

## 6. Konfigurasi

Salin `.env.example` menjadi `.env` lalu sesuaikan (file `.env` tidak di-commit).

| Variabel | Default | Keterangan |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` / `testing` / `production` |
| `SECRET_KEY` | `dev-only-change-me` | wajib diganti saat `APP_ENV=production` (nilai default ditolak) |
| `DATABASE_URL` | `sqlite:///iot_monitor.db` | SQLite disimpan di folder `instance/`. MySQL/MariaDB: `mysql+pymysql://user:pass@host:3306/iot_monitor` (`pip install PyMySQL`) |
| `API_KEY` | kosong | bila diisi, request tulis wajib mengirim header `X-API-Key` |

```bash
# Linux / macOS
cp .env.example .env
# Windows (PowerShell)
Copy-Item .env.example .env
```

## 7. Membuat database dan seed

```bash
flask db upgrade     # membuat semua tabel dari migration
flask seed           # mengisi data simulasi (lewati bila DB sudah berisi)
flask seed --reset   # hapus semua data lalu isi ulang
```

Data seed (fiktif, deterministik): 4 user, 5 perangkat, 7 sensor, 5 aturan alert, 336 pembacaan (24 jam terakhir), dan 4 alert dengan status berbeda.
Semua user seed memakai password `Password123` (hanya untuk pengembangan lokal; belum ada endpoint login pada v1.0).

> `flask db init` / `flask db migrate` **tidak perlu** dijalankan lagi karena folder `migrations/` sudah ada.
> Setelah mengubah model: `flask db migrate -m "pesan"` lalu `flask db upgrade`.

## 8. Menjalankan aplikasi

```bash
flask run                      # http://127.0.0.1:5000
# atau
python run.py
# produksi
gunicorn run:app
```

Cek: `http://127.0.0.1:5000/api/v1/health` dan dokumentasi interaktif di `http://127.0.0.1:5000/docs`.

## 9. Menjalankan test

```bash
pytest                                   # 95 test, memakai SQLite in-memory
pytest --cov=app --cov=seeds             # dengan coverage (sekitar 98%)
```

Test mencakup skenario berhasil dan skenario validasi/error untuk setiap endpoint utama, integritas database (unique, foreign key, check constraint, cascade), seed, serta kesesuaian `docs/openapi.yaml` dengan route yang sebenarnya.

## 10. Daftar endpoint

Base URL: `/api/v1`. Response sukses: `{"data": ..., "meta": ...}`. Daftar semua parameter dan skema ada di OpenAPI.

| Method | Path | Fungsi | Status |
| --- | --- | --- | --- |
| GET | `/health` | cek API & database | 200 / 503 |
| POST | `/users` | buat user (password di-hash) | 201, 409, 422 |
| GET | `/users` | daftar user (`q`, `role`, `sort`, pagination) | 200 |
| GET | `/users/{id}` | detail user | 200, 404 |
| DELETE | `/users/{id}` | hapus user (409 bila masih punya perangkat) | 204, 404, 409 |
| POST | `/devices` | registrasi perangkat | 201, 409, 422 |
| GET | `/devices` | daftar (`q`, `status`, `device_type`, `owner_id`, `sort`, pagination) | 200 |
| GET | `/devices/{id}` | detail perangkat | 200, 404 |
| PUT | `/devices/{id}` | ganti seluruh field | 200, 404, 409, 422 |
| PATCH | `/devices/{id}` | ubah sebagian field | 200, 404, 409, 422 |
| DELETE | `/devices/{id}` | hapus (sensor, telemetri, aturan, alert ikut terhapus) | 204, 404 |
| POST | `/sensors` | buat sensor | 201, 409, 422 |
| GET | `/sensors` | daftar (`q`, `device_id`, `sensor_type`, `sort`, pagination) | 200 |
| GET | `/sensors/{id}` | detail sensor | 200, 404 |
| PUT / PATCH | `/sensors/{id}` | ubah sensor | 200, 404, 409, 422 |
| DELETE | `/sensors/{id}` | hapus sensor | 204, 404 |
| GET | `/sensors/{id}/stats` | count, min, avg, max, latest (`from`, `to`) | 200, 404, 422 |
| POST | `/alert-rules` | buat aturan ambang | 201, 422 |
| GET | `/alert-rules` | daftar (`sensor_id`, `severity`, `is_active`, `sort`, pagination) | 200 |
| GET | `/alert-rules/{id}` | detail aturan | 200, 404 |
| PUT / PATCH | `/alert-rules/{id}` | ubah aturan | 200, 404, 422 |
| DELETE | `/alert-rules/{id}` | hapus aturan | 204, 404 |
| POST | `/telemetry` | kirim pembacaan + evaluasi alert | 201, 409, 422 |
| GET | `/telemetry` | daftar (`sensor_id`, `device_id`, `from`, `to`, `sort`, pagination) | 200 |
| GET | `/telemetry/{id}` | detail pembacaan | 200, 404 |
| DELETE | `/telemetry/{id}` | hapus pembacaan (alert tetap ada) | 204, 404 |
| GET | `/alerts` | daftar (`status`, `severity`, `sensor_id`, `device_id`, `from`, `to`, `sort`, pagination) | 200 |
| GET | `/alerts/{id}` | detail alert | 200, 404 |
| PATCH | `/alerts/{id}` | ubah status (`acknowledged` / `resolved`) | 200, 404, 409, 422 |

**Pagination, filter, sorting, pencarian** (berlaku di semua endpoint daftar):
`?page=1&per_page=20` (maks. 100), `?sort=-created_at,name` (awalan `-` = descending, hanya field yang diizinkan), `?q=teks` (substring, case-insensitive), serta filter per endpoint. Parameter tidak valid dibalas `422`.
Waktu memakai ISO 8601 UTC (contoh `2026-01-01T00:00:00Z`); untuk offset `+07:00` tulis `%2B07:00` di URL.

## 11. Contoh request dan response

Berikut keluaran nyata dari server lokal dengan data seed (ID dan timestamp akan berbeda di komputer Anda).

**Registrasi perangkat** - `POST /api/v1/devices`

```bash
curl -i -X POST http://127.0.0.1:5000/api/v1/devices \
  -H "Content-Type: application/json" \
  -d '{"owner_id":2,"name":"Node Dapur","serial_number":"ESP32-DP-001","device_type":"esp32","location":"Dapur"}'
```
```
HTTP/1.1 201 CREATED
Location: /api/v1/devices/6
```
```json
{"data": {"id": 6, "owner_id": 2, "name": "Node Dapur", "serial_number": "ESP32-DP-001",
          "device_type": "esp32", "location": "Dapur", "status": "active", "firmware_version": null,
          "last_seen_at": null, "created_at": "2026-11-26T02:03:22.747Z", "updated_at": "2026-11-26T02:03:22.747Z"}}
```

**Daftar dengan filter, sorting, pagination** - `GET /api/v1/devices?status=active&q=gudang&sort=-name&per_page=2`

```json
{"data": [{"id": 2, "name": "Node Gudang B", "serial_number": "ESP32-GB-001", "status": "active", "...": "..."},
          {"id": 1, "name": "Node Gudang A", "serial_number": "ESP32-GA-001", "status": "active", "...": "..."}],
 "meta": {"page": 1, "per_page": 2, "total": 2, "pages": 1}}
```

**Kirim telemetri yang melanggar aturan** - `POST /api/v1/telemetry`

```bash
curl -X POST http://127.0.0.1:5000/api/v1/telemetry -H "Content-Type: application/json" \
  -d '{"sensor_id":1,"value":38.5}'
```
```json
{"data": {"id": 337, "sensor_id": 1, "value": 38.5,
          "recorded_at": "2026-11-26T02:03:37.113Z", "created_at": "2026-11-26T02:03:37.115Z",
          "triggered_alerts": [{"id": 5, "rule_id": 1, "sensor_id": 1, "device_id": 1, "reading_id": 337,
            "severity": "high",
            "message": "Suhu Gudang A on Node Gudang A: reading 38.5 °C violates rule 'Gudang terlalu panas' (> 35 °C)",
            "status": "open", "triggered_at": "2026-11-26T02:03:37.113Z",
            "acknowledged_by_id": null, "acknowledged_at": null, "resolved_at": null}]}}
```

**Tangani alert** - `PATCH /api/v1/alerts/5` dengan `{"status":"acknowledged","acknowledged_by_id":1}`

```json
{"data": {"id": 5, "status": "acknowledged", "acknowledged_by_id": 1,
          "acknowledged_at": "2026-11-26T02:03:53.352Z", "resolved_at": null, "...": "..."}}
```

**Statistik sensor** - `GET /api/v1/sensors/5/stats`

```json
{"data": {"sensor_id": 5, "unit": "°C", "count": 48, "min": 21.9, "avg": 24.856, "max": 39.0,
          "latest": {"id": 334, "sensor_id": 5, "value": 39.0, "recorded_at": "2026-11-26T02:03:13.000Z", "created_at": "2026-11-26T02:03:13.904Z"}}}
```

### Format error yang seragam

Semua error: `{"error": {"code": "...", "message": "...", "details": {...}}}` (`details` hanya bila ada).

| Status | `code` | Kapan |
| --- | --- | --- |
| 400 | `INVALID_JSON` | body bukan JSON valid |
| 401 | `UNAUTHORIZED` | API key salah/tidak ada (bila `API_KEY` diaktifkan) |
| 404 | `NOT_FOUND` | resource tidak ada |
| 405 | `METHOD_NOT_ALLOWED` | method tidak didukung |
| 409 | `CONFLICT`, `DEVICE_NOT_ACTIVE`, `INVALID_STATE_TRANSITION`, `INTEGRITY_ERROR` | duplikat, perangkat tidak aktif, transisi status salah, pelanggaran constraint |
| 415 | `UNSUPPORTED_MEDIA_TYPE` | Content-Type bukan `application/json` |
| 422 | `VALIDATION_ERROR`, `VALUE_OUT_OF_RANGE` | input tidak valid / pembacaan di luar rentang sensor |
| 500 | `INTERNAL_SERVER_ERROR` | error tak terduga (detail hanya di log server) |

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Input validation failed.",
           "details": {"serial_number": ["Missing data for required field."],
                       "device_type": ["Must be one of: esp32, esp8266, raspberry_pi, gateway, other."]}}}
```
```json
{"error": {"code": "CONFLICT", "message": "Device with serial_number 'ESP32-GA-001' already exists.",
           "details": {"serial_number": ["Must be unique."]}}}
```
```json
{"error": {"code": "VALUE_OUT_OF_RANGE", "message": "Reading is outside the physical range of this sensor.",
           "details": {"value": ["Must be between -40.0 and 125.0 °C for this sensor."]}}}
```

## 12. Keamanan dasar

- **Aset yang dilindungi:** data telemetri, konfigurasi perangkat, kredensial user, dan integritas catatan alert.
- **Risiko dan kontrol:**

| Risiko | Kontrol di kode |
| --- | --- |
| SQL injection | seluruh query lewat ORM (parameter terikat); wildcard `LIKE` di-escape |
| Kebocoran kredensial | password di-hash (Werkzeug), tidak pernah ada di response; secret hanya dari `.env` (di-ignore Git) |
| Input berbahaya / data palsu | validasi schema (tipe, panjang, pola, enum, `NaN` ditolak), rentang fisik sensor, waktu tidak boleh di masa depan, field tak dikenal ditolak |
| Data tidak konsisten | foreign key (SQLite `PRAGMA foreign_keys=ON`), unique & check constraint, aksi cascade/restrict terdefinisi |
| Penyalahgunaan request tulis | `X-API-Key` opsional (dibandingkan dengan `hmac.compare_digest`); JWT direncanakan untuk UAS |
| Pemakaian sumber daya berlebihan | body maksimal 1 MB, `per_page` maksimal 100, sort hanya pada field yang diizinkan |
| Kebocoran informasi | error 500 generik tanpa stack trace; pesan integritas DB tidak diteruskan ke klien |
| Clickjacking / MIME sniffing | header `X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control: no-store`, `Content-Security-Policy` ketat |

- **Jenis kejadian (cybersecurity/operasional) yang dimodelkan sebagai alert:** suhu ruang server berlebih, kadar gas berbahaya, tegangan UPS turun, kelembapan tinggi; severity `low`..`critical`.
- Produksi: `APP_ENV=production` menolak `SECRET_KEY` bawaan. Aktifkan `API_KEY` bila API dipublikasikan dan gunakan HTTPS di depan aplikasi.

## 13. Dokumentasi API dan pengujian manual

- **Swagger UI:** `GET /docs` (memuat Swagger UI dari CDN jsDelivr, jadi butuh internet; spesifikasi dilayani dari `/openapi.yaml`).
- **OpenAPI:** [`docs/openapi.yaml`](docs/openapi.yaml) (OpenAPI 3.0.3, semua endpoint, skema, dan contoh error). Dapat diimpor ke Postman/Insomnia.
- **Postman:** impor [`docs/postman_collection.json`](docs/postman_collection.json), jalankan `flask db upgrade && flask seed` lalu server, kemudian jalankan folder 1-9 berurutan lewat Collection Runner. Setiap request menyimpan ID yang dipakai request berikutnya (variabel `base_url` dan `api_key` bisa diubah). Folder 8 berisi skenario error.

## 14. Deployment / link demo

`Procfile` sudah disediakan (`gunicorn run:app`). Contoh di Render / Railway:

- Build command: `pip install -r requirements.txt && flask db upgrade && flask seed`
- Start command: `gunicorn run:app --bind 0.0.0.0:$PORT`
- Environment: `APP_ENV=production`, `SECRET_KEY=<string acak>`, opsional `API_KEY`, dan `DATABASE_URL` bila memakai database terkelola.

Catatan: SQLite di layanan dengan disk sementara akan hilang saat restart; `flask seed` pada build mengisi data demo bila database masih kosong. Isi URL demo pada bagian atas README setelah deploy.

## 15. Rencana pengembangan UAS

Lihat [`docs/RENCANA_UAS.md`](docs/RENCANA_UAS.md): JWT + RBAC, autentikasi perangkat dan HMAC, audit log, dokumentasi, deployment (Docker/CI), synthetic data, optimasi query, dan frontend dashboard.

## 16. Referensi, library, dan bantuan AI

**Library:** Flask, Flask-SQLAlchemy, SQLAlchemy, Flask-Migrate (Alembic), marshmallow, python-dotenv, Werkzeug, gunicorn, pytest, pytest-cov, PyYAML. Swagger UI (swagger-ui-dist) dimuat dari CDN pada halaman `/docs`. ERD dibuat dengan Graphviz.

**Referensi:** dokumentasi resmi Flask, SQLAlchemy 2.0, Flask-SQLAlchemy 3.1, Flask-Migrate, marshmallow, OpenAPI Specification 3.0.3, dan RFC 9110 (semantik HTTP & status code).

**Bantuan AI:** kerangka proyek, kode, test, dokumentasi, ERD, OpenAPI, dan collection Postman pada repositori ini dibuat dengan bantuan **Claude (Anthropic)**, kemudian dijalankan dan diuji (95 test lulus). Penulis bertanggung jawab atas pemahaman dan penyesuaian akhir.

## Lisensi dan etika

Proyek untuk keperluan perkuliahan. Seluruh data adalah simulasi; tidak ada pemindaian, eksploitasi, atau pengujian terhadap sistem pihak lain.

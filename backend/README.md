# Warehouse Recommendation System Backend Service

Service backend berbasis **Python** (**FastAPI**) yang mengintegrasikan *Machine Learning* untuk optimasi *slotting* tata letak gudang dan rute *picking* dinamis.

---

## Ringkasan Arsitektur Backend & ML

Backend ini menggunakan arsitektur 3-fase berbasis *state machine* in-memory yang dikelola secara sinkron pada siklus *lifespan* FastAPI:

```text
[STARTUP / FastAPI Lifespan]
  │  MLState diinisialisasi
  │  Training dipanggil otomatis (validate -> preprocess -> Temporal ARM -> frequencies)
  │  app.state.ml_state.is_trained = True
  ▼
[GET /api/ml/warehouse/default]  ──> Mengambil konfigurasi default untuk prefill UI
[POST /api/ml/warehouse]         ──> Setup grid gudang & hitung slotting map
  │  app.state.ml_state.is_configured = True
  ▼
[POST /api/ml/infer]             ──> Inferensi pesanan (order batching & routing)
  │  Membaca state in-memory
  ▼
Output: Batches, rute navigasi picker, perbandingan jarak tempuh vs random slotting
```

---

## Struktur Direktori

```text
backend/
├── app/
│   ├── main.py                # Entrypoint FastAPI, lifespan handler, CORS & router wiring
│   ├── config/
│   │   └── settings.py        # Pengaturan aplikasi & environment
│   ├── core/
│   │   └── ml_state.py        # Container state in-memory
│   ├── routes/                # Route controllers
│   │   ├── health.py
│   │   ├── demo.py
│   │   ├── recommend.py
│   │   └── ml.py              # POST /api/ml/train, GET /api/ml/warehouse/default,
│   │                          # POST /api/ml/warehouse, POST /api/ml/infer
│   │
│   ├── schemas/               # Validasi request & response
│   │   ├── health.py
│   │   ├── demo.py
│   │   ├── recommend.py
│   │   └── ml.py              # Schema spesifik ML pipeline
│   ├── services/
│   │   ├── ml_service.py      # Bridge antara FastAPI dan ML module
│   │   ├── recommend_service.py
│   │   └── demo_service.py
│   ├── data/                  # Dataset transaksi
│   └── utils/
│       └── exceptions.py      # Custom exception handlers
│
├── ml/                        # ML Module
│   ├── config.py              # Hyperparameter ML
│   ├── service.py             # Service wrapper ML
│   ├── pipeline.py            # Pipeline training & inferensi ML
│   ├── validation.py          # Validasi skema & kualitas dataset
│   ├── preprocessing.py       # Pembersihan data & penanganan timestamp
│   ├── temporal_arm.py        # Algoritma Temporal Weighted FP-Growth
│   ├── slotting.py            # Alokasi lokasi rak berdasar afinitas
│   ├── genetic_batching.py    # Order batching menggunakan Genetic Algorithm
│   ├── routing.py             # Navigasi picker
│   └── warehouse_simulation.py# Konstruksi grid & penghitungan jarak
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Prasyarat Sistem

* **Docker Engine** v20.10+ & **Docker Compose** v2.0+
* Atau **Python 3.12** jika running aplikasi secara manual tanpa container.

---

## Cara Menjalankan Aplikasi

### Metode 1: Menggunakan Docker Compose

1. Buka terminal di direktori `backend/`:
   ```bash
   cd backend
   ```

2. Jalankan container:
   ```bash
   docker compose up
   ```

3. Server FastAPI akan aktif di `http://localhost:8000`. Dokumentasi Swagger tersedia di `http://localhost:8000/docs`.

---

### Metode 2: Menjalankan Secara Manual dengan Python (Virtual Environment)

1. Buka terminal di direktori `backend/`:
   ```bash
   cd backend
   ```

2. Buat virtual environment Python 3.12:
   ```bash
   python -m venv venv
   ```

3. Aktifkan virtual environment:
   * **Linux / macOS**:
     ```bash
     source venv/bin/activate
     ```
   * **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **Windows (CMD)**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```

4. Install dependencies aplikasi:
   ```bash
   pip install -r requirements.txt
   ```

5. Menjalankan server pengembangan:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Konfigurasi Environment Variables

Aplikasi membaca konfigurasi dari *environment variables*. Berikut daftar variabel yang tersedia:

| Nama Variabel | Tipe | Default | Deskripsi |
|---|---|---|---|
| `ENV` | `str` | `development` | Environment aplikasi (`development` / `production`). |
| `PROJECT_NAME` | `str` | `Warehouse Recommendation System` | Nama proyek pada OpenAPI documentation. |
| `API_PREFIX` | `str` | `/api` | Prefix untuk seluruh router API. |
| `DATA_CSV_PATH` | `str` | `app/data/indonesia_e-commerce_sales_and_shipping_2023–2025/all_months_clean.csv` | Path relatif file CSV dataset utama untuk proses training. |
| `ML_RANDOM_SEED` | `int` | `42` | Random seed untuk komponen stokhastik (seperti Genetic Algorithm). |
| `LOG_LEVEL` | `str` | `INFO` | Tingkat kategori logging (`INFO`, `DEBUG`, `WARNING`, `ERROR`). |

---

## API Endpoints

### 1. Utility & Health Endpoints

* **`GET /`**
  * **Deskripsi**: Menampilkan informasi status running dan versi aplikasi.
  * **Response Sample**: `{"message": "Welcome to Warehouse Recommendation System", "version": "1.0.0", "status": "running"}`

* **`GET /health`**
  * **Deskripsi**: Pemeriksaan kesehatan server dan detail status aplikasi.

---

### 2. Demo & Legacy Endpoints

* **`GET /demo/list`**
  * **Deskripsi**: Menampilkan daftar sampel dataset demo (small, medium, large).

* **`GET /demo/{dataset_id}`**
  * **Deskripsi**: Mengambil log transaksi sampel berdasarkan ID dataset demo.

* **`POST /recommend`**
  * **Deskripsi**: Endpoint legacy rekomendasi slotting dan rute picking.

---

### 3. ML Endpoints (Prefix `/api/ml`)

* **`POST /api/ml/train`**
  * **Deskripsi**: Menjalankan ulang pipeline pelatihan model ML. Pelatihan ini otomatis dijalankan saat server startup.
  * **Response**: `TrainResponse` (`status`, `n_categories`, `n_rules`, `n_transactions_train`, `time_s`).

* **`GET /api/ml/warehouse/default`**
  * **Deskripsi**: Mengambil nilai konfigurasi tata letak gudang default untuk pengisian awal (*prefill*) form pada UI frontend.
  * **Guard**: Membutuhkan `is_trained == True`.
  * **Response**: `DefaultWarehouseResponse` (`n_aisles`, `n_positions_per_aisle`, `aisle_width`, `position_spacing`, `depot`, `total_positions`, `description`).

* **`POST /api/ml/warehouse`**
  * **Deskripsi**: Mengirimkan konfigurasi grid gudang (jumlah lorong, posisi per lorong, lokasi depot) dan menghitung alokasi *slotting* rak. Mengirimkan body kosong `{}` akan menggunakan konfigurasi default.
  * **Guard**: Membutuhkan `is_trained == True`.
  * **Request Payload**: `WarehouseConfigRequest` (`n_aisles`, `n_positions_per_aisle`, `aisle_width`, `position_spacing`, `depot`).
  * **Response**: `WarehouseConfigResponse` (`config`, `slotting_map`, `warnings`, `n_categories`, `time_s`).

* **`POST /api/ml/infer`**
  * **Deskripsi**: Mengirimkan daftar pesanan (*orders*) untuk diproses menjadi *batch* pesanan dan memberikan rute pengambilan barang terpendek.
  * **Guard**: Membutuhkan `is_trained == True` dan `is_configured == True`.
  * **Request Payload**: `InferRequest` (`orders`, `seed`).
  * **Response**: `InferResponse` (`batches`, `distance_comparison`, `slotting_map`, `summary`).

---

## Error Codes & HTTP Status

Backend mengembalikan HTTP Status `422 Unprocessable Entity` dengan payload terstruktur apabila kriteria penggunaan endpoint belum terpenuhi:

| Error Code | HTTP Status | Kondisi Penyebab |
|---|:---:|---|
| `NOT_TRAINED` | `422` | Endpoint `/warehouse` atau `/infer` dipanggil sebelum proses *training* selesai. |
| `WAREHOUSE_NOT_CONFIGURED` | `422` | Endpoint `/infer` dipanggil sebelum konfigurasi gudang disetup via `POST /api/ml/warehouse`. |
| `GRID_TOO_SMALL` | `422` | Kapasitas total posisi rak gudang yang dimasukkan lebih kecil dari jumlah kategori produk. |
| `EMPTY_ORDERS` | `422` | Payload *orders* pada request `/infer` kosong. |
| `TRAINING_FAILED` | `422` | Dataset pada `DATA_CSV_PATH` tidak ditemukan atau gagal lolos uji validasi data. |
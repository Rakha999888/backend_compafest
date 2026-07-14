# Warehouse Recommendation API 🚀
### Sistem Kecerdasan Buatan (AI) untuk Optimasi Rute & Tata Letak Gudang

Selamat datang! Proyek ini adalah sistem backend berbasis **Python (FastAPI)** dan **Docker** yang dirancang untuk membantu pengelola gudang mengoptimalkan operasional harian mereka. 

Sistem ini membantu memecahkan dua masalah terbesar di gudang:
1. **Di mana sebaiknya barang disimpan?** (*Slotting Optimization*) agar barang yang sering keluar diletakkan di tempat yang paling mudah dijangkau.
2. **Lewat jalan mana untuk mengambil barang?** (*Picking Route*) agar pekerja tidak berjalan terlalu jauh dan bisa menghemat waktu.

---

## 📦 Apa Saja Fitur Utama Aplikasi Ini?

Aplikasi ini menyediakan beberapa fitur siap pakai yang dapat diakses melalui browser:
* **Cek Status Aplikasi (`GET /health`)**: Untuk memastikan server berjalan dengan baik.
* **Daftar Simulasi Data (`GET /demo/list`)**: Menyediakan 3 pilihan ukuran data simulasi (Kecil: 10 data, Sedang: 50 data, Besar: 100 data).
* **Unduh Data Mentah (`GET /demo/{dataset_id}`)**: Melihat data transaksi barang gudang asli sebelum dioptimasi.
* **Rekomendasi AI (`POST /recommend`)**: Memproses data transaksi untuk menghasilkan rekomendasi tata letak barang baru yang lebih efisien dan rute jalan terpendek untuk pekerja.

---

## ⚙️ Cara Menjalankan Aplikasi (Sangat Mudah!)

Anda bisa memilih salah satu dari dua cara mudah berikut untuk menjalankan aplikasi di komputer Anda:

### Cara 1: Menggunakan Docker (Rekomendasi - Paling Praktis)
Jika komputer Anda sudah terpasang **Docker Desktop**, Anda tidak perlu menginstal Python secara manual.

1. Buka terminal (CMD / PowerShell / Terminal Mac) di folder proyek ini.
2. Masuk ke folder backend:
   ```bash
   cd backend
   ```
3. Jalankan perintah berikut:
   ```bash
   docker compose up
   ```
4. Selesai! Aplikasi Anda sudah aktif.

---

### Cara 2: Menjalankan Manual dengan Python
Pastikan komputer Anda sudah terpasang **Python 3.12**.

1. Buka terminal di folder proyek ini, lalu masuk ke folder backend:
   ```bash
   cd backend
   ```
2. Buat lingkungan virtual (virtual environment) agar library tidak berantakan:
   ```bash
   python -m venv venv
   ```
3. Aktifkan lingkungan virtual:
   * **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
   * **Windows (CMD)**: `.\venv\Scripts\activate.bat`
   * **Mac / Linux**: `source venv/bin/activate`
4. Install semua modul pendukung:
   ```bash
   pip install -r requirements.txt
   ```
5. Jalankan aplikasinya:
   ```bash
   uvicorn app.main:app --reload
   ```

---

## 🔎 Cara Mencoba Aplikasi & Melihat Hasil Rekomendasi

Setelah aplikasi berjalan, buka browser Anda dan kunjungi halaman berikut:

👉 **[http://localhost:8000/docs](http://localhost:8000/docs)** (Dokumentasi Swagger)

Halaman ini sangat ramah pengguna. Anda bisa langsung mencoba setiap menu (*endpoint*) secara visual dengan mengklik tombol **"Try it out"** lalu klik **"Execute"** untuk melihat hasil datanya secara langsung tanpa perlu mengetik kode pemrograman apa pun!

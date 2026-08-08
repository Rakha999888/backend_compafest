# Warehouse Recommendation System - Project Overview

Sistem Rekomendasi Slotting Gudang dan Rute Picking Dinamis Berbasis Association Rule Mining (ARM) dan Algoritma Genetika pada Data Transaksi E-Commerce Riil Indonesia.

---

## Ringkasan Proyek

Biaya logistik nasional Indonesia tercatat sebesar 14,29% dari Produk Domestik Bruto (Bappenas, Kemenko Perekonomian, & BPS, 2023). Komponen pergudangan menyumbang bagian signifikan dari biaya logistik tersebut. Di dalam operasional gudang, aktivitas pengambilan barang (*order picking*) secara konsisten terbukti menjadi komponen biaya terbesar yang memakan 50-75% dari total biaya operasional gudang (Gamal et al., 2026; Masae et al., 2020; Chiang et al., 2014).

Sebagian besar gudang e-commerce UMKM di Indonesia masih mengandalkan penataan barang (*slotting*) statis berbasis aturan sederhana (seperti ABC tradisional) atau persepsi intuitif (Amorim-Lopes et al., 2020; Öztürkoğlu, 2018). Pada lingkungan e-commerce yang memiliki tingkat volatilitas dan fluktuasi permintaan musiman yang tinggi, strategi slotting statis yang jarang dievaluasi ulang akan mengalami penurunan performa secara drastis seiring waktu (Kofler et al., 2015). Hal ini menyebabkan jarak tempuh *picker* menjadi tidak efisien dan waktu pemrosesan pesanan membengkak.

Sistem ini memecahkan dua masalah utama dalam operasional gudang manual (*picker-to-parts*):
1. **Slotting Optimization**: Menentukan posisi peletakan kategori barang di rak gudang berdasarkan frekuensi kemunculan (*turnover*) dan kekuatan asosiasi antar barang yang diperhitungkan secara temporal.
2. **Dynamic Order Batching & Routing**: Mengelompokkan beberapa pesanan ke dalam *batch* optimal serta menentukan rute pengambilan barang terpendek untuk meminimalkan jarak tempuh total *picker*.

---

## Teknologi dan Metode Utama

* **Temporal Weighted FP-Growth**: Mengekstraksi *association rules* dari transaksi historis e-commerce dengan pembobotan waktu *half-life* 90 hari. Transaksi baru diberikan bobot eksponensial lebih tinggi untuk menangkap dinamika tren pasar.
* **Integrated Cluster-Based Slotting**: Mengombinasikan skor frekuensi kategori dan matriks afinitas produk untuk menempatkan pasangan barang yang sering dibeli bersamaan pada lokasi rak yang berdekatan dan dekat dengan titik *depot*.
* **Genetic Algorithm (DEAP) Order Batching**: Mengelompokkan pesanan ke dalam *batch* berdasarkan kesamaan afinitas barang, dibatasi oleh kapasitas maksimum *picker* (misalnya 10 item per *batch*).
* **Routing Heuristics**: Menghitung rute navigasi *picker* di sepanjang lorong gudang (*aisles*) serta menyediakan estimasi penghematan jarak dibandingkan dengan penempatan barang secara acak (*random slotting*).

---

Untuk instruksi instalasi, konfigurasi environment variable, dan rincian *endpoint* API, silakan merujuk ke **[Dokumentasi Backend Lengkap](backend/README.md)**.

---

## Daftar Rujukan

1. **Bappenas, Kemenko Perekonomian, & Badan Pusat Statistik (BPS).** (2023). Layanan National Logistic Ecosystem Terus Dikembangkan Pemerintah untuk Menunjang Keberhasilan Reformasi Logistik 4.0. [www.ekon.go.id](https://ekon.go.id/publikasi/detail/5421/layanan-national-logistic-ecosystem-terus-dikembangkan-pemerintah-untuk-menunjang-keberhasilan-reformasi-logistik-40)
2. **Gamal, S., Bajba, S., Mahabub, S. A., Abdel-Aal, M. A., & Haddad, A. N.** (2026). The On-Demand Warehousing Problem: A Taxonomic Review. *Journal of Engineering*, 2026(1), Article 6109448. [https://doi.org/10.1155/je/6109448](https://doi.org/10.1155/je/6109448)
3. **Masae, M., Glock, C. H., & Grosse, E. H.** (2020). Order picker routing in warehouses: A systematic literature review. *International Journal of Production Economics*, 224, Article 107564. [https://doi.org/10.1016/j.ijpe.2019.107564](https://doi.org/10.1016/j.ijpe.2019.107564)
4. **Kofler, A., Beham, A., Wagner, S., & Affenzeller, M.** (2015). A robust storage location assignment problem considering demand location uncertainty. *Procedia Computer Science*, 60, 1422-1431. [https://doi.org/10.1007/978-3-319-15720-7_29](https://doi.org/10.1007/978-3-319-15720-7_29)
5. **Chiang, D. M. H., Lin, C., & Chen, M.** (2014). Data mining based storage assignment heuristics for travel distance reduction. *Expert Systems*, 31(1), 81-90. [https://doi.org/10.1111/exsy.12006](https://doi.org/10.1111/exsy.12006)
6. **Öztürkoğlu, Ö.** (2018). A bi-objective mathematical model for product allocation in block stacking warehouses. *International Transactions in Operational Research*, 27(4), 2184-2210. [https://doi.org/10.1111/itor.12506](https://doi.org/10.1111/itor.12506)
7. **Amorim-Lopes, M., Guimarães, L., Alves, J., & Almada-Lobo, B.** (2020). Improving picking performance at a large retailer warehouse by combining probabilistic simulation, optimization, and discrete-event simulation. *International Transactions in Operational Research*, 28(2), 687-715. [https://doi.org/10.1111/itor.12852](https://doi.org/10.1111/itor.12852)

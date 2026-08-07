# parameter untuk ARM + GA + Slotting

# ARM Berbobot Temporal

# transaksi berusia H hari mendapat bobot 0.5 vs transaksi terbaru
HALF_LIFE_DAYS: float = 60.0

# frekuensi minimum itemset agar dianggap "sering muncul bersama"
MIN_SUPPORT: float = 0.001

# seberapa sering Y muncul di transaksi yang sudah mengandung X (min 5%)
MIN_CONFIDENCE: float = 0.05

# skor afinitas = W1*suppW_norm + W2*liftW_norm
# skor afinitas = W1*(seberapa sering muncul bersama) + W2*(seberapa kuat asosiasi relatif)
W1: float = 0.3  # bobot support
W2: float = 0.7  # bobot lift, lebih dominan karena lebih informatif di dataset sparse


# Genetic Algorithm

# jumlah maksimum item unik (kategori) yang boleh ada dalam satu batch picking
BATCH_CAPACITY_MAX_ITEMS: int = 20

# jumlah individu (solusi kandidat) yang dievaluasi per generasi
POPULATION_SIZE: int = 187

# batas generasi sebagai safety limit jika stagnation tidak terpicu
N_GENERATIONS: int = 200

# probabilitas dua parent bertukar sub-kelompok batch di tiap pasangan (group-aware crossover)
CROSSOVER_RATE: float = 0.668

# probabilitas satu order di-reassign ke batch lain di tiap individu per generasi
MUTATION_RATE: float = 0.096

# jumlah individu yang bersaing untuk dipilih jadi parent (tournament selection)
TOURNAMENT_SIZE: int = 3

# generasi tanpa perbaikan fitness sebelum GA berhenti lebih awal
STAGNATION_LIMIT: int = 20

# denda per item yang melebihi BATCH_CAPACITY_MAX_ITEMS;
# cukup besar agar solusi melanggar kapasitas selalu kalah fitness
PENALTY_COEFFICIENT: float = 1000.0

# proporsi individu terbaik yang langsung lolos ke generasi berikutnya
ELITISM_RATE: float = 0.05


# Slotting

# bobot frekuensi vs sentralitas afinitas dalam skor slotting:
# Skor(c) = BETA*FrekuensiNorm + (1-BETA)*SentralitasNorm
BETA: float = 0.5


# Simulasi Gudang

# grid 5x8 = 40 slot untuk 38 kategori unik dataset primer
N_AISLES: int = 5  # aisle = lorong memanjang di gudang
N_POSITIONS_PER_AISLE: int = 8

# depot di sudut kiri bawah grid (aisle=0, position=0)
DEPOT_POSITION: tuple[int, int] = (0, 0)

AISLE_WIDTH: float = 3.0       # jarak antar lorong (unit)
POSITION_SPACING: float = 1.0  # jarak antar posisi dalam satu lorong (unit)


# seed default untuk GA batching, simulasi gudang, dan imputasi timestamp
RANDOM_SEED: int = 42


# Komputasi Paralel

# 0 = auto-detect via os.cpu_count(), 1 = sequential
N_WORKERS: int = 0

# di bawah threshold ini overhead serialisasi > benefit paralel
PARALLEL_FITNESS_THRESHOLD: int = 50

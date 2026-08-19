"""Genetic Algorithm (GA) untuk order batching berbasis score afinitas antar kategori."""

from __future__ import annotations

import logging
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ml.config import (
    BATCH_CAPACITY_MAX_ITEMS,
    CROSSOVER_RATE,
    ELITISM_RATE,
    MUTATION_RATE,
    N_GENERATIONS,
    N_WORKERS,
    PARALLEL_FITNESS_THRESHOLD,
    PENALTY_COEFFICIENT,
    POPULATION_SIZE,
    RANDOM_SEED,
    STAGNATION_LIMIT,
    TOURNAMENT_SIZE,
)
from ml.temporal_arm import AffinityMatrix

logger = logging.getLogger(__name__)

@dataclass
class Order:
    """Satu order dengan daftar kategorinya."""

    order_id: str
    categories: list[str]
    n_items: int = 0

    def __post_init__(self):
        self.n_items = len(self.categories)

@dataclass
class BatchingResult:
    """Hasil pengelompokan order ke batch."""

    assignment: dict[str, int]       # order_id -> batch_index
    batches: list[list[str]]         # daftar batch, isi = list order_id
    fitness_history: list[float]
    best_fitness: float
    n_batches: int
    metadata: dict[str, Any] = field(default_factory=dict)

def normalize_rgf(chromosome: list[int]) -> list[int]:
    """Normalisasi kromosom ke bentuk kanonik RGF (Restricted Growth Function), contoh: [3,1,3,2,1] -> [0,1,0,2,1]."""
    mapping = {}
    next_id = 0
    result = []
    for gene in chromosome:
        if gene not in mapping:
            mapping[gene] = next_id
            next_id += 1
        result.append(mapping[gene])
    return result

def compute_fitness(
    chromosome: list[int],
    orders: list[Order],
    affinity: AffinityMatrix,
    max_items_per_batch: int = BATCH_CAPACITY_MAX_ITEMS,
    penalty_coeff: float = PENALTY_COEFFICIENT,
) -> float:
    """Fitness = total afinitas antar kategori dalam batch - penalti pelanggaran kapasitas."""
    batches: dict[int, list[int]] = {}
    for order_idx, batch_idx in enumerate(chromosome):
        if batch_idx not in batches:
            batches[batch_idx] = []
        batches[batch_idx].append(order_idx)

    total_affinity = 0.0
    total_violation = 0

    for batch_idx, order_indices in batches.items():
        batch_items = sum(orders[i].n_items for i in order_indices)
        if batch_items > max_items_per_batch:
            total_violation += batch_items - max_items_per_batch

        batch_categories: set[str] = set()
        for i in order_indices:
            batch_categories.update(orders[i].categories)

        total_affinity += affinity.get_upper_triangle_sum(list(batch_categories))

    return total_affinity - penalty_coeff * total_violation

def _compute_fitness_single(args: tuple) -> float:
    """Wrapper untuk parallel fitness evaluation via ProcessPoolExecutor.map()."""
    chrom, orders, affinity, max_items, penalty = args
    return compute_fitness(chrom, orders, affinity, max_items, penalty)

def _get_n_workers() -> int:
    """Tentukan jumlah worker berdasarkan config."""
    if N_WORKERS == 0:
        return max(1, (os.cpu_count() or 1))
    return max(1, N_WORKERS)

def _evaluate_population(
    population: list[list[int]],
    orders: list[Order],
    affinity: AffinityMatrix,
    max_items_per_batch: int,
    penalty_coeff: float,
    n_workers: int,
    use_parallel: bool,
) -> list[float]:
    """Evaluasi fitness seluruh populasi (sequential atau parallel)."""
    if use_parallel and n_workers > 1:
        args = [
            (chrom, orders, affinity, max_items_per_batch, penalty_coeff)
            for chrom in population
        ]
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            return list(executor.map(_compute_fitness_single, args))
    else:
        return [
            compute_fitness(
                chrom, orders, affinity, max_items_per_batch, penalty_coeff
            )
            for chrom in population
        ]

def init_chromosome(
    n_orders: int,
    max_batches: int,
    rng: random.Random | None = None,
) -> list[int]:
    """Inisialisasi kromosom acak."""
    r = rng if rng is not None else random
    chrom = [r.randint(0, max_batches - 1) for _ in range(n_orders)]
    return normalize_rgf(chrom)

def group_aware_crossover(
    parent1: list[int],
    parent2: list[int],
    rng: random.Random | None = None,
) -> tuple[list[int], list[int]]:
    """Group-aware crossover: tukar subset kelompok utuh antar induk."""
    r = rng if rng is not None else random
    n = len(parent1)

    groups_p1 = set(parent1)
    n_groups_select = max(1, len(groups_p1) // 2)
    selected_groups = set(r.sample(sorted(groups_p1), n_groups_select))

    child1 = list(parent1)
    for i in range(n):
        if parent1[i] not in selected_groups:
            child1[i] = parent2[i]

    groups_p2 = set(parent2)
    n_groups_select2 = max(1, len(groups_p2) // 2)
    selected_groups2 = set(r.sample(sorted(groups_p2), n_groups_select2))

    child2 = list(parent2)
    for i in range(n):
        if parent2[i] not in selected_groups2:
            child2[i] = parent1[i]

    return normalize_rgf(child1), normalize_rgf(child2)

def single_order_mutation(
    chromosome: list[int],
    rng: random.Random | None = None,
) -> list[int]:
    """Mutasi: reassign satu order ke batch lain secara acak."""
    r = rng if rng is not None else random
    chrom = list(chromosome)
    n = len(chrom)
    idx = r.randint(0, n - 1)
    max_group = max(chrom) + 1  # boleh membuat batch baru
    chrom[idx] = r.randint(0, max_group)
    return normalize_rgf(chrom)

def run_ga_batching(
    orders: list[Order],
    affinity: AffinityMatrix,
    population_size: int = POPULATION_SIZE,
    n_generations: int = N_GENERATIONS,
    crossover_rate: float = CROSSOVER_RATE,
    mutation_rate: float = MUTATION_RATE,
    tournament_size: int = TOURNAMENT_SIZE,
    stagnation_limit: int = STAGNATION_LIMIT,
    elitism_rate: float = ELITISM_RATE,
    max_items_per_batch: int = BATCH_CAPACITY_MAX_ITEMS,
    penalty_coeff: float = PENALTY_COEFFICIENT,
    seed: int = RANDOM_SEED,
) -> BatchingResult:
    """Jalankan GA untuk order batching."""
    rng = random.Random(seed)
    t_start = time.time()

    n_orders = len(orders)
    if n_orders == 0:
        return BatchingResult(
            assignment={}, batches=[], fitness_history=[],
            best_fitness=0.0, n_batches=0,
        )

    total_items = sum(o.n_items for o in orders)
    max_batches = max(2, (total_items // max_items_per_batch) + 2)
    n_elite = max(1, int(population_size * elitism_rate))

    n_workers = _get_n_workers()
   
    use_parallel = False
    logger.info(
        "GA batching: %d orders, max_batches=%d, pop=%d, gen=%d (sequential)",
        n_orders, max_batches, population_size, n_generations,
    )

    population = [
        init_chromosome(n_orders, max_batches, rng=rng)
        for _ in range(population_size)
    ]

    fitness_values = _evaluate_population(
        population, orders, affinity,
        max_items_per_batch, penalty_coeff,
        n_workers, use_parallel,
    )

    fitness_history = []
    best_fitness_ever = max(fitness_values)
    stagnation_count = 0

    for gen in range(n_generations):
        current_best = max(fitness_values)
        fitness_history.append(current_best)

        if current_best > best_fitness_ever + 1e-9:
            best_fitness_ever = current_best
            stagnation_count = 0
        else:
            stagnation_count += 1

        if stagnation_count >= stagnation_limit:
            logger.info(
                "stagnasi: berhenti di generasi %d (%d generasi tanpa perbaikan)",
                gen, stagnation_limit,
            )
            break

        if gen % 50 == 0 or gen == n_generations - 1:
            avg_fit = sum(fitness_values) / len(fitness_values)
            logger.info(
                "gen %d: best=%.4f, avg=%.4f, stagnasi=%d/%d",
                gen, current_best, avg_fit, stagnation_count, stagnation_limit,
            )

        sorted_indices = sorted(
            range(len(fitness_values)),
            key=lambda i: fitness_values[i],
            reverse=True,
        )
        elite = [list(population[i]) for i in sorted_indices[:n_elite]]
        elite_fitness = [fitness_values[i] for i in sorted_indices[:n_elite]]

        selected = []
        for _ in range(population_size - n_elite):
            tournament = rng.sample(range(len(population)), tournament_size)
            winner = max(tournament, key=lambda i: fitness_values[i])
            selected.append(list(population[winner]))

        offspring = []
        for i in range(0, len(selected) - 1, 2):
            if rng.random() < crossover_rate:
                c1, c2 = group_aware_crossover(selected[i], selected[i + 1], rng=rng)
                offspring.extend([c1, c2])
            else:
                offspring.extend([list(selected[i]), list(selected[i + 1])])

        if len(selected) % 2 == 1:
            offspring.append(list(selected[-1]))

        for i in range(len(offspring)):
            if rng.random() < mutation_rate:
                offspring[i] = single_order_mutation(offspring[i], rng=rng)

        trimmed_offspring = offspring[:population_size - n_elite]
        population = elite + trimmed_offspring

        offspring_fitness = _evaluate_population(
            trimmed_offspring, orders, affinity,
            max_items_per_batch, penalty_coeff,
            n_workers, use_parallel,
        )
        fitness_values = elite_fitness + offspring_fitness

    best_idx = max(range(len(fitness_values)), key=lambda i: fitness_values[i])
    best_chrom = normalize_rgf(population[best_idx])
    best_fit = fitness_values[best_idx]

    assignment = {}
    batch_orders: dict[int, list[str]] = {}
    for order_idx, batch_idx in enumerate(best_chrom):
        oid = orders[order_idx].order_id
        assignment[oid] = batch_idx
        if batch_idx not in batch_orders:
            batch_orders[batch_idx] = []
        batch_orders[batch_idx].append(oid)

    batches = [batch_orders[k] for k in sorted(batch_orders)]
    t_elapsed = time.time() - t_start

    return BatchingResult(
        assignment=assignment,
        batches=batches,
        fitness_history=fitness_history,
        best_fitness=best_fit,
        n_batches=len(batches),
        metadata={
            "population_size": population_size,
            "n_generations_run": len(fitness_history),
            "crossover_rate": crossover_rate,
            "mutation_rate": mutation_rate,
            "stagnation_limit": stagnation_limit,
            "seed": seed,
            "elapsed_seconds": round(t_elapsed, 2),
            "max_items_per_batch": max_items_per_batch,
            "n_orders": n_orders,
            "stagnation_triggered": stagnation_count >= stagnation_limit,
        },
    )

def run_ga_multi_seed(
    orders: list[Order],
    affinity: AffinityMatrix,
    n_runs: int = 5,
    base_seed: int = RANDOM_SEED,
    **kwargs,
) -> list[BatchingResult]:
    """Jalankan GA dengan beberapa seed untuk reproduksibilitas."""
    n_workers = _get_n_workers()
    use_parallel_seeds = n_workers > 1 and n_runs > 1

    if use_parallel_seeds:
        logger.info(
            "multi-seed: %d runs diparalelkan (%d workers)",
            n_runs, min(n_workers, n_runs),
        )
        # Per-run parallelism dimatikan untuk menghindari nested parallelism
        seeds = [base_seed + i for i in range(n_runs)]

        def _run_single_seed(s: int) -> BatchingResult:
            return run_ga_batching(orders, affinity, seed=s, **kwargs)

        with ProcessPoolExecutor(
            max_workers=min(n_workers, n_runs)
        ) as executor:
            results = list(executor.map(_run_single_seed, seeds))
        return results
    else:
        results = []
        for i in range(n_runs):
            seed = base_seed + i
            logger.info("multi-seed run %d/%d (seed=%d)", i + 1, n_runs, seed)
            result = run_ga_batching(orders, affinity, seed=seed, **kwargs)
            results.append(result)
        return results

def summarize_multi_seed(results: list[BatchingResult]) -> dict[str, Any]:
    """Rangkum hasil multi-seed run."""
    fitness_values = [r.best_fitness for r in results]
    n_batches = [r.n_batches for r in results]
    times = [r.metadata.get("elapsed_seconds", 0) for r in results]

    return {
        "n_runs": len(results),
        "fitness_mean": np.mean(fitness_values),
        "fitness_std": np.std(fitness_values),
        "fitness_min": min(fitness_values),
        "fitness_max": max(fitness_values),
        "n_batches_mean": np.mean(n_batches),
        "n_batches_std": np.std(n_batches),
        "time_mean": np.mean(times),
        "time_std": np.std(times),
        "seeds": [r.metadata.get("seed", 0) for r in results],
    }

def orders_from_transactions(
    transactions: Any,
) -> list[Order]:
    """Konversi DataFrame transaksi menjadi list[Order]."""
    orders = []
    for _, row in transactions.iterrows():
        orders.append(Order(
            order_id=str(row["order_id"]),
            categories=list(row["itemset"]),
        ))
    return orders

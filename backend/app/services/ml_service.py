import logging
import time
from typing import Optional

from app.config.settings import settings
from app.core.ml_state import MLState

logger = logging.getLogger(__name__)

class MLService:

    def train(self, state: MLState) -> dict:
        """Run full training pipeline."""
        from ml.preprocessing import load_primary_dataset, preprocess_primary

        state.seed = settings.get_random_seed()
        logger.info("random seed terpasang: %d", state.seed)
        from ml.temporal_arm import run_temporal_arm_pipeline
        from ml.validation import validate_primary_dataset
        from ml.warehouse_simulation import compute_category_frequencies

        t_start = time.time()

        df = load_primary_dataset(settings.DATA_CSV_PATH)
        report = validate_primary_dataset(df)
        if report.has_critical_failures:
            failures = [r.message for r in report.critical_failures]
            raise ValueError("Validasi dataset gagal:\n" + "\n".join(failures))

        if report.warnings:
            for w in report.warnings:
                logger.warning(f"Peringatan validasi dataset: {w.rule_name} -> {w.message}")

        # full dataset, tidak ada split (demo pakai dummy orders)
        data = preprocess_primary(df)

        categories = sorted(data.binary_matrix.columns.tolist())
        affinity = run_temporal_arm_pipeline(
            data.transactions,
            data.binary_matrix,
            categories,
        )
        frequencies = compute_category_frequencies(data.transactions)

        state.affinity = affinity
        state.categories = categories
        state.frequencies = frequencies
        state.train_data = data
        state.train_meta = {
            "n_categories": len(categories),
            "n_rules": int(affinity.metadata.get("n_rules", 0)),
            "n_transactions_train": len(data.transactions),
            "time_s": round(time.time() - t_start, 2),
        }
        state.is_trained = True

        logger.info(
            "training selesai: %d kategori, %d aturan, %.2fs",
            len(categories),
            affinity.metadata.get("n_rules", 0),
            time.time() - t_start,
        )
        return state.train_meta

    def configure_warehouse(self, state: MLState, config_dict: dict) -> dict:
        """Setup grid + slotting. config_dict kosong -> pakai default."""
        from ml.service import WarehouseConfig
        from ml.service import configure_warehouse as ml_configure_warehouse

        if config_dict and "depot" in config_dict:
            config_dict = {**config_dict, "depot": tuple(config_dict["depot"])}

        config = WarehouseConfig(**config_dict) if config_dict else None
        result = ml_configure_warehouse(state.train_data, state.affinity, config)

        state.warehouse_result = result
        state.is_configured = True

        warnings = [
            {"code": m.code, "message": m.message}
            for m in result.validation.messages
            if m.level == "warning"
        ]

        return {
            "config": {
                "n_aisles": result.config.n_aisles,
                "n_positions_per_aisle": result.config.n_positions_per_aisle,
                "aisle_width": result.config.aisle_width,
                "position_spacing": result.config.position_spacing,
                "depot": list(result.config.depot),
            },
            "slotting_map": result.slotting_map,
            "warnings": warnings,
            "n_categories": result.n_categories,
            "time_s": result.time_s,
        }

    def infer(self, state: MLState, orders: list[dict], seed: Optional[int] = None) -> dict:
        from ml.service import infer as ml_infer

        actual_seed = seed if seed is not None else (state.seed or settings.get_random_seed())
        result = ml_infer(
            orders=orders,
            affinity=state.affinity,
            slotting=state.warehouse_result.slotting,
            grid=state.warehouse_result.grid,
            categories=state.categories,
            frequencies=state.frequencies,
            seed=actual_seed,
        )

        return {
            "batches": result.batches,
            "distance_comparison": result.distance_comparison,
            "slotting_map": result.slotting_map,
            "summary": result.summary,
        }

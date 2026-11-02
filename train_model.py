import argparse
import logging
import os
import pickle
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from app import CATEGORICAL_COLUMNS, TARGET_COLUMN, encode_categories, engineer_features

PROJECT_DIR = Path(__file__).resolve().parent
EXCLUDED_FEATURES = ("Driver", "Race", "Year")
RANDOM_STATE = 42
logger = logging.getLogger("f1_pit_stop_training")


def build_feature_frame(
    source: pd.DataFrame,
    encoders: dict[str, dict[str, float]],
    global_mean: float,
) -> pd.DataFrame:
    columns_to_drop = ["id", TARGET_COLUMN, *EXCLUDED_FEATURES]
    missing_columns = sorted(set(columns_to_drop).difference(source.columns))
    if missing_columns:
        raise ValueError(
            "Training data is missing required columns: "
            + ", ".join(missing_columns)
        )

    raw_features = source.drop(columns=columns_to_drop)
    engineered = engineer_features(raw_features)
    encoded = encode_categories(engineered, encoders, global_mean)
    if set(EXCLUDED_FEATURES).intersection(encoded.columns):
        raise ValueError("Excluded features unexpectedly remain in the model inputs")
    return encoded


def stratified_split(target: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    random = np.random.default_rng(RANDOM_STATE)
    validation_indexes: list[np.ndarray] = []
    for label in sorted(target.unique()):
        indexes = np.flatnonzero(target.to_numpy() == label)
        if len(indexes) < 2:
            raise ValueError(f"Not enough training examples for class {label}")
        random.shuffle(indexes)
        validation_size = max(1, int(round(len(indexes) * 0.2)))
        validation_indexes.append(indexes[:validation_size])

    validation = np.concatenate(validation_indexes)
    random.shuffle(validation)
    is_validation = np.zeros(len(target), dtype=bool)
    is_validation[validation] = True
    return np.flatnonzero(~is_validation), validation


def make_model(
    *,
    scale_pos_weight: float,
    n_estimators: int,
    early_stopping: bool,
) -> XGBClassifier:
    model_options: dict[str, object] = {
        "n_estimators": n_estimators,
        "learning_rate": 0.08,
        "max_depth": 7,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 0.5,
        "reg_alpha": 0.3,
        "min_child_weight": 5,
        "scale_pos_weight": scale_pos_weight,
        "tree_method": "hist",
        "max_bin": 128,
        "n_jobs": min(4, os.cpu_count() or 1),
        "eval_metric": "auc",
        "random_state": RANDOM_STATE,
    }
    if early_stopping:
        model_options["early_stopping_rounds"] = 50
    return XGBClassifier(**model_options)


def train_and_save_model(
    training_data_path: Path,
    model_path: Path,
) -> tuple[float, int, list[str]]:
    if not training_data_path.is_file():
        raise FileNotFoundError(f"Training data file was not found: {training_data_path}")

    training_data = pd.read_csv(training_data_path)
    required_columns = {
        "id",
        TARGET_COLUMN,
        *EXCLUDED_FEATURES,
        *CATEGORICAL_COLUMNS,
        "PitStop",
        "LapNumber",
        "Stint",
        "TyreLife",
        "Position",
        "LapTime (s)",
        "LapTime_Delta",
        "Cumulative_Degradation",
        "RaceProgress",
        "Position_Change",
    }
    missing_columns = sorted(required_columns.difference(training_data.columns))
    if missing_columns:
        raise ValueError(
            "Training data is missing required columns: "
            + ", ".join(missing_columns)
        )
    if training_data.empty or training_data[TARGET_COLUMN].isna().any():
        raise ValueError("Training data must contain non-empty, labeled rows")
    target = training_data[TARGET_COLUMN].astype(int)
    if not target.isin([0, 1]).all():
        raise ValueError(f"{TARGET_COLUMN} must contain labeled binary targets")

    global_mean = float(target.mean())
    target_encoders = {
        column: target.groupby(training_data[column]).mean().to_dict()
        for column in CATEGORICAL_COLUMNS
    }
    features = build_feature_frame(training_data, target_encoders, global_mean)
    feature_names = [str(column) for column in features.columns]
    if set(EXCLUDED_FEATURES).intersection(feature_names):
        raise ValueError("The training matrix contains a feature marked for removal")

    medians = features.median(axis=0)
    if not np.isfinite(medians.to_numpy(dtype=float)).all():
        raise ValueError("Training data cannot provide finite medians for all features")
    features = features.replace([np.inf, -np.inf], np.nan).fillna(medians)

    training_indexes, validation_indexes = stratified_split(target)
    training_target = target.iloc[training_indexes]
    positive_count = int((training_target == 1).sum())
    negative_count = int((training_target == 0).sum())
    if positive_count == 0:
        raise ValueError("The training split must contain positive examples")

    validation_model = make_model(
        scale_pos_weight=negative_count / positive_count,
        n_estimators=500,
        early_stopping=True,
    )
    validation_model.fit(
        features.iloc[training_indexes],
        training_target,
        eval_set=[
            (features.iloc[validation_indexes], target.iloc[validation_indexes])
        ],
        verbose=50,
    )
    validation_auc = max(validation_model.evals_result()["validation_0"]["auc"])
    best_n_estimators = int(validation_model.best_iteration) + 1

    final_model = make_model(
        scale_pos_weight=negative_count / positive_count,
        n_estimators=best_n_estimators,
        early_stopping=False,
    )
    final_model.fit(features, target, verbose=False)
    booster = final_model.get_booster()
    if booster.num_features() != len(feature_names):
        raise ValueError("The trained model has an unexpected number of features")
    if booster.feature_names is not None and booster.feature_names != feature_names:
        raise ValueError("The trained model contains an unexpected feature order")
    booster.feature_names = feature_names
    if list(final_model.feature_names_in_) != feature_names:
        raise ValueError("The trained model did not retain the expected feature order")

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=model_path.parent,
        prefix=f"{model_path.stem}_",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        try:
            pickle.dump(final_model, temporary_file, protocol=pickle.HIGHEST_PROTOCOL)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    try:
        temporary_path.replace(model_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    logger.info(
        "Saved %d-feature model to %s (validation ROC-AUC %.4f, %d trees)",
        len(feature_names),
        model_path,
        validation_auc,
        best_n_estimators,
    )
    return validation_auc, best_n_estimators, feature_names


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the pit-stop model without driver, circuit, or year features."
    )
    parser.add_argument(
        "--train-data",
        type=Path,
        default=PROJECT_DIR / "train.csv",
        help="Path to the labeled training CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_DIR / "pitstop.pkl",
        help="Path for the trained XGBoost pickle.",
    )
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    validation_auc, tree_count, features = train_and_save_model(
        arguments.train_data.resolve(),
        arguments.output.resolve(),
    )
    print(f"Validation ROC-AUC: {validation_auc:.4f}")
    print(f"Saved {tree_count} trees with {len(features)} features to {arguments.output}")
    print(f"Removed features: {', '.join(EXCLUDED_FEATURES)}")


if __name__ == "__main__":
    main()

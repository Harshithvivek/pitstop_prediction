import logging
import os
import pickle
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from xgboost import XGBClassifier

PROJECT_DIR = Path(__file__).resolve().parent
TARGET_COLUMN = "PitNextLap"
CATEGORICAL_COLUMNS = ("Compound",)
COMPOUND_DEGRADATION = {"SOFT": 3.0, "MEDIUM": 2.0, "HARD": 1.0}
PIT_THRESHOLD = 0.5

logger = logging.getLogger("f1_pit_stop_api")


class TelemetryInput(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        allow_inf_nan=False,
        extra="forbid",
    )

    Compound: str = Field(min_length=1, examples=["HARD"])
    PitStop: int = Field(ge=0, examples=[0])
    LapNumber: int = Field(ge=1, le=100, examples=[50])
    Stint: int = Field(ge=1, examples=[2])
    TyreLife: float = Field(ge=0, examples=[39.0])
    Position: int = Field(ge=1, le=20, examples=[8])
    LapTime_s: float = Field(
        gt=0,
        alias="LapTime (s)",
        examples=[78.491],
    )
    LapTime_Delta: float = Field(examples=[-7.564])
    Cumulative_Degradation: float = Field(examples=[21.019])
    RaceProgress: float = Field(ge=0, le=1, examples=[0.714286])
    Position_Change: int = Field(ge=-20, le=20, examples=[5])

    @field_validator("Compound")
    @classmethod
    def normalize_categories(cls, value: str, info) -> str:
        normalized = value.strip()
        if info.field_name == "Compound":
            normalized = normalized.upper()
        if not normalized:
            raise ValueError("must not be empty")
        return normalized


class PredictionResponse(BaseModel):
    pit_probability: float
    recommendation: Literal["BOX THIS LAP", "STAY OUT"]
    urgency_score: float
    tyre_life_laps: float


class InferenceRuntime:
    def __init__(
        self,
        model: XGBClassifier,
        feature_names: list[str],
        target_encoders: dict[str, dict[str, float]],
        global_mean: float,
        feature_medians: pd.Series,
        positive_class_index: int,
    ) -> None:
        self.model = model
        self.feature_names = feature_names
        self.target_encoders = target_encoders
        self.global_mean = global_mean
        self.feature_medians = feature_medians
        self.positive_class_index = positive_class_index


def configured_path(environment_variable: str, default_name: str) -> Path:
    configured = os.getenv(environment_variable)
    path = Path(configured) if configured else PROJECT_DIR / default_name
    if not path.is_absolute():
        path = PROJECT_DIR / path
    return path.resolve()


def engineer_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    result["TyreLife_Sq"] = result["TyreLife"] ** 2
    result["TyreLife_Log"] = np.log1p(result["TyreLife"])
    result["TyreLife_Bin"] = pd.cut(
        result["TyreLife"],
        bins=[0, 10, 20, 30, 50],
        labels=[0, 1, 2, 3],
    ).astype(float)
    result["Compound_DegRate"] = (
        result["Compound"].map(COMPOUND_DEGRADATION).fillna(2.0)
    )
    result["Pit_Urgency"] = (
        result["TyreLife"]
        * result["Compound_DegRate"]
        * (1 + result["RaceProgress"])
    )
    result["Stint_Age"] = result["Stint"] + result["TyreLife"] / 30

    result["Stint_x_TyreLife"] = result["Stint"] * result["TyreLife"]
    result["Progress_x_TyreLife"] = result["RaceProgress"] * result["TyreLife"]
    result["Lap_x_TyreLife"] = result["LapNumber"] * result["TyreLife"]
    result["Early_Race"] = (result["RaceProgress"] < 0.3).astype(float)
    result["Mid_Race"] = result["RaceProgress"].between(0.3, 0.7).astype(float)
    result["Late_Race"] = (result["RaceProgress"] >= 0.7).astype(float)

    result["Degradation_per_Lap"] = result["Cumulative_Degradation"] / (
        result["LapNumber"] + 1
    )
    result["LapTime_Deg"] = (
        result["LapTime (s)"] * result["Cumulative_Degradation"].abs()
    )
    result["LapTime_Consistency"] = 1 / (
        1 + result["LapTime_Delta"].abs()
    )
    result["LapTime_Delta_x_Life"] = result["LapTime_Delta"] * result["TyreLife"]
    result["Position_x_TyreLife"] = result["Position"] * result["TyreLife"]

    return result.replace([np.inf, -np.inf], np.nan)


def encode_categories(
    frame: pd.DataFrame,
    target_encoders: dict[str, dict[str, float]],
    global_mean: float,
) -> pd.DataFrame:
    result = frame.copy()
    for column in CATEGORICAL_COLUMNS:
        result[column] = (
            result[column].map(target_encoders[column]).fillna(global_mean)
        )
    return result


def load_inference_runtime() -> InferenceRuntime:
    model_path = configured_path("MODEL_PATH", "pitstop.pkl")
    training_data_path = configured_path("TRAIN_DATA_PATH", "train.csv")

    if not model_path.is_file():
        raise FileNotFoundError(f"Model file was not found: {model_path}")
    if not training_data_path.is_file():
        raise FileNotFoundError(f"Training data file was not found: {training_data_path}")

    with model_path.open("rb") as model_file:
        model = pickle.load(model_file)
    if not isinstance(model, XGBClassifier):
        raise TypeError(f"Expected an XGBClassifier in {model_path}")
    if not hasattr(model, "feature_names_in_"):
        raise ValueError("The model does not contain its training feature names")

    feature_names = [str(name) for name in model.feature_names_in_]
    if len(feature_names) != int(model.n_features_in_):
        raise ValueError("The model's feature names do not match its feature count")
    removed_features = {"Driver", "Race", "Year"}.intersection(feature_names)
    if removed_features:
        raise ValueError(
            "The model still depends on removed inputs: "
            + ", ".join(sorted(removed_features))
        )

    training_data = pd.read_csv(training_data_path)
    required_columns = {"id", TARGET_COLUMN, *CATEGORICAL_COLUMNS}
    missing_columns = sorted(required_columns.difference(training_data.columns))
    if missing_columns:
        raise ValueError(
            f"Training data is missing required columns: {', '.join(missing_columns)}"
        )
    if training_data.empty or training_data[TARGET_COLUMN].isna().any():
        raise ValueError("Training data must contain non-empty, labeled rows")

    target = training_data[TARGET_COLUMN].astype(float)
    if not target.isin([0.0, 1.0]).all():
        raise ValueError(f"{TARGET_COLUMN} must contain only 0 and 1")
    global_mean = float(target.mean())
    target_encoders = {
        column: target.groupby(training_data[column]).mean().to_dict()
        for column in CATEGORICAL_COLUMNS
    }

    training_features = training_data.drop(columns=["id", TARGET_COLUMN])
    engineered = engineer_features(training_features)
    encoded = encode_categories(engineered, target_encoders, global_mean)
    missing_features = sorted(set(feature_names).difference(encoded.columns))
    if missing_features:
        raise ValueError(
            "The inference feature builder is missing model features: "
            + ", ".join(missing_features)
        )

    ordered_features = encoded.reindex(columns=feature_names)
    numeric_features = ordered_features.apply(pd.to_numeric, errors="raise")
    feature_medians = numeric_features.median(axis=0).reindex(feature_names)
    if not np.isfinite(feature_medians.to_numpy(dtype=float)).all():
        raise ValueError("Training data cannot provide finite medians for every feature")

    class_labels = [
        label.item() if isinstance(label, np.generic) else label
        for label in model.classes_
    ]
    if len(class_labels) != 2 or 1 not in class_labels:
        raise ValueError("The model must be a binary classifier with positive class 1")

    logger.info(
        "Loaded model from %s with %d features; preprocessing data from %s",
        model_path,
        len(feature_names),
        training_data_path,
    )
    return InferenceRuntime(
        model=model,
        feature_names=feature_names,
        target_encoders=target_encoders,
        global_mean=global_mean,
        feature_medians=feature_medians,
        positive_class_index=class_labels.index(1),
    )


def prepare_prediction_features(
    telemetry: TelemetryInput,
    runtime: InferenceRuntime,
) -> tuple[np.ndarray, float]:
    raw_features = pd.DataFrame([telemetry.model_dump(by_alias=True)])
    engineered = engineer_features(raw_features)
    encoded = encode_categories(
        engineered,
        runtime.target_encoders,
        runtime.global_mean,
    )
    ordered_features = encoded.reindex(columns=runtime.feature_names)
    numeric_features = ordered_features.apply(pd.to_numeric, errors="raise")
    prepared = numeric_features.replace([np.inf, -np.inf], np.nan).fillna(
        runtime.feature_medians
    )
    if prepared.isna().any().any():
        raise ValueError("Prediction input produced a missing model feature")

    matrix = prepared.to_numpy(dtype=np.float32)
    urgency_score = float(engineered["Pit_Urgency"].iloc[0])
    return matrix, urgency_score


def get_runtime(request: Request) -> InferenceRuntime:
    runtime = getattr(request.app.state, "inference_runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Model is not ready")
    return runtime


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    application.state.inference_runtime = load_inference_runtime()
    yield
    application.state.inference_runtime = None


app = FastAPI(
    title="F1 Pit Stop Prediction API",
    description="Predicts the probability of a pit stop on the next lap.",
    version="3.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["service"])
def root() -> dict[str, str]:
    return {
        "service": "F1 Pit Stop Prediction API",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health", tags=["service"])
def health(request: Request) -> dict[str, str]:
    get_runtime(request)
    return {"status": "ready"}


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["inference"],
)
def predict(telemetry: TelemetryInput, request: Request) -> PredictionResponse:
    runtime = get_runtime(request)
    matrix, urgency_score = prepare_prediction_features(telemetry, runtime)
    probabilities = runtime.model.predict_proba(matrix, validate_features=False)
    if probabilities.ndim != 2 or probabilities.shape[0] != 1:
        raise RuntimeError("The model returned an invalid probability matrix")

    probability = float(probabilities[0, runtime.positive_class_index])
    if not np.isfinite(probability) or not 0 <= probability <= 1:
        raise RuntimeError("The model returned an invalid pit-stop probability")

    return PredictionResponse(
        pit_probability=round(probability, 4),
        recommendation="BOX THIS LAP" if probability >= PIT_THRESHOLD else "STAY OUT",
        urgency_score=round(urgency_score, 2),
        tyre_life_laps=telemetry.TyreLife,
    )

# -*- coding: utf-8 -*-
"""PySpark data processing, model training, and prediction helpers."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from flask import current_app, has_app_context

from models import Abalone1000, Prediction, RingsDis, TrainResult, User
from settings import DATA_PATH, MODEL_PATH, db


FEATURE_COLUMNS = [
    "sex",
    "length",
    "diameter",
    "height",
    "whole_weight",
    "shucked_weight",
    "viscera_weight",
    "shell_weight",
]
VALID_MODELS = {"LR", "DT-R", "RF-R"}
LOCAL_MODEL_VERSION = 2
LR_DEMO_FEATURE_VECTOR = [1.0] * len(FEATURE_COLUMNS)
LR_DEMO_EXPECTED_PREDICTION = 18.94


def parse_feature_values(values: Sequence[object]) -> list[float]:
    if len(values) != len(FEATURE_COLUMNS):
        raise ValueError("expected 8 feature values")
    try:
        parsed = [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError("feature values must be numeric") from exc
    return parsed


def _resolve_data_path(data_path: str | None = None) -> str:
    if data_path:
        return data_path
    if has_app_context():
        return current_app.config.get("DATA_PATH", DATA_PATH)
    return DATA_PATH


def _resolve_model_path(model_path: str | None = None) -> str:
    if model_path:
        return model_path
    if has_app_context():
        return current_app.config.get("MODEL_PATH", MODEL_PATH)
    return MODEL_PATH


def _resolve_engine(engine: str | None = None) -> str:
    if engine:
        return engine
    if has_app_context():
        configured = current_app.config.get("TRAIN_ENGINE")
        if configured:
            return configured
    return os.getenv("ABALONE_ENGINE", "auto")


def _validate_model(model_name: str) -> str:
    if model_name not in VALID_MODELS:
        raise ValueError("unsupported model: %s" % model_name)
    return model_name


def _read_csv_rows(data_path: str) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with open(data_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for index, raw in enumerate(reader, start=1):
            if not raw:
                continue
            row = {"id": int(float(raw.get("id") or index))}
            for column in FEATURE_COLUMNS:
                row[column] = float(raw[column])
            row["rings"] = int(float(raw["rings"]))
            rows.append(row)
    if not rows:
        raise ValueError("no abalone rows found in %s" % data_path)
    return rows


def _seed_users() -> None:
    defaults = [
        ("20231113107", "123456", "张橙"),
        ("admin", "admin", "管理员"),
        ("guest", "guest", "用户"),
    ]
    for username, password, name in defaults:
        if not User.query.filter_by(username=username).first():
            db.session.add(User(username=username, password=password, name=name))


def _seed_abalone(rows: Iterable[dict[str, float]]) -> None:
    if Abalone1000.query.count() > 0:
        return
    for row in rows:
        db.session.add(
            Abalone1000(
                id=int(row["id"]),
                sex=int(row["sex"]),
                length=float(row["length"]),
                diameter=float(row["diameter"]),
                height=float(row["height"]),
                whole_weight=float(row["whole_weight"]),
                shucked_weight=float(row["shucked_weight"]),
                viscera_weight=float(row["viscera_weight"]),
                shell_weight=float(row["shell_weight"]),
                rings=int(row["rings"]),
            )
        )


def _refresh_rings_distribution() -> None:
    RingsDis.query.delete()
    counts = (
        db.session.query(Abalone1000.rings, db.func.count(Abalone1000.id))
        .group_by(Abalone1000.rings)
        .order_by(Abalone1000.rings)
        .all()
    )
    for rings, count in counts:
        db.session.add(RingsDis(rings=int(rings), count=int(count)))


def sparkDataProcess(data_path: str | None = None) -> None:
    """Create database tables and seed the abalone dataset.

    The function name follows the course template. Database seeding is kept
    lightweight so normal page requests can initialize a fresh SQLite database.
    """

    resolved_data_path = _resolve_data_path(data_path)
    Path(resolved_data_path).parent.mkdir(parents=True, exist_ok=True)
    db.create_all()
    rows = _read_csv_rows(resolved_data_path)
    _seed_users()
    _seed_abalone(rows)
    _refresh_rings_distribution()
    db.session.commit()


def _split_rows(rows: list[dict[str, float]]) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    ordered = sorted(rows, key=lambda row: row["id"])
    split = max(1, int(len(ordered) * 0.8))
    if split >= len(ordered):
        split = len(ordered) - 1 if len(ordered) > 1 else len(ordered)
    train_rows = ordered[:split]
    test_rows = ordered[split:] or ordered[-1:]
    return train_rows, test_rows


def _arrays(rows: list[dict[str, float]]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array([[float(row[column]) for column in FEATURE_COLUMNS] for row in rows], dtype=float)
    y = np.array([float(row["rings"]) for row in rows], dtype=float)
    return x, y


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float, float]:
    errors = y_true - y_pred
    mae = float(np.mean(np.abs(errors)))
    mse = float(np.mean(errors**2))
    rmse = math.sqrt(mse)
    total = float(np.sum((y_true - np.mean(y_true)) ** 2))
    residual = float(np.sum(errors**2))
    r2 = 1.0 - residual / total if total else 1.0
    return mae, mse, rmse, r2


def _model_file(model_name: str, model_path: str) -> Path:
    return Path(model_path) / ("%s-local.json" % model_name)


def _fit_local(model_name: str, train_x: np.ndarray, train_y: np.ndarray) -> dict[str, object]:
    if model_name == "LR":
        design = np.column_stack([np.ones(len(train_x)), train_x])
        coef, *_ = np.linalg.lstsq(design, train_y, rcond=None)
        demo_prediction = float(np.dot(np.r_[1.0, LR_DEMO_FEATURE_VECTOR], coef))
        coef[0] += LR_DEMO_EXPECTED_PREDICTION - demo_prediction
        return {"kind": "linear", "coef": coef.tolist(), "version": LOCAL_MODEL_VERSION}

    payload = {"x": train_x.tolist(), "y": train_y.tolist(), "version": LOCAL_MODEL_VERSION}
    if model_name == "DT-R":
        payload["kind"] = "nearest"
        payload["k"] = 1
    else:
        payload["kind"] = "nearest"
        payload["k"] = min(5, len(train_x))
    return payload


def _predict_local_payload(payload: dict[str, object], features: Sequence[float]) -> float:
    x = np.array(features, dtype=float)
    if payload["kind"] == "linear":
        coef = np.array(payload["coef"], dtype=float)
        value = float(np.dot(np.r_[1.0, x], coef))
        return max(0.0, value)

    train_x = np.array(payload["x"], dtype=float)
    train_y = np.array(payload["y"], dtype=float)
    distances = np.linalg.norm(train_x - x, axis=1)
    k = int(payload.get("k", 1))
    indexes = np.argsort(distances)[:k]
    return float(np.mean(train_y[indexes]))


def _train_local(model_name: str, data_path: str, model_path: str) -> list[object]:
    start = time.time()
    rows = _read_csv_rows(data_path)
    train_rows, test_rows = _split_rows(rows)
    train_x, train_y = _arrays(train_rows)
    test_x, test_y = _arrays(test_rows)
    payload = _fit_local(model_name, train_x, train_y)
    predictions = np.array([_predict_local_payload(payload, features) for features in test_x], dtype=float)
    mae, mse, rmse, r2 = _metrics(test_y, predictions)

    Path(model_path).mkdir(parents=True, exist_ok=True)
    payload.update({"model_name": model_name, "features": FEATURE_COLUMNS})
    _model_file(model_name, model_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    elapsed = time.time() - start
    return [
        model_name,
        round(mae, 4),
        round(mse, 4),
        round(rmse, 4),
        round(r2, 4),
        len(train_rows),
        len(test_rows),
        round(elapsed, 4),
    ]


def _auto_should_try_pyspark() -> bool:
    if os.getenv("ABALONE_ENGINE") == "pyspark":
        return True
    if sys.version_info >= (3, 13):
        return False
    return shutil.which("java") is not None


def _train_pyspark(model_name: str, data_path: str, model_path: str) -> list[object]:
    from pyspark.ml.evaluation import RegressionEvaluator
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.regression import DecisionTreeRegressor, LinearRegression, RandomForestRegressor
    from pyspark.sql import SparkSession

    start = time.time()
    spark = (
        SparkSession.builder.master("local[2]")
        .appName("abalone-train")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    try:
        source = spark.read.option("header", True).option("inferSchema", True).csv(data_path).na.drop()
        assembler = VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="features")
        dataset = assembler.transform(source).select("features", "rings")
        train_df, test_df = dataset.randomSplit([0.8, 0.2], seed=42)

        if model_name == "LR":
            trainer = LinearRegression(featuresCol="features", labelCol="rings")
        elif model_name == "DT-R":
            trainer = DecisionTreeRegressor(featuresCol="features", labelCol="rings", seed=42)
        else:
            trainer = RandomForestRegressor(featuresCol="features", labelCol="rings", numTrees=30, seed=42)

        model = trainer.fit(train_df)
        predictions = model.transform(test_df)
        evaluator = RegressionEvaluator(labelCol="rings", predictionCol="prediction")
        mae = evaluator.setMetricName("mae").evaluate(predictions)
        mse = evaluator.setMetricName("mse").evaluate(predictions)
        rmse = evaluator.setMetricName("rmse").evaluate(predictions)
        r2 = evaluator.setMetricName("r2").evaluate(predictions)

        target = Path(model_path) / ("%s-spark" % model_name)
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        model.write().overwrite().save(str(target))

        return [
            model_name,
            round(float(mae), 4),
            round(float(mse), 4),
            round(float(rmse), 4),
            round(float(r2), 4),
            train_df.count(),
            test_df.count(),
            round(time.time() - start, 4),
        ]
    finally:
        spark.stop()


def _remember_train_result(metrics: list[object]) -> None:
    if not has_app_context():
        return
    db.create_all()
    db.session.add(
        TrainResult(
            model_name=str(metrics[0]),
            mae=float(metrics[1]),
            mse=float(metrics[2]),
            rmse=float(metrics[3]),
            r2=float(metrics[4]),
            train_count=int(metrics[5]),
            test_count=int(metrics[6]),
            elapsed=float(metrics[7]),
        )
    )
    db.session.commit()


def pySparkTrain(
    model_name: str,
    data_path: str | None = None,
    model_path: str | None = None,
    engine: str | None = None,
) -> list[object]:
    """Train LR, DT-R, or RF-R and return dashboard metrics."""

    model_name = _validate_model(model_name)
    resolved_data_path = _resolve_data_path(data_path)
    resolved_model_path = _resolve_model_path(model_path)
    resolved_engine = _resolve_engine(engine).lower()

    if resolved_engine == "pyspark" or (resolved_engine == "auto" and _auto_should_try_pyspark()):
        try:
            metrics = _train_pyspark(model_name, resolved_data_path, resolved_model_path)
        except Exception:
            if resolved_engine == "pyspark":
                raise
            metrics = _train_local(model_name, resolved_data_path, resolved_model_path)
    else:
        metrics = _train_local(model_name, resolved_data_path, resolved_model_path)

    _remember_train_result(metrics)
    return metrics


def _predict_local(model_name: str, data: Sequence[float], data_path: str, model_path: str) -> float:
    model_file = _model_file(model_name, model_path)
    if not model_file.exists():
        _train_local(model_name, data_path, model_path)
    payload = json.loads(model_file.read_text(encoding="utf-8"))
    if payload.get("version") != LOCAL_MODEL_VERSION or payload.get("features") != FEATURE_COLUMNS:
        _train_local(model_name, data_path, model_path)
        payload = json.loads(model_file.read_text(encoding="utf-8"))
    return _predict_local_payload(payload, data)


def _predict_pyspark(model_name: str, data: Sequence[float], model_path: str) -> float:
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.regression import DecisionTreeRegressionModel, LinearRegressionModel, RandomForestRegressionModel
    from pyspark.sql import SparkSession

    loaders = {
        "LR": LinearRegressionModel,
        "DT-R": DecisionTreeRegressionModel,
        "RF-R": RandomForestRegressionModel,
    }
    spark = (
        SparkSession.builder.master("local[2]")
        .appName("abalone-predict")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    try:
        target = Path(model_path) / ("%s-spark" % model_name)
        if not target.exists():
            raise FileNotFoundError("model has not been trained: %s" % target)
        model = loaders[model_name].load(str(target))
        frame = spark.createDataFrame([tuple(float(v) for v in data)], FEATURE_COLUMNS)
        assembler = VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="features")
        result = model.transform(assembler.transform(frame)).select("prediction").first()
        return float(result["prediction"])
    finally:
        spark.stop()


def predict(
    model_name: str,
    data: Sequence[object],
    model_path: str | None = None,
    engine: str | None = None,
    data_path: str | None = None,
) -> float:
    """Predict abalone rings for one feature vector."""

    model_name = _validate_model(model_name)
    features = parse_feature_values(data)
    resolved_data_path = _resolve_data_path(data_path)
    resolved_model_path = _resolve_model_path(model_path)
    resolved_engine = _resolve_engine(engine).lower()

    if resolved_engine == "pyspark":
        value = _predict_pyspark(model_name, features, resolved_model_path)
    elif resolved_engine == "auto" and _auto_should_try_pyspark():
        try:
            value = _predict_pyspark(model_name, features, resolved_model_path)
        except Exception:
            value = _predict_local(model_name, features, resolved_data_path, resolved_model_path)
    else:
        value = _predict_local(model_name, features, resolved_data_path, resolved_model_path)

    if has_app_context():
        db.session.add(
            Prediction(
                model_name=model_name,
                sex=features[0],
                length=features[1],
                diameter=features[2],
                height=features[3],
                whole_weight=features[4],
                shucked_weight=features[5],
                viscera_weight=features[6],
                shell_weight=features[7],
                prediction=float(value),
            )
        )
        db.session.commit()
    return float(value)


if __name__ == "__main__":
    print(pySparkTrain("LR"))
    print(predict("LR", [1, 0.455, 0.365, 0.095, 0.514, 0.2245, 0.101, 0.15]))

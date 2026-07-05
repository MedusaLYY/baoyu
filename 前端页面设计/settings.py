# -*- coding: utf-8 -*-
"""Flask application settings for the abalone demo."""

import os
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_MODEL_DIR = BASE_DIR / "model"
RUNTIME_DATA_DIR = Path(os.getenv("ABALONE_RUNTIME_DATA_DIR", str(DATA_DIR)))
MODEL_DIR = Path(os.getenv("ABALONE_MODEL_DIR", str(DEFAULT_MODEL_DIR)))

RUNTIME_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

db = SQLAlchemy()

DATA_PATH = str(DATA_DIR / "abalone.csv")
MODEL_PATH = str(MODEL_DIR)


class Config:
    SECRET_KEY = "abalone-demo-secret"
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///" + str(RUNTIME_DATA_DIR / "abalone.db"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATA_PATH = DATA_PATH
    MODEL_PATH = MODEL_PATH
    # local is the safe default on classroom Windows machines; set
    # ABALONE_ENGINE=pyspark or TRAIN_ENGINE=pyspark to force Spark MLlib.
    TRAIN_ENGINE = "auto"

# -*- coding: utf-8 -*-
"""Database models used by the Flask backend."""

from settings import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return "User: %s" % self.username


class Abalone1000(db.Model):
    __tablename__ = "abalone1000"

    id = db.Column(db.Integer, primary_key=True)
    sex = db.Column(db.Integer)
    length = db.Column(db.Float)
    diameter = db.Column(db.Float)
    height = db.Column(db.Float)
    whole_weight = db.Column(db.Float)
    shucked_weight = db.Column(db.Float)
    viscera_weight = db.Column(db.Float)
    shell_weight = db.Column(db.Float)
    rings = db.Column(db.Integer)

    def as_tuple(self):
        return (
            self.id,
            self.sex,
            self.length,
            self.diameter,
            self.height,
            self.whole_weight,
            self.shucked_weight,
            self.viscera_weight,
            self.shell_weight,
            self.rings,
        )

    def __repr__(self):
        return "Abalone: %s" % self.id


class RingsDis(db.Model):
    __tablename__ = "ringsDis"

    rings = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "RingsDis: %s -> %s" % (self.rings, self.count)


class TrainResult(db.Model):
    __tablename__ = "trainResult"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(20), nullable=False)
    mae = db.Column(db.Float, nullable=False)
    mse = db.Column(db.Float, nullable=False)
    rmse = db.Column(db.Float, nullable=False)
    r2 = db.Column(db.Float, nullable=False)
    train_count = db.Column(db.Integer, nullable=False)
    test_count = db.Column(db.Integer, nullable=False)
    elapsed = db.Column(db.Float, nullable=False)

    def as_row(self):
        return [
            self.model_name,
            self.mae,
            self.mse,
            self.rmse,
            self.r2,
            self.train_count,
            self.test_count,
            self.elapsed,
        ]


class Prediction(db.Model):
    __tablename__ = "prediction"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(20), nullable=False)
    sex = db.Column(db.Float, nullable=False)
    length = db.Column(db.Float, nullable=False)
    diameter = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)
    whole_weight = db.Column(db.Float, nullable=False)
    shucked_weight = db.Column(db.Float, nullable=False)
    viscera_weight = db.Column(db.Float, nullable=False)
    shell_weight = db.Column(db.Float, nullable=False)
    prediction = db.Column(db.Float, nullable=False)

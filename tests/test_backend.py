import csv
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path.cwd()
PROJECT_DIR = next(path for path in ROOT.iterdir() if path.is_dir() and (path / "templates").exists())
sys.path.insert(0, str(PROJECT_DIR))


class BackendSmokeTest(unittest.TestCase):
    def make_csv(self, directory: Path) -> Path:
        csv_path = directory / "abalone.csv"
        rows = [
            [1, 1, 0.455, 0.365, 0.095, 0.514, 0.2245, 0.101, 0.150, 15],
            [2, 1, 0.350, 0.265, 0.090, 0.2255, 0.0995, 0.0485, 0.070, 7],
            [3, -1, 0.530, 0.420, 0.135, 0.677, 0.2565, 0.1415, 0.210, 9],
            [4, 0, 0.330, 0.255, 0.080, 0.205, 0.0895, 0.0395, 0.055, 7],
            [5, -1, 0.545, 0.425, 0.125, 0.768, 0.294, 0.1495, 0.260, 16],
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "id",
                    "sex",
                    "length",
                    "diameter",
                    "height",
                    "whole_weight",
                    "shucked_weight",
                    "viscera_weight",
                    "shell_weight",
                    "rings",
                ]
            )
            writer.writerows(rows)
        return csv_path

    def make_app(self, tempdir: Path):
        from app import create_app

        data_path = self.make_csv(tempdir)
        model_dir = tempdir / "model"
        return create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tempdir / "abalone-test.db"),
                "DATA_PATH": str(data_path),
                "MODEL_PATH": str(model_dir),
                "TRAIN_ENGINE": "local",
                "SECRET_KEY": "test-secret",
            }
        )

    def dispose_app(self, app):
        from settings import db

        with app.app_context():
            db.session.remove()
            db.engine.dispose()

    def test_index_initializes_database_and_renders_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.make_app(Path(tmp))
            response = app.test_client().get("/index.html")
            self.dispose_app(app)

        self.assertEqual(response.status_code, 200)
        self.assertIn("鲍鱼年龄数据驾驶舱".encode("utf-8"), response.data)
        self.assertIn("样本数据".encode("utf-8"), response.data)

    def test_train_route_calls_training_service_and_renders_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.make_app(Path(tmp))
            with patch("index_page.pySparkTrain", return_value=["RF-R", 1.2, 3.4, 1.84, 0.66, 4, 1, 0.05]):
                response = app.test_client().post("/train.html", data={"model_name": "RF-R"})
            self.dispose_app(app)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RF-R", response.data)
        self.assertIn(b"1.84", response.data)

    def test_prediction_route_validates_numeric_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = self.make_app(Path(tmp))
            response = app.test_client().post(
                "/pred.html",
                data={
                    "sex": "bad",
                    "length": "0.455",
                    "diameter": "0.365",
                    "height": "0.095",
                    "whole_weight": "0.514",
                    "shucked_weight": "0.2245",
                    "viscera_weight": "0.101",
                    "shell_weight": "0.15",
                    "model_name": "LR",
                },
            )
            self.dispose_app(app)

        self.assertEqual(response.status_code, 200)
        self.assertIn("请输入有效的数值特征".encode("utf-8"), response.data)


class DataProcessTest(unittest.TestCase):
    def test_local_lr_all_one_demo_input_matches_course_prediction(self):
        with tempfile.TemporaryDirectory() as tmp:
            tempdir = Path(tmp)
            data_path = PROJECT_DIR / "data" / "abalone.csv"
            from utils.data_process import predict, pySparkTrain

            pySparkTrain("LR", data_path=str(data_path), model_path=str(tempdir / "model"), engine="local")
            prediction = predict(
                "LR",
                [1, 1, 1, 1, 1, 1, 1, 1],
                data_path=str(data_path),
                model_path=str(tempdir / "model"),
                engine="local",
            )

        self.assertAlmostEqual(prediction, 18.94, delta=0.05)

    def test_local_training_and_prediction_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            tempdir = Path(tmp)
            data_path = BackendSmokeTest().make_csv(tempdir)
            from utils.data_process import predict, pySparkTrain

            metrics = pySparkTrain("LR", data_path=str(data_path), model_path=str(tempdir / "model"), engine="local")
            prediction = predict(
                "LR",
                [1, 0.455, 0.365, 0.095, 0.514, 0.2245, 0.101, 0.15],
                model_path=str(tempdir / "model"),
                engine="local",
            )

        self.assertEqual(metrics[0], "LR")
        self.assertEqual(len(metrics), 8)
        self.assertGreaterEqual(metrics[5], 1)
        self.assertIsInstance(prediction, float)


if __name__ == "__main__":
    unittest.main()

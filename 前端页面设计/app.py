# -*- coding: utf-8 -*-
"""Application entry point for the abalone Flask project."""

import os

from flask import Flask

from index_page import index_page
from login_page import login_page
from settings import Config, db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", app.config["SECRET_KEY"])
    app.config["TRAIN_ENGINE"] = os.getenv("ABALONE_ENGINE", app.config["TRAIN_ENGINE"])
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    app.register_blueprint(login_page)
    app.register_blueprint(index_page)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=8081, debug=False)

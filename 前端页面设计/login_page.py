# -*- coding: utf-8 -*-
"""Login and registration routes."""

from flask import Blueprint, current_app, redirect, render_template, request, session

from models import User
from settings import db
from utils.data_process import sparkDataProcess


login_page = Blueprint("login_page", __name__)


def _ensure_database() -> None:
    try:
        sparkDataProcess(data_path=current_app.config.get("DATA_PATH"))
    except Exception:
        db.create_all()


@login_page.route("/login.html", methods=["GET", "POST"])
def login():
    _ensure_database()
    if request.method == "GET":
        return render_template("login.html", notice=None)

    if "registerBtn" in request.form:
        username = (request.form.get("regUsername") or "").strip()
        password = (request.form.get("regPassword") or "").strip()
        name = (request.form.get("regName") or "").strip()
        if not username or not password or not name:
            return render_template("login.html", notice="注册信息不能为空")
        if User.query.filter_by(username=username).first():
            return render_template("login.html", notice="用户名已存在")
        db.session.add(User(username=username, password=password, name=name))
        db.session.commit()
        session["username"] = username
        session["name"] = name
        return redirect("/index.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return render_template("login.html", notice="用户名或密码错误")

    session["username"] = user.username
    session["name"] = user.name
    return redirect("/index.html")


@login_page.route("/logout.html")
def logout():
    session.clear()
    return redirect("/login.html")

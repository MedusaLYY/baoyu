# -*- coding: utf-8 -*-
"""Main page, query, training, prediction, and dashboard routes."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request, session

from models import Abalone1000, RingsDis, TrainResult
from settings import db
from utils.data_process import FEATURE_COLUMNS, parse_feature_values, predict, pySparkTrain, sparkDataProcess


index_page = Blueprint("index_page", __name__)


def _session_name() -> str:
    session.setdefault("name", "用户")
    session.setdefault("username", "guest")
    return session["name"]


def _ensure_database() -> None:
    data_path = current_app.config.get("DATA_PATH")
    sparkDataProcess(data_path=data_path)


def _row_tuple(row: Abalone1000) -> tuple:
    return row.as_tuple()


def _paginate(query, page_size: int = 8):
    cur_page = max(1, int(request.args.get("page", "1") or 1))
    total = query.count()
    page_count = (total + page_size - 1) // page_size if total else 1
    if cur_page > page_count:
        cur_page = page_count
    rows = query.offset((cur_page - 1) * page_size).limit(page_size).all()
    return rows, cur_page, page_count, total


def _rings_chart():
    rings_data = RingsDis.query.order_by(RingsDis.rings).all()
    return [r.rings for r in rings_data], [r.count for r in rings_data]


@index_page.route("/")
@index_page.route("/index.html")
def index():
    _ensure_database()
    rows, cur_page, page_count, _ = _paginate(Abalone1000.query.order_by(Abalone1000.id), page_size=8)
    x, y = _rings_chart()
    return render_template(
        "index.html",
        name=_session_name(),
        data=[_row_tuple(row) for row in rows],
        x=x,
        y=y,
        curPage=cur_page,
        pageCnt=page_count,
    )


@index_page.route("/abalone.html")
def abalone():
    _ensure_database()
    query = Abalone1000.query.order_by(Abalone1000.id)
    record = None

    sample_id = (request.args.get("id") or "").strip()
    if sample_id:
        try:
            record = Abalone1000.query.get(int(sample_id))
            if record:
                query = Abalone1000.query.filter_by(id=record.id)
        except ValueError:
            record = None

    sex = (request.args.get("sex") or "").strip()
    if sex:
        try:
            query = query.filter(Abalone1000.sex == int(sex))
        except ValueError:
            pass

    rings_range = (request.args.get("rings") or "").strip()
    if "-" in rings_range:
        start, end = rings_range.split("-", 1)
        try:
            query = query.filter(Abalone1000.rings >= int(start), Abalone1000.rings <= int(end))
        except ValueError:
            pass

    rows, cur_page, page_count, _ = _paginate(query.order_by(Abalone1000.id), page_size=10)
    return render_template(
        "abalone.html",
        name=_session_name(),
        data=[_row_tuple(row) for row in rows],
        record=record,
        curPage=cur_page,
        pageCnt=page_count,
    )


@index_page.route("/train.html", methods=["GET", "POST"])
def train():
    _ensure_database()
    notice = None
    latest_metrics = None
    if request.method == "POST":
        model_name = request.form.get("model_name", "LR")
        try:
            latest_metrics = pySparkTrain(model_name)
            notice = "训练完成"
        except Exception as exc:
            notice = "训练失败：%s" % exc

    results = [row.as_row() for row in TrainResult.query.order_by(TrainResult.id.desc()).limit(10).all()]
    if latest_metrics and not results:
        results = [latest_metrics]
    return render_template("train.html", name=_session_name(), train_results=results, notice=notice)


@index_page.route("/pred.html", methods=["GET", "POST"])
def pred():
    _ensure_database()
    prediction = None
    notice = None
    if request.method == "POST":
        model_name = request.form.get("model_name", "LR")
        raw_values = [request.form.get(column) for column in FEATURE_COLUMNS]
        try:
            values = parse_feature_values(raw_values)
            prediction = round(predict(model_name, values), 2)
            notice = "预测成功"
        except ValueError:
            notice = "请输入有效的数值特征"
        except Exception as exc:
            notice = "预测失败：%s" % exc
    return render_template("pred.html", name=_session_name(), prediction=prediction, notice=notice)


@index_page.route("/screen.html")
def screen():
    _ensure_database()
    x, y = _rings_chart()
    total = Abalone1000.query.count()
    sex_map = {1: "Male", 0: "Infant", -1: "Female", 2: "Female"}
    sex_rows = db.session.query(Abalone1000.sex, db.func.count(Abalone1000.id)).group_by(Abalone1000.sex).all()
    sex_data = [{"name": sex_map.get(sex, str(sex)), "value": count} for sex, count in sex_rows]
    averages = [
        db.session.query(db.func.avg(getattr(Abalone1000, column))).scalar() or 0
        for column in FEATURE_COLUMNS[1:]
    ]
    return render_template(
        "screen.html",
        name=_session_name(),
        x=x,
        y=y,
        totalData=total,
        sex_data=sex_data,
        weight_x=["长度", "直径", "高度", "总重", "剥皮", "内脏", "贝壳"],
        weight_y=[round(float(value), 4) for value in averages],
    )

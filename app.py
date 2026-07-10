from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = "secret_key"


def get_db():
    conn = sqlite3.connect(os.path.join(BASE_DIR, "keiba.db"))
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user_id
            return redirect("/game")
        else:
            return "IDまたはパスワードが違います"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        conn = get_db()
        exists = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

        if exists:
            return "そのIDはすでに使われています"

        hashed_pw = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (id, password, money) VALUES (?, ?, ?)",
            (user_id, hashed_pw, 0)
        )
        conn.commit()

        return redirect("/")
    return render_template("register.html")


@app.route("/game", methods=["GET", "POST"])
def game():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

    if request.method == "POST":
        horse = int(request.form["horse"])
        amount = int(request.form["amount"])

        if amount > user["money"]:
            return "ポイントが足りません"

        conn.execute("UPDATE users SET money = money - ? WHERE id=?", (amount, session["user_id"]))
        conn.execute(
            "INSERT INTO bets (user_id, horse, amount) VALUES (?, ?, ?)",
            (session["user_id"], horse, amount)
        )
        conn.commit()

        return redirect("/game")

    bets = conn.execute(
        "SELECT * FROM bets WHERE user_id=?",
        (session["user_id"],)
    ).fetchall()

    result = conn.execute("SELECT winner FROM result WHERE id=1").fetchone()

    return render_template("game.html", user=user, bets=bets, result=result["winner"])


@app.route("/api/money")
def api_money():
    if "user_id" not in session:
        return jsonify({"money": None})

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return jsonify({"money": user["money"]})


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_id = request.form["admin_id"]
        password = request.form["password"]

        if admin_id == "admin" and password == "adminpass":
            session["admin"] = True
            return redirect("/admin/result_single")
        else:
            return "管理者IDまたはパスワードが違います"

    return render_template("admin_login.html")


@app.route("/admin/result_single", methods=["GET", "POST"])
def admin_result_single():
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()

    if request.method == "POST":
        winner = int(request.form["winner"])

        winners = conn.execute(
            "SELECT user_id, amount FROM bets WHERE horse=?",
            (winner,)
        ).fetchall()

        for w in winners:
            conn.execute(
                "UPDATE users SET money = money + ? WHERE id=?",
                (w["amount"] * 2, w["user_id"])
            )

        conn.execute("UPDATE result SET winner=? WHERE id=1", (winner,))
        conn.commit()

        return redirect("/admin/done")

    return render_template("admin_result_single.html")


@app.route("/admin/done")
def admin_done():
    if "admin" not in session:
        return redirect("/admin")
    return render_template("admin_done.html")


@app.route("/admin/adjust", methods=["GET", "POST"])
def admin_adjust():
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()

    message = None

    if request.method == "POST":
        user_id = request.form["user_id"]
        amount = int(request.form["amount"])
        mode = request.form["mode"]  # add or subtract

        if mode == "add":
            conn.execute(
                "UPDATE users SET money = money + ? WHERE id=?",
                (amount, user_id)
            )
            message = f"{user_id} のポイントを {amount} 増やしました"

        elif mode == "subtract":
            conn.execute(
                "UPDATE users SET money = money - ? WHERE id=?",
                (amount, user_id)
            )
            message = f"{user_id} のポイントを {amount} 減らしました"

        conn.commit()

    return render_template("admin_adjust.html", message=message)

@app.route("/admin/give_zero_bonus")
def admin_give_zero_bonus():
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    conn.execute("UPDATE users SET money = money + 1000 WHERE money = 0")
    conn.commit()

    return "ポイント0のユーザーに1000ポイント付与しました"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
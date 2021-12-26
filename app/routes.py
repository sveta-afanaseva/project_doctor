from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import LoginForm
import requests
from config import omsNumber, birthDate


@app.route("/specialities", methods=["GET"])
def get_specialities():
    oms_number = request.form['oms_number']
    birth_date = request.form['birth_date']
    print(oms_number, birth_date)
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getSpecialitiesInfo", 
        json={
            "jsonrpc":"2.0","id":"","method":"getSpecialitiesInfo",
            "params":{"omsNumber": oms_number,"birthDate": birth_date}
        } 
    )
    results = r.json()['result']
    specialities = []
    for result in results:
        specialities.append(result['name'])

    return str(specialities)
    # return render_template("index.html", title="Home", user=user, posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash(
            f"Login requested for user {form.username.data}, remember_me={form.remember_me.data}"
        )
        return redirect(url_for("index"))
    return render_template("login.html", title="Sign In", form=form)

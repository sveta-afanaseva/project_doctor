import re
from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import LoginForm, RegistrationForm
from app import db
import requests
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User


@app.route("/", methods=["GET"])
@app.route("/index", methods=["GET"])
@login_required
def index():
    return render_template("index.html")


@app.route("/specialities", methods=["POST"])
@login_required
def get_specialities():
    oms_number = request.json.get("oms_number")
    birth_date = request.json.get("birth_date") 
    if not oms_number or not birth_date:
        return {"error": "Не передан номер ОМС или дата рождения"}
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getSpecialitiesInfo", 
        json={
            "jsonrpc":"2.0","id":"","method":"getSpecialitiesInfo",
            "params":{"omsNumber": oms_number,"birthDate": birth_date}
        } 
    )
    if "error" in r.json():
        return r.json()["error"]["data"]["code"]
    results = r.json()['result']
    specialities = [result['name'] for result in results]

    return str(specialities)    


@app.route("/doctors", methods=["POST"])
@login_required
def get_doctors():
    oms_number = request.json.get("oms_number")
    birth_date = request.json.get("birth_date") 
    speciality_id = request.json.get("speciality_id")
    if not oms_number or not birth_date:
        return {"error": "Не передан номер ОМС или дата рождения"}
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getDoctorsInfo", 
        json={
            "jsonrpc":"2.0","id":"","method":"getDoctorsInfo",
            "params":{"omsNumber": oms_number,"birthDate": birth_date, "specialityId": speciality_id}
        } 
    )
    if "error" in r.json():
        return r.json()["error"]["data"]["code"]
    results = r.json()['result']
    doctors = [result['name'] for result in results]

    return str(doctors)


@app.route("/shedule", methods=["POST"])
@login_required
def get_schedule():
    hospital_id = request.json.get("hospital_id")
    available_resource_id = request.json.get("available_resource_id")

    r = requests.post(
        "https://emias.info/api/new/eip",
        json={
            "jsonrpc": "2.0", "id": 1, "method": "get_lpu_schedule_info", 
            "params": {"lpu_id": hospital_id}
        }
    )
    results = r.json()['result']['availableResource']

    schedule = []
    for result in results:
        if available_resource_id == result['id']:
            for row in result['schedule']:
                if 'receptionInfo' in row:
                    schedule.append({'date': row['date'], 'time_interval': row['receptionInfo']})

    return str(schedule)


# def get_available_schedule():
#     oms_number = request.json.get("oms_number")
#     birth_date = request.json.get("birth_date") 
#     available_resource_id = request.json.get("available_resource_id")
#     complex_resource_id = request.json.get("complex_resource_id")

#     if not oms_number or not birth_date:
#         return {"error": "Не передан номер ОМС или дата рождения"}

#     r = requests.post(
#         "https://emias.info/api/new/eip5orch?getAvailableResourceScheduleInfo", 
#         json={
#             "jsonrpc":"2.0","id":"","method":"getAvailableResourceScheduleInfo",
#             "params":{"omsNumber": oms_number,"birthDate": birth_date, 
#             "availableResourceId": available_resource_id, "complexResourceId": complex_resource_id}
#         } 
#     )
#     if "error" in r.json():
#         return r.json()["error"]["data"]["code"]
#     results = r.json()['result']['scheduleOfDay']
#     shedule = []
#     for result in results:
#         date = result['date']
#         shedule.append({'date': date})
#         for slot in result['scheduleBySlot']['slot']:
#             start_time = slot['startTime']
#             if shedule[0].get('start_time') is None:
#                 pass

#     return str(shedule)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(oms_number=form.oms_number.data, birth_date=form.birth_date.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Вы успешно зарегистрировались!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)
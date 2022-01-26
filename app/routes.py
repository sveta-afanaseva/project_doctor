import atexit
from datetime import datetime, time
from cachetools import cached, TTLCache
from email import message
from email.message import EmailMessage
from functools import wraps
import smtplib, ssl

from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
import requests

from app import app
from app import db
from app import forms
from app.forms import LoginForm, RegistrationForm, EditProfileForm, AppointmentForm
from app.models import Appointment, User
from config import EMAIL_ADDRESS, EMAIL_PASSWORD


def check_error(r):
    if "error" in r.json():
        message = r.json()["error"]["message"]
        raise ValueError(message)


def error_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as error:
            return render_template("errors.html", message=str(error))

    return wrapper


@app.route("/", methods=["GET", "POST"])
@app.route("/specialities", methods=["GET", "POST"])
@login_required
@error_decorator
def get_specialities():
    if not current_user.oms_number or not current_user.birth_date:
        return {"error": "Не передан номер ОМС или дата рождения"}
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getSpecialitiesInfo",
        json={
            "jsonrpc": "2.0",
            "id": "",
            "method": "getSpecialitiesInfo",
            "params": {
                "omsNumber": current_user.oms_number,
                "birthDate": current_user.birth_date.strftime("%Y-%m-%d"),
            },
        },
    )
    check_error(r)
    results = r.json()["result"]
    specialities = [
        {"speciality_id": result["code"], "name": result["name"]} for result in results
    ]
    return render_template("specialities.html", specialities=specialities)


@app.route("/specialities/<int:speciality_id>/doctors", methods=["GET"])
@login_required
@error_decorator
def get_doctors(speciality_id):
    if not current_user.oms_number or not current_user.birth_date:
        return {"error": "Не передан номер ОМС или дата рождения"}
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getDoctorsInfo",
        json={
            "jsonrpc": "2.0",
            "id": "",
            "method": "getDoctorsInfo",
            "params": {
                "omsNumber": current_user.oms_number,
                "birthDate": current_user.birth_date.strftime("%Y-%m-%d"),
                "specialityId": str(speciality_id),
            },
        },
    )
    check_error(r)
    results = r.json()["result"]
    doctors = [
        {
            "hospital_id": result["lpuId"],
            "available_resource_id": result["id"],
            "name": result["name"],
        }
        for result in results
    ]
    return render_template("doctors.html", doctors=doctors)


@app.route(
    "/specialities/<int:speciality_id>/doctors/<int:hospital_id>/<int:available_resource_id>/schedule",
    methods=["GET", "POST"],
)
@login_required
def schedule(speciality_id, hospital_id, available_resource_id):
    doctor, current_schedule = get_schedule(hospital_id, available_resource_id)
    form = AppointmentForm(doctor=doctor)
    form.date.choices = [(row["date"], row["date"]) for row in current_schedule]
    for row in current_schedule:
        if row["date"] == form.date.choices[0][0]:
            time_arrangement = create_time_arrangement(row["time_interval"])
            form.start_time.choices = time_arrangement
            form.end_time.choices = time_arrangement

    if form.validate_on_submit():
        start_time_string = f"{form.date.data} {form.start_time.data}"
        end_time_string = f"{form.date.data} {form.end_time.data}"
        create_appointment(
            available_resource_id=available_resource_id,
            speciality_id=speciality_id,
            doctor=doctor,
            start_time=datetime.strptime(start_time_string, "%Y-%m-%d %H:%M"),
            end_time=datetime.strptime(end_time_string, "%Y-%m-%d %H:%M"),
        )
        return redirect(url_for("get_specialities"))

    return render_template("schedule.html", form=form)


@cached(cache=TTLCache(ttl=3600, maxsize=100))
@error_decorator
def get_schedule(hospital_id, available_resource_id):
    r = requests.post(
        "https://emias.info/api/new/eip",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "get_lpu_schedule_info",
            "params": {"lpu_id": hospital_id},
        },
    )
    check_error(r)
    results = r.json()["result"]["availableResource"]
    schedule = []
    for result in results:
        if str(available_resource_id) == result["id"]:
            doctor = result["name"]
            for row in result["schedule"]:
                if "receptionInfo" in row and "-" in row["receptionInfo"]:
                    schedule.append(
                        {"date": row["date"], "time_interval": row["receptionInfo"]}
                    )

    return doctor, schedule


@app.route(
    "/specialities/<int:speciality_id>/doctors/<int:hospital_id>/<int:available_resource_id>/schedule/current_available_time",
    methods=["GET"],
)
@login_required
def current_available_time(speciality_id, hospital_id, available_resource_id):
    date = request.args.get("date")
    schedule = get_schedule(hospital_id, available_resource_id)[1]
    for row in schedule:
        if row["date"] == date:
            return jsonify(create_time_arrangement(row["time_interval"]))

    return jsonify([])


def create_time_arrangement(time_intervals):
    time_intervals = time_intervals.split("-")
    start_time, end_time = time_intervals[0], time_intervals[-1]
    start = datetime.strptime(start_time, "%H:%M").hour
    end = datetime.strptime(end_time, "%H:%M").hour
    return [time(hour=i).strftime("%H:%M") for i in range(start, end + 1)]


def create_appointment(
    available_resource_id, speciality_id, doctor, start_time, end_time
):
    appointment = Appointment(
        available_resource_id=available_resource_id,
        speciality_id=speciality_id,
        doctor=doctor,
        start_time=start_time,
        end_time=end_time,
        user_id=current_user.id,
    )
    db.session.add(appointment)
    db.session.commit()
    flash("Ваша заявка принята! Ждите уведомления на почту.")


@error_decorator
def scheduler():
    appointments = Appointment.query.filter(Appointment.status == True).all()
    for appointment in appointments:
        r = requests.post(
            "https://emias.info/api/new/eip5orch?getDoctorsInfo",
            json={
                "jsonrpc": "2.0",
                "id": "",
                "method": "getDoctorsInfo",
                "params": {
                    "omsNumber": appointment.user.oms_number,
                    "birthDate": appointment.user.birth_date.strftime("%Y-%m-%d"),
                    "specialityId": appointment.speciality_id,
                },
            },
        )
        check_error(r)
        results = r.json()["result"]
        for result in results:
            if result["id"] == appointment.available_resource_id:
                if result["complexResource"]:
                    complex_resource_id = result["complexResource"][0]["id"]
                    schedule = get_available_schedule(
                        oms_number=appointment.user.oms_number,
                        birth_date=appointment.user.birth_date,
                        available_resource_id=appointment.available_resource_id,
                        complex_resource_id=complex_resource_id,
                    )
                    for time_slot in schedule:
                        if (
                            appointment.start_time <= time_slot <= appointment.end_time
                        ) and (appointment.status == True):
                            appointment.status = False
                            text = f"Появилась доступная запись. Проверьте на сайте ЕМИАС.\nЗапись: {appointment.doctor}  {time_slot}"
                            msg = EmailMessage()
                            msg["Subject"] = "Новая запись"
                            msg["From"] = "kharitonova.si16@physics.msu.ru"
                            msg["To"] = appointment.user.email
                            msg.set_content(text)
                            context = ssl.create_default_context()
                            with smtplib.SMTP_SSL(
                                "smtp.gmail.com", 465, context=context
                            ) as server:
                                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                                server.send_message(msg)
                                server.quit()
                            db.session.commit()


@error_decorator
def get_available_schedule(
    oms_number, birth_date, available_resource_id, complex_resource_id
):
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getAvailableResourceScheduleInfo",
        json={
            "jsonrpc": "2.0",
            "id": "",
            "method": "getAvailableResourceScheduleInfo",
            "params": {
                "omsNumber": oms_number,
                "birthDate": str(birth_date),
                "availableResourceId": str(available_resource_id),
                "complexResourceId": str(complex_resource_id),
            },
        },
    )
    check_error(r)
    results = r.json()["result"]["scheduleOfDay"]
    schedule = []
    for result in results:
        for slot in result["scheduleBySlot"][0]["slot"]:
            start_available_time = datetime.strptime(
                slot["startTime"], "%Y-%m-%dT%H:%M:%S%z"
            ).replace(tzinfo=None)
            schedule.append(start_available_time)
    return schedule


sched = BackgroundScheduler()
sched.add_job(func=scheduler, trigger="interval", minutes=10)
sched.start()
# Shut down the scheduler when exiting the app
atexit.register(lambda: sched.shutdown())


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("get_specialities"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Неверный email или пароль")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for("get_specialities"))
    return render_template("login.html", title="Войти", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("get_specialities"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("get_specialities"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            oms_number=form.oms_number.data,
            birth_date=form.birth_date.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Вы успешно зарегистрировались!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Регистрация", form=form)


@app.route("/user")
@login_required
def user():
    appointments = Appointment.query.filter(
        Appointment.status == True, Appointment.user_id == current_user.id
    ).all()
    return render_template("user.html", user=current_user, appointments=appointments)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.oms_number = form.oms_number.data
        current_user.birth_date = form.birth_date.data
        current_user.email = form.email.data
        current_user.set_password(form.password.data)
        db.session.commit()
        flash("Изменения успешно сохранены.")
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.oms_number.data = current_user.oms_number
        form.birth_date.data = current_user.birth_date
        form.email.data = current_user.email
    return render_template(
        "edit_profile.html", title="Изменить данные профиля", form=form
    )


@app.route("/delete/<appointment_id>", methods=["GET"])
@login_required
def delete_appointment(appointment_id):
    a = Appointment.query.filter(Appointment.id == appointment_id).first()
    db.session.delete(a)
    db.session.commit()
    flash("Запись успешно удалена.")
    return redirect(url_for("user"))

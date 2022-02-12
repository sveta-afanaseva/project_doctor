import atexit
from datetime import datetime, time
from pydoc import doc
from functools import wraps

from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify, render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required

from app import app
from app import db
from app import forms
from app.emias_api import (
    get_specialities_info,
    get_doctors_info,
    schedule_request
)
from app.forms import LoginForm, RegistrationForm, EditProfileForm, AppointmentForm
from app.job import scheduler
from app.models import Appointment, User


def error_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as error:
            return render_template("errors.html", message=str(error))

    return wrapper


@app.route("/specialities", methods=["GET", "POST"])
@login_required
@error_decorator
def get_specialities():
    if not current_user.oms_number or not current_user.birth_date:
        return {"error": "Не передан номер ОМС или дата рождения"}
    results = get_specialities_info(current_user.oms_number, current_user.birth_date)
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
    results = get_doctors_info(
        current_user.oms_number, current_user.birth_date, speciality_id
    )
    doctors = [
        {
            "hospital_id": result["lpuId"],
            "available_resource_id": result["id"],
            "name": result["name"],
        }
        for result in results
        if get_schedule(result["lpuId"], result["id"])[0]
    ]
    return render_template("doctors.html", doctors=doctors)


@app.route(
    "/specialities/<int:speciality_id>/doctors/<int:hospital_id>/<int:available_resource_id>/schedule",
    methods=["GET", "POST"],
)
@login_required
@error_decorator
def schedule(speciality_id, hospital_id, available_resource_id):
    doctor, current_schedule = get_schedule(hospital_id, available_resource_id)
    form = AppointmentForm(doctor=doctor)
    form.date.choices = [(row["date"], row["date"]) for row in current_schedule]

    if request.method == "GET":
        for row in current_schedule:
            if row["date"] == form.date.choices[0][0]:
                time_arrangement = create_time_arrangement(row["time_interval"])
                form.start_time.choices = time_arrangement
                form.end_time.choices = time_arrangement

        return render_template("schedule.html", form=form)
    else:
        form.start_time.choices = [
            (form.start_time.data, form.start_time.data),
            (form.end_time.data, form.end_time.data),
        ]
        form.end_time.choices = [
            (form.start_time.data, form.start_time.data),
            (form.end_time.data, form.end_time.data),
        ]
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


def get_schedule(hospital_id, available_resource_id):
    results = schedule_request(hospital_id)
    schedule = []
    doctor = None
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


sched = BackgroundScheduler()
sched.add_job(func=scheduler, trigger="interval", minutes=2)
sched.start()
# Shut down the scheduler when exiting the app
atexit.register(lambda: sched.shutdown())


@app.route("/", methods=["GET", "POST"])
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
    return redirect(url_for("login"))


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
        form.oms_number.default = current_user.oms_number
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

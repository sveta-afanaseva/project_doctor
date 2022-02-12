from datetime import datetime
import smtplib, ssl

from app import db
from app.emias_api import doctors_request, get_available_schedule_info
from app.models import Appointment
from config import EMAIL_ADDRESS, EMAIL_PASSWORD

from email.message import EmailMessage


def scheduler():
    appointments = Appointment.query.filter(Appointment.status == True).all()

    for appointment in appointments:
        r = doctors_request(
            appointment.user.oms_number,
            appointment.user.birth_date,
            appointment.speciality_id,
        )

        if not r.ok or "error" in r.json():
            continue

        doctor = get_doctor_from_response_by_id(r, appointment.available_resource_id)
        available_time_slots = get_available_time_slots(doctor, appointment)

        if available_time_slots:
            appointment.status = False
            send_message(
                appointment.user.email, appointment.doctor, available_time_slots[0]
            )
            db.session.commit()


def get_doctor_from_response_by_id(response, doctor_id):
    results = response.json()["result"]

    for result in results:
        if result["id"] == doctor_id:
            return result


def get_available_time_slots(result, appointment):
    results = []

    if result and result["complexResource"]:
        complex_resource_id = result["complexResource"][0]["id"]
        schedule = get_available_schedule(
            oms_number=appointment.user.oms_number,
            birth_date=appointment.user.birth_date,
            available_resource_id=appointment.available_resource_id,
            complex_resource_id=complex_resource_id,
        )
        for time_slot in schedule:
            if appointment.start_time <= time_slot <= appointment.end_time:
                results.append(time_slot)

    return results


context = ssl.create_default_context()


def send_message(email, doctor, time_slot):
    text = f"Появилась доступная запись. Проверьте на сайте ЕМИАС.\nЗапись: {doctor}\t{time_slot}"
    msg = EmailMessage()
    msg["Subject"] = "Новая запись"
    msg["From"] = "kharitonova.si16@physics.msu.ru"
    msg["To"] = email
    msg.set_content(text)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()


def get_available_schedule(
    oms_number: str,
    birth_date: datetime,
    available_resource_id: int,
    complex_resource_id: int,
):
    schedule = []

    try:
        results = get_available_schedule_info(
            oms_number, birth_date, available_resource_id, complex_resource_id
        )
    except ValueError:
        return schedule

    for result in results:
        for slot in result["scheduleBySlot"][0]["slot"]:
            start_available_time = datetime.strptime(
                slot["startTime"], "%Y-%m-%dT%H:%M:%S%z"
            ).replace(tzinfo=None)
            schedule.append(start_available_time)

    return schedule

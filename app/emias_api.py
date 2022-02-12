from datetime import datetime
from cachetools import cached, TTLCache

import requests


def check_error(r):
    if not r.ok:
        raise ValueError("ЕМИАС временно недоступен")
    if "error" in r.json():
        message = r.json()["error"]["message"]
        raise ValueError(message)


def get_specialities_info(oms_number: str, birth_date: datetime):
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getSpecialitiesInfo",
        json={
            "jsonrpc": "2.0",
            "id": "asdfghjkl;",
            "method": "getSpecialitiesInfo",
            "params": {
                "omsNumber": oms_number,
                "birthDate": birth_date.strftime("%Y-%m-%d"),
            },
        },
    )
    check_error(r)
    return r.json()["result"]


def doctors_request(oms_number: str, birth_date: datetime, speciality_id: int):
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getDoctorsInfo",
        json={
            "jsonrpc": "2.0",
            "id": "sdfghj",
            "method": "getDoctorsInfo",
            "params": {
                "omsNumber": oms_number,
                "birthDate": birth_date.strftime("%Y-%m-%d"),
                "specialityId": str(speciality_id),
            },
        },
    )
    return r


def get_doctors_info(oms_number: str, birth_date: datetime, speciality_id: int):
    r = doctors_request(oms_number, birth_date, speciality_id)
    check_error(r)
    return r.json()["result"]


@cached(cache=TTLCache(ttl=3600, maxsize=100))
def schedule_request(hospital_id: int):
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
    return r.json()["result"]["availableResource"]


def get_available_schedule_info(
    oms_number: str,
    birth_date: datetime,
    available_resource_id: int,
    complex_resource_id: int,
):
    r = requests.post(
        "https://emias.info/api/new/eip5orch?getAvailableResourceScheduleInfo",
        json={
            "jsonrpc": "2.0",
            "id": "asdfghj",
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
    return r.json()["result"]["scheduleOfDay"]

from enum import unique
from datetime import datetime
from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    oms_number = db.Column(db.String(16), unique=True)
    birth_date = db.Column(db.Date)
    email = db.Column(db.String(120), unique=True)
    appointments = db.relationship("Appointment", backref="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User {self.oms_number}>"


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    available_resource_id = db.Column(db.Integer)
    complex_resource_id = db.Column(db.Integer)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return f"<Appointment {self.available_resource_id}>"

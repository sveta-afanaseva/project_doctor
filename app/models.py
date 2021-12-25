from enum import unique
from datetime import datetime
from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    omsNumber = db.Column(db.String(16), unique=True)
    birthDate = db.Column(db.Date)
    email = db.Column(db.String(120), unique=True)
    appointments = db.relationship("Appointment", backref="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User {self.omsNumber}>"


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    availableResourceId = db.Column(db.Integer)
    complexResourceId = db.Column(db.Integer)
    startTime = db.Column(db.DateTime)
    endTime = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return f"<Appointment {self.availableResourceId}>"

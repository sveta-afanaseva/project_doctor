from email.policy import default
from enum import unique
from datetime import datetime
from venv import create
from app import db
from flask_login import UserMixin
from app import login
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    oms_number = db.Column(db.String(16), unique=True)
    birth_date = db.Column(db.Date)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))
    appointments = db.relationship("Appointment", backref="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User {self.oms_number}>"
        
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    available_resource_id = db.Column(db.Integer)
    complex_resource_id = db.Column(db.Integer)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.Boolean, default=True, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    def __repr__(self):
        return f"<Appointment {self.available_resource_id}>"

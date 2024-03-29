from datetime import date
from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    DateField,
    SelectField,
)
from wtforms import validators
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length
from app.models import User
import email_validator


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("запомнить меня")
    submit = SubmitField("Войти")


class RegistrationForm(FlaskForm):
    oms_number = PasswordField("Полис ОМС", validators=[DataRequired(), Length(16, 16)])
    birth_date = DateField("Дата рождения", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    password2 = PasswordField(
        "Повторите пароль", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_oms_number(self, oms_number):
        user = User.query.filter_by(oms_number=oms_number.data).first()
        if user is not None:
            raise ValidationError("Пользователь с таким ОМС уже зарегистрирован")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Пользователь с таким е-мейлом уже существует")


class EditProfileForm(FlaskForm):
    oms_number = StringField("Полис ОМС", validators=[DataRequired(), Length(16, 16)])
    birth_date = DateField("Дата рождения", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    submit = SubmitField("Сохранить изменения")

    def validate_oms_number(self, oms_number):
        if oms_number.data != current_user.oms_number:
            user = User.query.filter_by(oms_number=oms_number.data).first()
            if user is not None:
                raise ValidationError("Пользователь с таким ОМС уже зарегистрирован")

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user is not None and user is not current_user:
                raise ValidationError("Пользователь с таким е-мейлом уже существует")


class AppointmentForm(FlaskForm):
    doctor = StringField("Врач", render_kw={"disabled": "disabled"})
    date = SelectField("Дата", validators=[DataRequired()])
    start_time = SelectField("Время начала", validators=[DataRequired()])
    end_time = SelectField("Время окончания", validators=[DataRequired()])
    submit = SubmitField("Создать запись")

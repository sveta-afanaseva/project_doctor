from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, DateField
from wtforms import validators
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from app.models import User
import email_validator


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember_me = BooleanField("запомнить меня")
    submit = SubmitField("Войти")

class RegistrationForm(FlaskForm):
    oms_number = StringField('Полис ОМС', validators=[DataRequired()])
    birth_date = DateField('Дата рождения', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField(
        'Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_oms(self, oms_number):
        user = User.query.filter_by(oms_number=oms_number.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким ОМС уже зарегистрирован')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Пользователь с таким е-мейлом уже существует')
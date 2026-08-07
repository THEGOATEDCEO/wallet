from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, PasswordField, StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=40)])
    email = StringField('Email', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=80)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=6, max=80)])
    submit = SubmitField('Create account')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Log in')


class SendForm(FlaskForm):
    recipient = StringField('Recipient', validators=[DataRequired(), Length(max=80)])
    amount = IntegerField('Amount', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Send PERKS')


class BuyPerksForm(FlaskForm):
    requested_perks = IntegerField('Number of PERKS', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit Purchase Request')


class SellPerksForm(FlaskForm):
    amount = IntegerField('Amount of PERKS to Sell', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit Sale')


class WalletSettingsForm(FlaskForm):
    perk_price = StringField('Perk Price (₹)', validators=[DataRequired()])
    submit = SubmitField('Update Price')


class PurchaseRequestActionForm(FlaskForm):
    action = HiddenField('Action')
    submit = SubmitField('Apply')


class AdminForm(FlaskForm):
    action = HiddenField('Action')
    target_user_id = HiddenField('Target User')
    amount = IntegerField('Amount', validators=[Optional(), NumberRange(min=1)])
    submit = SubmitField('Apply')


class SearchUsersForm(FlaskForm):
    query = StringField('Search', validators=[Optional(), Length(max=80)])
    submit = SubmitField('Search')


class MiningForm(FlaskForm):
    nonce = StringField('Nonce', validators=[DataRequired(), Length(min=15, max=15), Regexp('^[0-9]{15}$', message='Nonce must be exactly 15 digits')])
    submit = SubmitField('Submit Mining Challenge')


class TerminateForm(FlaskForm):
    confirm = HiddenField('confirm', default='1')
    submit = SubmitField('Terminate Server')

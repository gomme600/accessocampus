from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, BooleanField, SubmitField, RadioField, \
    TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, \
    Length
from app.models import User, UID


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Request Password Reset')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[DataRequired()])
    submit = SubmitField('Submit')

class CommandForm(FlaskForm):
    building_submit = StringField('Building name (ex: irit2) - Leave blank for all')
    room_submit = StringField('Room name (ex: 366) - Leave blank for all')
    client_ID_submit = StringField('Door/Gate ID (ex: 92) - Leave blank for all')
    command = RadioField("", choices=[('force_open', 'Force Open'), ('force_close', 'Force Close'), ('normal', 'Return to normal'), ('status', 'Get status in log')], default='normal')
    command_submit = SubmitField('SendCommand')

def validate_name(form, field):
        #print("Checking name: " + UID.query.filter_by(name=field.data).first().name)
        try:
            user = UID.query.filter_by(name=field.data).first().name
            if user is not None:
                raise ValidationError('Please use a different name.')
        except:
            print("Name field empty!")

class AddUidForm(FlaskForm):
    uid_submit = StringField('UID', validators=[DataRequired()])
    door_submit = StringField('Door', validators=[DataRequired()])
    name_submit = StringField('Name', validators=[DataRequired(), validate_name])
    code_submit = PasswordField('Code', validators=[DataRequired()])
    code_submit_2 = PasswordField('Repeat code', validators=[DataRequired(), EqualTo('code_submit_2')])
    photo = FileField(validators=[FileRequired()])
    add_submit = SubmitField('Add')

class RemoveUidForm(FlaskForm):
    ID_submit = StringField('Name', validators=[DataRequired()])
    remove_submit = SubmitField('Remove')


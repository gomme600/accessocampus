from datetime import datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, \
    ResetPasswordRequestForm, ResetPasswordForm, AddUidForm, RemoveUidForm, CommandForm
from app.models import User, Post, UID
from app.email import send_password_reset_email
import paho.mqtt.client as mqtt #import the mqtt client
import time #Used for the timing
import json #Used for converting to and from json strings
import settings
import os
from flask_wtf.file import FileField, FileRequired
from werkzeug.utils import secure_filename
import base64
from PIL import Image
from io import BytesIO
import sys

##########################
##----USER SETTINGS----###
##########################

#Connection variables, change as required
MQTT_server = "neocampus.univ-tlse3.fr"
MQTT_user = "test"
MQTT_password = "test"
#The MQTT topic where we find the weewx default loop topic: example: TestTopic/_meteo
MQTT_topic = "TestTopic/req"

#The MQTT topic to publish outdoor data into (weather station data)
MQTT_auth_topic = "TestTopic/auth"

##########################
##----END  SETTINGS----###
##########################

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
##    form = PostForm()
##    if form.validate_on_submit():
##        post = Post(body=form.post.data, author=current_user)
##        db.session.add(post)
##        db.session.commit()
##        flash('Command sent!')
##        return redirect(url_for('index'))
    form = AddUidForm()
    form2 = RemoveUidForm()
    form3 = CommandForm()
#    print("Form 1: ")
#    print(form.validate_on_submit())
#    print(form.errors)
#    print("Form 2: ")
#    print(form2.validate_on_submit())
#    print(form2.errors)
#    print("Form 3: ")
#    print(form3.validate_on_submit())
#    print(form3.errors)

    if form.validate_on_submit() and form.add_submit.data:
        print("Form1")
        if((form.uid_submit.data != None) and (form.door_submit.data != None) and (form.name_submit.data != None) and (form.code_submit.data != None)):
            f = form.photo.data

            buffer = BytesIO()
            buffer.seek(0)
            f.save(buffer)

            #f.save(os.path.join('faces', secure_filename(form.name_submit.data)+'.jpg'))
            #img = Image.open("faces/"+secure_filename(form.name_submit.data)+'.jpg')

            buffer.seek(0)
            img = Image.open(buffer)
            print(sys.getsizeof(buffer))
            maxsize = (256, 256)
            img.thumbnail(maxsize)

            #img = img.resize((256, 256))
            print(sys.getsizeof(buffer))
            buffer.seek(0)
            img.save("tmp.jpg", "JPEG", quality=60, optimize=True)
            #img.save("faces/"+secure_filename(form.name_submit.data)+'.jpg',"JPEG", optimize=True)
            #with open("faces/"+secure_filename(form.name_submit.data)+'.jpg', "rb") as img_file:
                #received_image_B64 = base64.b64encode(img_file.read())
            #os.remove("faces/"+secure_filename(form.name_submit.data)+'.jpg')

            with open("tmp.jpg", "rb") as img_file:
                received_image_B64 = base64.b64encode(img_file.read())
            os.remove("tmp.jpg")
            received_image_B64 = str(received_image_B64)[2:-1]
            received_image_B64 = "data:image/jpeg;base64," + received_image_B64
            data = UID(uid=form.uid_submit.data, door=form.door_submit.data, name=form.name_submit.data, image=received_image_B64)
            data.set_code(form.code_submit.data)
            db.session.add(data)
            db.session.commit()
            flash('Data added!')
        else:
            flash('Incomplete form!')
        return redirect(url_for('index'))
    
    if form2.validate_on_submit() and form2.remove_submit.data:
        print("Form2")
        if(form2.ID_submit.data != None):
            to_delete = UID.query.filter_by(name=form2.ID_submit.data).first()
        else:
            flash("Please input a name!")
        if(to_delete != None):
            db.session.delete(to_delete)
            db.session.commit()
            flash('Data removed!')
        else:
            flash("Entry doesn't exist!")
        return redirect(url_for('index'))
    
    if form3.validate_on_submit() and form3.command_submit.data:
        print("Form3")
        flash('Command sent!')

        #Get command and unit_ID
        command = form3.command.data
        if(form3.client_ID_submit.data != ""):
            unit_ID = form3.client_ID_submit.data
        else:
            unit_ID = "ALL"

        if(form3.building_submit.data != ""):
            building_ID = form3.building_submit.data
        else:
            building_ID = "ALL"

        if(form3.room_submit.data != ""):
            room_ID = form3.room_submit.data
        else:
            room_ID = "ALL"
        
        #MQTT address
        broker_address=MQTT_server
        print("creating new instance")
        client = mqtt.Client("P98") #create new instance

        # Auth
        client.username_pw_set(username=MQTT_user,password=MQTT_password)

        # now we connect
        print("connecting to broker")
        client.connect(broker_address) #connect to broker

        #Publish
        mqtt_payload = {"unit_id": unit_ID, "command": command}
        client.publish(building_ID + "/" + room_ID + "/access/command", json.dumps(mqtt_payload))
        print("Published to: " + building_ID + "/" + room_ID + "/access/command")
                  
        return redirect(url_for('index'))
    
    
    page = request.args.get('page', 1, type=int)
    posts = UID.query.order_by(UID.id.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', form=form, form2=form2, form3=form3,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('explore.html', title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    #if current_user.is_authenticated:
    #    return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))

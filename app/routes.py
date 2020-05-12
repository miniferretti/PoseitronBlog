from app import app, db
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Post
from werkzeug.urls import url_parse
from datetime import datetime
# import matplotlib.pyplot as plt
# import io
# import base64
import webbrowser
import time
import random
import json
from struct import unpack
from struct import pack
import socket
import select
# import requests

ID_type = 1  # Type
UDP_IP = "192.168.1.111"  # IP address of the robot
UDP_PORT = 5005  # Network Port
# Binding of the socket to the UDP protocol
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)

# timeSpeed = 0

# print('Debut routes')


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Home', form=form, posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


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
    return render_template('edit_profile.html', title='Edit Profile', form=form)


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
    return render_template("index.html", title='Explore', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/robotPresentation')
@login_required
def robotPresentation():
    page = request.args.get('page', 1, type=int)
    next_url = url_for('robotPresentation')
    return render_template("robotPresentation.html", title='Robot\' presentation')

# a modifier pour recuperer les donnees du robot


class L(list):
    def append(self, item):
        list.append(self, item)
        if len(self) > 100:
            del self[0]


Vr = L()
VrRef = L()
Vl = L()
VlRef = L()
Time = L()
X = 0
Y = 0


@app.route('/_robotData', methods=['GET'])
@login_required
def robotData():
    data = [float(0), float(0), float(0),
            float(0), float(0), float(0),
            float(0), float(0), float(0),
            float(0), int(0), float(0),
            float(0), float(0), float(0),
            int(ID_type)]
    msg = pack('ffffffffffiffffi', *data)
    sock.sendto(msg, (UDP_IP, UDP_PORT))
    ready = select.select([sock], [], [], 0.1)
    if ready[0]:
        msg2 = sock.recv(56)
        data1 = unpack('<7d', msg2)
        Vr.append(data1[0])
        VrRef.append(data1[1])
        Vl.append(data1[2])
        VlRef.append(data1[3])
        Time.append(data1[4])
        X = (data1[5])
        Y = (data1[6])
    # global timeSpeed
    # timeSpeed = timeSpeed + 500
    # X = random.randint(0, 100)
    # Y = random.randint(0, 100)
    # Vl = random.randint(0, 100)
    # Vr = random.randint(0, 100)
    # VrRef = 50
    # VlRef = 50
    return jsonify(resultx=X, resulty=Y, speedLeft=Vl, speedRight=Vr,
                   consignLeft=VlRef, consignRight=VrRef, time=Time)


@app.route('/graphiques')
@login_required
def graphiques():
    return render_template("graphiques.html", title='Robot data')

# print('Fin routes')

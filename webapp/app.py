#!/usr/bin/env python3
# TODO: Organize imports properly
from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

from generatetopo import odl_topo_builder
from get_stats import Odl_Stat_Collector
from deviceInfo import odl_switch_info
from auxiliary import Webapp_Auxiliary
from forms import RegisterForm
from user_db import create_user_db


app = Flask(__name__)
# aux = Webapp_Auxiliary()
# odlControllerList = aux.device_scan()
# controllerIP = odlControllerList[0]
controllerIP = "134.117.89.138"

# TODO: Manage creds outside of app
app.secret_key = "secret123"
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'sdlens'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Init Mysql
mysql = MySQL(app)

# TODO: CLEAN UP CODE, MAKE INIT SCRIPT
@app.route("/")
def index():
    if 'logged_in' in session:
        return render_template('home.html')
    else:
        return redirect(url_for('login'))


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route("/dashboard")
@is_logged_in
def dashboard():
    return render_template('home.html')


@app.route("/topology")
@is_logged_in
def topology():
    parser = odl_topo_builder(controllerIP)
    return render_template('topo.html', topologyInfo=parser.fetch_topology())


@app.route("/node-stats")
@is_logged_in
def node_stats():
    o = Odl_Stat_Collector(controllerIP)
    return render_template('nodes.html', nodes=o.run())


@app.route("/device-info")
@is_logged_in
def device_info():
    o = odl_switch_info(controllerIP)
    return render_template('deviceInfo.html', nodes=o.run())

 
@app.route("/controller")
@is_logged_in
def getControllerIP():
    # print(odlControllerList)
    return render_template('settings.html', odlIP=controllerIP)


@app.route("/graphs")
@is_logged_in
def graphs():
    return render_template('graphs.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        submit_user(form)
        flash('You are now registered and can login', 'success')
        redirect(url_for('index'))

    return render_template('register.html', form=form)


def submit_user(form):
    """Helper function to submit user registration to the Database."""
    name = form.name.data
    email = form.email.data
    username = form.username.data
    password = sha256_crypt.encrypt(str(form.password.data))
    # TODO: Move into sql tooling object
    cur = mysql.connection.cursor()
    query = ("INSERT INTO users(name, email, username, password) " +
             f"VALUES('{name}', '{email}', '{username}', '{password}')")
    cur.execute(query)
    mysql.connection.commit()
    cur.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']
        # TODO: Use SQL tooling object once made.
        cur = mysql.connection.cursor()
        # Get user by username
        result = cur.execute(f"SELECT * FROM users WHERE username = '{username}'")

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare passwords
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in', 'sucess')
                return redirect(url_for('dashboard'))
            else:
                error = 'invalid login'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out')
    return redirect(url_for('login'))


if __name__ == "__main__":
    create_user_db()
    app.run(debug=True)

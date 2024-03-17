import flask
import flask_login
from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, insert, update
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user

# flask init
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-goes-here'

# db init
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///li_main.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class User(UserMixin, db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(32))
    password: Mapped[str] = mapped_column(String(64))
    team_code: Mapped[str] = mapped_column(String(16))

class Team(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(32))
    admin_id: Mapped[int] = mapped_column(Integer)

with app.app_context():
    db.create_all()

# login init
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index.html',  logged_in=current_user.is_authenticated, user=current_user)
    else:
        return redirect(url_for('login'))
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        check_if_exist = db.session.execute(db.select(User).where(User.email == request.form['email'])).scalar()
        if check_if_exist == None:
            password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256', salt_length=8)
            new_user = User(
                email=request.form.get('email'),
                name=request.form.get('username'),
                password=password,
                team_code=request.form.get('team_code')
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            if new_user.team_code == '':
                return redirect(url_for('joinTeam'))
            return redirect(url_for('home'))
        else:
            flask.flash("Email already in use")
    return render_template("register.html")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = db.session.execute(db.select(User).where(User.email == request.form['email'])).scalar()
        if user != None:
            hashed_password = db.session.execute(
                db.select(User.password).where(User.email == request.form['email'])).scalar()
            if check_password_hash(hashed_password, request.form['password']):
                login_user(user)
                return redirect(url_for('home'))
        else:
            flask.flash('Wrong creditentials')
    return render_template("login.html")

@app.route('/myTasks', methods=['GET', 'POST'])
def myTasks():
    return render_template('myTasks.html')
@app.route('/teamTasks', methods=['GET', 'POST'])
def teamTasks():
    return render_template('teamTasks.html')
@app.route('/joinTeam', methods=['GET','POST'])
def joinTeam():
    if current_user.team_code == '':
        if request.method == 'POST':
            id = current_user.id
            db.session.execute(db.update(User).where(User.id == id).values(team_code=request.form.get('team_code')))
            db.session.commit()
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))
    return render_template('teams.html')
@app.route('/createTeam', methods=['GET','POST'])
def createTeam():
    return render_template('createTeam.html')

@app.route('/teamDashboard', methods=['GET','POST'])
def teamDashboard():
    return render_template('teamDashboard.html')
@app.route('/addTask', methods=['GET','POST'])
def addTask():
    return render_template('addTask.html')
@app.route('/createInvite', methods=['GET','POST'])
def createInvite():
    return render_template('invite.html')
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
# app init
if __name__ == "__main__":
    app.run(debug=True)
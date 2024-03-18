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
    team_id: Mapped[str] = mapped_column(String(64))
    is_admin: Mapped[int] = mapped_column(Integer)


class Team(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(32))


class TeamInvites(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer)
    no_uses: Mapped[int] = mapped_column(Integer)


class TeamMembers(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id = mapped_column(Integer)
    user_id = mapped_column(Integer)


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
        team = db.session.execute(db.select(Team).where(Team.id == current_user.team_id)).scalar()
        return render_template('index.html',  logged_in=current_user.is_authenticated, user=current_user, team=team)
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        check_if_exist = db.session.execute(db.select(User).where(User.email == request.form['email'])).scalar()
        if check_if_exist == None:
            password = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256', salt_length=8)
            if request.form.get('team_code') != '':
                new_user = User(
                    email=request.form.get('email'),
                    name=request.form.get('username'),
                    password=password,
                    team_id=request.form.get('team_code'),
                    is_admin=0
                )
            else:
                new_user = User(
                    email=request.form.get('email'),
                    name=request.form.get('username'),
                    password=password,
                    team_id='',
                    is_admin=0
                )
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('joinTeam'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
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
    return render_template("login.html", messages=flask.get_flashed_messages())

@app.route('/myTasks', methods=['GET', 'POST'])
def myTasks():
    return render_template('myTasks.html')
@app.route('/teamTasks', methods=['GET', 'POST'])
def teamTasks():
    return render_template('teamTasks.html')
@app.route('/joinTeam', methods=['GET','POST'])
def joinTeam():
    if current_user.team_id == '':
        if request.method == 'POST':
            # id = current_user.id
            # db.session.execute(db.update(User).where(User.id == id).values(team_id=request.form.get('team_code')))
            # db.session.commit()
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))
    return render_template('teams.html')
@app.route('/leaveTeam', methods=['GET','POST'])
def leaveTeam():
    return redirect(url_for('home'))


@app.route('/createTeam', methods=['GET','POST'])
def createTeam():
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        new_team = Team(
            team_name = request.form.get('team_name')
        )
        db.session.add(new_team)
        # db.session.commit()
        db.session.execute(db.update(User).where(User.id == current_user.id).values(is_admin=1))
        db.session.execute(db.update(User).where(User.id == current_user.id).values(team_id=new_team.id))
        new_member = TeamMembers(
            team_id = new_team.id,
            user_id = current_user.id
        )
        db.session.add(new_member)
        db.session.commit()
        return redirect(url_for('home'))
    if current_user.is_authenticated:
        if current_user.team_id == '':
            return render_template('createTeam.html')
    else:
        return redirect(url_for('login'))

@app.route('/teamDashboard', methods=['GET','POST'])
def teamDashboard():
    if current_user.is_authenticated:
        if current_user.is_admin == 1:
            team = db.session.execute(db.select(Team).where(Team.id == current_user.team_id)).scalar()
            team_members = db.session.execute(db.select(TeamMembers).where(TeamMembers.team_id == team.id)).scalars().all()
            users = []
            for team_user in team_members:
                users.append(db.session.execute(db.select(User).where(User.id == team_user.user_id)).scalar())
            return render_template('teamDashboard.html', users=users)
        else:
            return redirect(url_for('teamTasks'))
    else:
        return redirect(url_for('createTeam'))
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
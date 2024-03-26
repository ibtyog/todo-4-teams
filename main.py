import flask
import flask_login
from flask import Flask, render_template, request, url_for, redirect, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, insert, update
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import datetime
from code_gen import get_random_code
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
    team_code: Mapped[str] = mapped_column(String(8))
    team_id: Mapped[int] = mapped_column(Integer)
    no_uses: Mapped[int] = mapped_column(Integer)


class TeamMembers(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id = mapped_column(Integer)
    user_id = mapped_column(Integer)


class PersonalTask(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(128))
    expiration_date: Mapped[int] = mapped_column(Integer)
    str_time: Mapped[str] = mapped_column(String(32))

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
        current_time = int(datetime.datetime.now().strftime("%Y%m%d%H%M%S")[:-2])
        tasks = db.session.execute(db.Select(PersonalTask).where(PersonalTask.user_id == current_user.id, PersonalTask.expiration_date >= current_time).order_by(PersonalTask.expiration_date).limit(3)).scalars().all()
        return render_template('index.html', user=current_user, team=team, tasks=tasks)
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
                    team_id='',
                    is_admin=0
                )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            if request.form.get('team_code') != '':
                team_code = request.form.get('team_code')
                team = db.session.execute(db.Select(TeamInvites).where(TeamInvites.team_code == team_code)).scalar()
                if team != None:
                    new_member = TeamMembers(
                        team_id = team.team_id,
                        user_id = current_user.id
                    )
                    db.session.add(new_member)
                    db.session.commit()
                    db.session.execute(db.update(User).where(User.id == new_member.user_id).values(team_id=new_member.team_id))

                    no_uses = team.no_uses - 1
                    db.session.execute(db.update(TeamInvites).where(TeamInvites.id == team.id).values(no_uses=no_uses))
                    invite = db.session.execute(db.select(TeamInvites).where(TeamInvites.id == team.id)).scalar()
                    if invite.no_uses == 0:
                        db.session.delete(invite)
                    db.session.commit()
            else:
                return redirect(url_for('joinTeam'))

            return redirect(url_for('home'))
        else:
            flask.flash("Email already in use")
    return render_template("register.html", user=current_user)

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
    return render_template("login.html", messages=flask.get_flashed_messages(), user=current_user)

@app.route('/myTasks', methods=['GET', 'POST'])
def myTasks():
    if current_user.is_authenticated:
        current_time = int(datetime.datetime.now().strftime("%Y%m%d%H%M%S")[:-2])
        current_tasks = db.session.execute(db.Select(PersonalTask).where(PersonalTask.user_id == current_user.id, PersonalTask.expiration_date >= current_time)).scalars().all()
        expired_tasks = db.session.execute(db.Select(PersonalTask).where(PersonalTask.user_id == current_user.id, PersonalTask.expiration_date < current_time)).scalars().all()

        return render_template('myTasks.html', user=current_user, c_tasks=current_tasks, e_tasks=expired_tasks)
    return redirect(url_for('login'))


@app.route('/teamTasks', methods=['GET', 'POST'])
def teamTasks():
    return render_template('teamTasks.html', user=current_user)


@app.route('/joinTeam', methods=['GET','POST'])
def joinTeam():
    if current_user.team_id == '':
        if request.method == 'POST':
            id = current_user.id
            team_code = request.form.get('team_code')
            team = db.session.execute(db.Select(TeamInvites).where(TeamInvites.team_code == team_code)).scalar()
            if team != None:
                db.session.execute(db.update(User).where(User.id == id).values(team_id=team.team_id))
                new_member = TeamMembers(
                    team_id = team.id,
                    user_id = current_user.id
                )
                db.session.add(new_member)
                no_uses = team.no_uses - 1
                db.session.execute(db.update(TeamInvites).where(TeamInvites.id == team.id).values(no_uses=no_uses))
                invite = db.session.execute(db.select(TeamInvites).where(TeamInvites.id == team.id)).scalar()
                if invite.no_uses == 0:
                    db.session.delete(invite)
                db.session.commit()
            return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))
    return render_template('teams.html', user=current_user)
# TODO: if admin leaves team delete team and remove members, invites, tasks
@app.route('/leaveTeam', methods=['GET','POST'])
def leaveTeam():
    team_id = current_user.team_id
    db.session.execute(db.update(User).values(team_id=''))
    team_member = db.session.execute(db.Select(TeamMembers).where(TeamMembers.user_id == current_user.id)).scalar()
    db.session.delete(team_member)
    team_count = db.session.execute(db.Select(TeamMembers).where(TeamMembers.team_id == team_id)).scalars().all()
    if team_count == []:
        team = db.session.execute(db.Select(Team).where(Team.id == team_id)).scalar()
        invites = db.session.execute(db.Select(TeamInvites).where(TeamInvites.team_id == team_id)).scalars().all()
        for invite in invites:
            db.session.delete(invite)
        db.session.delete(team)

    db.session.commit()
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
            return render_template('createTeam.html', user=current_user)
    else:
        return redirect(url_for('login'))
# TODO: add members tasks and removing members
@app.route('/teamDashboard', methods=['GET','POST'])
def teamDashboard():
    if current_user.is_authenticated:
        if current_user.is_admin == 1:
            team = db.session.execute(db.select(Team).where(Team.id == current_user.team_id)).scalar()
            team_members = db.session.execute(db.select(TeamMembers).where(TeamMembers.team_id == team.id)).scalars().all()
            users = []
            for team_user in team_members:
                users.append(db.session.execute(db.select(User).where(User.id == team_user.user_id)).scalar())
            return render_template('teamDashboard.html', users=users, user=current_user)
        else:
            return redirect(url_for('teamTasks'))
    else:
        return redirect(url_for('createTeam'))

@app.route('/createInvite', methods=['GET','POST'])
def createInvite():
    if current_user.is_authenticated:
        if current_user.is_admin == 1:
            if request.method == 'POST':
                code = get_random_code()
                while db.session.execute(db.Select(TeamInvites).where(TeamInvites.team_code == code)).scalar() != None:
                    code = get_random_code()
                new_invite = TeamInvites(
                    team_code=code,
                    team_id = current_user.team_id,
                    no_uses = request.form.get('no_uses')
                )
                team_str = new_invite.team_code
                db.session.add(new_invite)
                db.session.commit()
                print(team_str)
                return render_template('invite.html',  user=current_user, team_code=team_str)
            return render_template('createInvite.html', method=request.method, user=current_user)
        else:
            return redirect(url_for('createTeam'))
    else:
        return redirect(url_for('login'))

@app.route('/createPersonalTask', methods=['GET','POST'])
def createPersonalTask():
    if current_user.is_authenticated:
        if request.method == "POST":
            datetime = request.form.get('expiration-date')
            date = int(datetime[0:4] + datetime[5:7] + datetime[8:10] + datetime[11:13] + datetime[14:])
            str_time = datetime[0:4] + '-' + datetime[5:7] + '-' +  datetime[8:10] + ' ' +  datetime[11:13] + ':' +  datetime[14:]
            task = PersonalTask(
                user_id = current_user.id,
                title = request.form.get('title'),
                expiration_date = date,
                str_time = str_time
            )
            db.session.add(task)
            db.session.commit()
            return redirect(url_for('myTasks'))
        return render_template('createPersonalTask.html', user=current_user)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
# app init
if __name__ == "__main__":
    app.run(debug=True)
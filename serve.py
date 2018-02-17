import os
from collections import Counter
from datetime import datetime, timedelta

from flask import Flask, url_for, redirect, request, render_template, abort
from flask_admin import base, helpers, expose
from flask_admin.contrib import sqla
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from wtforms import form, fields, validators
from werkzeug.security import generate_password_hash, check_password_hash

import flask_admin as admin
import flask_login as login

import atexit
from apscheduler.scheduler import Scheduler

from steemit import tag_filter

app = Flask(__name__)

app.config['SECRET_KEY'] = 'steemit'


app.config['DATABASE_FILE'] = 'tag.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = False
db = SQLAlchemy(app)


class Tags(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_name = db.Column(db.String(200))
    day = db.Column(db.Date)
    last = db.Column(db.Integer, default = None)

    def __str__(self):
        return str(self.tag_name)

    def __repr__(self):
        return '<tag_name %r>' % (self.tag_name)

    def get_or_create(self, tag, day):
        get_tags = self.query.filter_by(tag_name=tag, day=day).first() or False
        if get_tags:
            return get_tags
        else:
            self.tag_name = tag
            self.day = day 
            db.session.add(self)
            db.session.commit()
            return self

class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.Integer(), db.ForeignKey(Tags.id))
    tag = db.relationship(Tags)

    post_id = db.Column(db.Integer())
    author = db.Column(db.String(200))
    title = db.Column(db.String(400))
    url = db.Column(db.String(400))

    def __str__(self):
        return str(self.post_id)

    def __repr__(self):
        return '<tag_name %r>' % (self.post_id)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        if not check_password_hash(user.password, self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    email = fields.StringField()
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated


# Create customized index view class that handles login & registration
class MyAdminIndexView(base.AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        link = ''
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))
    
# Flask views
@app.route('/admin')
def admin():
    return redirect(url_for('admin.login_view'))

@app.route('/')
def index():
    if request.query_string and request.args.get('tag'):
        return redirect('/' + request.args.get('tag'))
    
    return render_template('form.html')




# Initialize flask-login
init_login()

# Create admin
admin = base.Admin(app, 'Bot', index_view=MyAdminIndexView(), base_template='my_master.html')

# Add view
admin.add_view(MyModelView(Tags, db.session))
admin.add_view(MyModelView(Posts, db.session))
admin.add_view(MyModelView(User, db.session))

def build_sample_db():
    db.drop_all()
    db.create_all()

    test_user = User(login="test", password=generate_password_hash("test"))
    db.session.add(test_user)
    db.session.commit()
    return

global post_ids

def task(tag, min=1):
    cron = Scheduler(daemon=True)
    cron.start()

    @cron.interval_schedule(minutes=min)
    def job_function():
        now_day = datetime.now().date()
        tag_db = Tags().get_or_create(tag, now_day)

        tag_list = tag_filter(tag, 100)
        tag_list.reverse()
        new_tag = {}

        for tags in tag_list:
            #tags['root_comment']
            _create_time = datetime.strptime(tags['created'], '%Y-%m-%dT%H:%M:%S') + timedelta(hours=3)
            if now_day.day == _create_time.day:
                new_tag[tags['root_comment']] = tags

        post_list = list(new_tag.keys())
        import ipdb; ipdb.set_trace()

        if not tag_db.last:
            tag_db.last = post_list[-1]
            post_ids = tag_db.last
            db.session.add(tag_db)
            db.session.commit()
        
            #Kayit işlemini yap
        else:
            new_list = post_list[post_list.index(tag_db.last)+1:]
            tag_db.last  = new_list[-1]
            db.session.add(tag_db)
            db.session.commit()

            #Kayit işlemini yap
            import ipdb; ipdb.set_trace()
            print(1)
    
    atexit.register(lambda: cron.shutdown(wait=False))

if __name__ == '__main__':
    task('tr', 1)

    #main
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)
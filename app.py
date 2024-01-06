from flask import Flask, redirect, url_for, request

from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView

from flask_login import current_user


app = Flask(__name__, static_folder='static')
app.config.from_pyfile('config.py')

from database import *

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_admin() # This does the trick rendering the view only if the user is authenticated



admin = Admin(app, 'Admin Area', template_mode='bootstrap4',index_view=MyAdminIndexView())

admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Subforum, db.session))
admin.add_view(ModelView(Post, db.session))
admin.add_view(ModelView(File, db.session))
admin.add_view(ModelView(Comment, db.session))

#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:admin@localhost:5432/web_forum'
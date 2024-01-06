from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from random import choice
from string import digits
from datetime import datetime
from app import app

import re

global db
db = SQLAlchemy(app)

username_pattern = re.compile('^[A-Za-z0-9@#$%^&+=]{8,32}')
password_pattern = re.compile('^[A-Za-z0-9@#$%^&+=]{6,32}')


def valid_username(username):
	if len(username) < 6 or len(username) > 32:
		return False
	return True


def valid_password(password):
	if len(password) < 6 or len(password) > 32:
		return False
	return True


def valid_title(title):
	valid = False
	print(f"1111111111111111111111111111TEST {Post.query.filter(Post.post_title == title).first()}")
	if len(title) > 4 and len(title) < 140 and Post.query.filter(Post.post_title == title).first() is None:
		valid = True
	return valid 

def valid_content(content):
	return len(content) > 10 and len(content) < 5000

def valid_comment(content):
		return len(content) < 2500

def valid_media_type(filename):
		IMAGE_FORMATS = [".jpg", ".png", ".jpeg", ".gif"]
		VIDEO_FORMATS = [".mp4", ".avi", ".mov"]

		if filename == "":
			return None
		
		if filename[filename.index('.'):] in IMAGE_FORMATS:
			return "img"

		if filename[filename.index('.'):] in VIDEO_FORMATS:
			return "vid"

		else:
			return f"You can only add these file types: \n{IMAGE_FORMATS};\n{VIDEO_FORMATS}"

def username_taken(username):
	return User.query.filter(User.username == username).first()

def email_taken(email):
	return User.query.filter(User.email == email).first()

def subforum_id_taken(subid):
	return Subforum.query.filter(Subforum.sub_forum_id == subid)

def subforum_name_taken(subname):
	return Subforum.query.filter(Subforum.sub_forum_name == subname).first()

def get_username_by_id(id):
	return User.query.filter(User.id == id).first()["username"]


def generate_subforum_id():
    result = ""
    for _ in range(0, 5):
       result += choice(str(digits))
    return int(result)


class User(db.Model, UserMixin):
	__tablename__ = "users"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, unique=True)
	username = db.Column(db.Text, unique=True)
	password_hash = db.Column(db.Text)
	email = db.Column(db.Text, unique=True)
	admin = db.Column(db.Boolean, default=False)
	posts = db.relationship("Post", backref="users")
	comments = db.relationship("Comment", backref="user")
	#comments = db.relationship("Comment", backref="user")


	def __init__(self, email, username, password, user_id=None):
		self.user_id = user_id
		self.email = email
		self.username = username
		self.password_hash = generate_password_hash(password)


	def is_admin(self):
		return self.admin

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)


class Subforum(db.Model):
	__tablename__ = "subforums"
	id = db.Column(db.Integer, primary_key=True)
	sub_forum_id = db.Column(db.Integer, unique=True)
	sub_forum_name = db.Column(db.Text, unique=True)
	sub_forum_description = db.Column(db.Text)
	sub_forum_author = db.Column(db.Integer, db.ForeignKey("users.id"))
	sub_posts = db.relationship("Post", backref="subforum")
	sub_readonly = db.Column(db.Boolean, default=False)
	sub_created_at = db.Column(db.DateTime, default=datetime.now)


	def __init__(self, sub_forum_id, sub_forum_name, sub_forum_description, sub_forum_author, sub_readonly):
		self.sub_forum_id = sub_forum_id
		self.sub_forum_name = sub_forum_name
		self.sub_forum_description = sub_forum_description
		self.sub_forum_author = sub_forum_author
		self.sub_readonly = sub_readonly


	def get_posts_count(self, sub_id):
		return len(Post.query.filter(Post.subforum_id == sub_id).all())


class Post(db.Model):
	__tablename__ = "posts"
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
	subforum_id = db.Column(db.Integer, db.ForeignKey('subforums.id'))
	post_title = db.Column(db.Text, unique=True)
	post_content = db.Column(db.Text)
	post_files = db.relationship("File", backref="post")
	post_comments = db.relationship("Comment", backref="post")
	post_date = db.Column(db.DateTime, default=datetime.now)

	lastcheck = None
	savedresponce = None

	def __init__(self, post_title, post_content):
		self.post_title = post_title
		self.post_content = post_content


	def get_author(self):
		return User.query.filter(User.id == self.user_id).first().username

	def get_time_string(self):
		#this only needs to be calculated every so often, not for every request
		#this can be a rudamentary chache
		now = datetime.now()
		if self.lastcheck is None or (now - self.lastcheck).total_seconds() > 30:
			self.lastcheck = now
		else:
			return self.savedresponce

		diff = now - self.post_date

		seconds = diff.total_seconds()
		if seconds / (60 * 60 * 24 * 30) > 1:
			self.savedresponce =  " " + str(int(seconds / (60 * 60 * 24 * 30))) + " months ago"
		elif seconds / (60 * 60 * 24) > 1:
			self.savedresponce =  " " + str(int(seconds / (60*  60 * 24))) + " days ago"
		elif seconds / (60 * 60) > 1:
			self.savedresponce = " " + str(int(seconds / (60 * 60))) + " hours ago"
		elif seconds / (60) > 1:
			self.savedresponce = " " + str(int(seconds / 60)) + " minutes ago"
		else:
			self.savedresponce =  "Just a moment ago!"

		return self.savedresponce


class File(db.Model):
	__tablename__ = "files"
	id = db.Column(db.Integer, primary_key=True)
	post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))
	filename = db.Column(db.Text)
	data = db.Column(db.LargeBinary)

	def __init__(self, filename, data):
		self.filename = filename
		self.data = data


	def check_media_type(self):
		IMAGE_FORMATS = [".jpg", ".png", ".jpeg", ".gif"]
		VIDEO_FORMATS = [".mp4", ".avi", ".mov"]
		
		if self.filename[self.filename.index('.'):] in IMAGE_FORMATS:
			return "img"

		if self.filename[self.filename.index('.'):] in VIDEO_FORMATS:
			return "vid"


class Comment(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	content = db.Column(db.Text)
	postdate = db.Column(db.DateTime, default=datetime.now)
	user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
	post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

	def __init__(self, content):
		self.content = content

	def get_author(self):
		return User.query.filter(User.id == self.user_id).first()




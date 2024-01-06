from flask import Flask, render_template, request, session, redirect, url_for, send_file
from io import BytesIO
from base64 import b64encode
from app import app
from database import *
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, or_
from flask_login import LoginManager, login_required, current_user, logout_user, login_user

import os
import config


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'


@login_manager.user_loader
def load_user(userid):
	return User.query.get(int(userid))


@app.route('/', methods=['GET', 'POST'])
def main_page():
	subforums = Subforum.query.order_by(desc('sub_created_at')).limit(5)
	posts = Post.query.order_by(desc('post_date')).limit(5)
	query = ""
	if request.method == "POST":
		query = request.form["search_request"]
		obj_type = request.form["obj_type"]
		return redirect(url_for('search', q=query, t=obj_type))
	return render_template("main_page.html", subforums=subforums, posts=posts)


@app.route('/search', methods=["GET","POST"])
def search():
	results = {}
	search_request = request.args.get('q')
	obj_type = request.args.get('t')
	if obj_type == "user":
		requested_user = User.query.filter(User.username.contains(search_request)).all()
		results = requested_user
	if obj_type == "subforum":
		all_subs = Subforum.query.filter(Subforum.sub_forum_name.contains(search_request)).all()
		results = all_subs
	if obj_type == "post":
		all_posts = Post.query.filter(Post.post_title.contains(search_request)).all()
		results = all_posts
	return render_template("search_result.html", query=search_request,results=results)


@app.route('/addsub', methods=['GET', 'POST'])
def addsub():
	if request.method == "POST":
		sub_forum_id = generate_subforum_id()
		sub_forum_name = request.form["sub_name"]
		sub_readonly = request.form.get("readonly", False)
		sub_description = request.form["sub_decrpt"]

		retry = False
		errors = []

		if current_user.is_authenticated:
			sub_forum_author = current_user.id

		if not current_user.is_authenticated:
			sub_forum_author = 1
		
		if len(str(sub_forum_id)) != 5:
			sub_forum_id = generate_subforum_id()
			if subforum_id_taken(sub_forum_id):
				sub_forum_id = generate_subforum_id()

		if not len(sub_forum_name) >= 4 or not len(sub_forum_name) < 32:
			errors.append("Your subforum name isn't valid")
			retry = True

		if subforum_name_taken(sub_forum_name):
			errors.append("Subforum with that name alrealdy exists")
			retry = True

		if sub_readonly is not False:
			sub_readonly = True
			
		if not len(sub_description) > 0:
			sub_description = "No description"

		if retry:
			return render_template("addsub.html", errors=errors)

		new_subforum = Subforum(sub_forum_id, sub_forum_name, sub_description, 
			sub_forum_author, sub_readonly)

		db.session.add(new_subforum)
		db.session.commit()
		#print("ADDED TO DB")
		return redirect(url_for('subforums'))

	return render_template("addsub.html")


@app.route('/login')
def login_page():
	return render_template("login.html")


@app.route('/action_login', methods=['GET', 'POST'])
def action_login():
	if request.method == "POST":
		username = request.form["username"]
		password = request.form["password"]
		user = User.query.filter(User.username == username).first()
		if user and user.check_password(password):
			login_user(user)
			return redirect("/")
		else:
			errors = []
			errors.append("Username or password is incorrect")
			return render_template('login.html', errors=errors)


@app.route('/register')
def register():
	return render_template("register.html")


@app.route('/action_register', methods=['GET', 'POST'])
def action_register():
	if request.method == "POST":
		session.permanent = True
		email = request.form["email"]
		username = request.form["username"]
		password = request.form["password"]
		errors = []
		retry = False

		if email_taken(email):
			errors.append("An account already exists with this email")
			retry = True

		if username_taken(username):
			errors.append("Username is already taken")
			retry = True

		if not valid_username(username):
			errors.append("Username is not valid")
			retry = True

		if not valid_password(password):
			errors.append("Password is not valid")
			retry = True

		if retry:
			return render_template('register.html', errors=errors)

		new_user = User(email, username, password)
		db.session.add(new_user)
		db.session.commit()
		login_user(new_user)
		return redirect("/")


@app.route("/logout")
@login_required
def logout():
	logout_user()
	return redirect("/")



@app.route('/user/<user>/')
@login_required
def user(user):
	if current_user.is_authenticated:
		print(f"!!!!!!!!!!!!!!TEST {current_user.is_admin()}")
		user = current_user
		subforums = Subforum.query.filter(Subforum.sub_forum_author == int(user.id)).all()
		posts = Post.query.filter(Post.user_id == int(user.id)).all()
		comments = Comment.query.filter(Comment.user_id == int(user.id)).all()
	else:
		return redirect(url_for("login"))

	return render_template('user.html', user=user, subforums=subforums, posts=posts, coms=comments)



@app.route('/subforums')
@app.route('/subforums/my')
def subforums():
	page = request.args.get('page', 1, type=int)
	print(page)
	if "/my" in request.base_url:
		author = ""
		if current_user.is_authenticated:
			author = current_user.id
		else:
			return redirect('/subforums')
		all_subforums = Subforum.query.filter(Subforum.sub_forum_author == author).paginate(page=page, per_page=6)
		return render_template("subforums.html", subforums=all_subforums)
	else:
		all_subforums = Subforum.query.paginate(page=page, per_page=6)
		return render_template("subforums.html", subforums=all_subforums)

@app.route('/sub/<sub>/')
def subforum(sub):
	page = request.args.get('page', 1, type=int)
	try:
		q_subforum = Subforum.query.filter(Subforum.sub_forum_id == sub).first()
	except: return redirect("/subforums")
	if q_subforum:
		posts = Post.query.filter(Post.subforum_id == q_subforum.id).paginate(page=page, per_page=6)
		sorted_items = list(posts.items)[::-1]
		posts.items = sorted_items
		return render_template("subforum.html", subforum=q_subforum, posts=posts)   
	else:
		return redirect("/subforums")


@app.route("/viewpost")
def viewpost():
	id = int(request.args.get("post", None))
	post = Post.query.filter(Post.id == id).first()
	if post:
		comments = Comment.query.filter(Comment.post_id == post.id).all()
		images = {}
		videos = {}
		files = File.query.filter(File.post_id == post.id).all()
		
		for file in files:
			ftype = file.check_media_type()
			if ftype == "img":
				images[str(file.id)] = b64encode(file.data).decode('ascii')
			if ftype == "vid":
				videos[str(file.id)] = b64encode(file.data).decode('ascii')

		return render_template("viewpost.html", post=post, data=list, images=images, videos=videos, comments=comments)
	else: return redirect("/subforums")


@app.route('/addpost', defaults={'id': ""})
@app.route('/addpost/<id>')
def addpost(id):
	if id:
		value = id
	else:
		pass
	return render_template("addpost.html", id=id)


@app.route('/action_post', methods=['GET', 'POST'])
def action_post():
	if request.method == "POST":
		sub_id = request.form.get("subforum_id", None)
		#print(f"SUB ID {sub_id}")
		try:
			subforum = Subforum.query.filter(Subforum.sub_forum_id == sub_id).first()
		except: return redirect("/subforums")
		if not subforum:
			return redirect("/subforums")
		post_title = request.form["post_title"]
		post_content = request.form["post_content"]
		post_files = request.files.getlist("form_file")
		print(f"POST FILES: {post_files[0].filename}")

		if current_user.is_anonymous:
			user = User.query.filter(User.user_id == 0).first()  
		else:
			user = current_user

		errors = []
		retry = False

		if not valid_title(post_title):
			errors.append("Title must be between 4 and 140 characters long")
			retry = True

		if not valid_content(post_content):
			errors.append("Post must be between 10 and 5000 characters long")
			retry = True

		if len(post_files) > 3:
			errors.append("You are only allowed to upload a maximum of 3 files")
			retry = True

		if len(post_files) <=3 and post_files[0].filename != "":
			accepted_file_format = True
			for file in post_files:
				accept_types = ['img', 'vid']
				try:
					type_check = valid_media_type(str(file.filename))
				except: pass
				finally: type_check = valid_media_type(str(file.filename))
				if type_check not in accept_types:
					accepted_file_format = False

			if accepted_file_format != True:
				errors.append(valid_media_type("wrong.type"))
				retry = True

		if retry:
			return render_template("addpost.html", errors=errors, id=sub_id)

		has_files = False
		if post_files[0].filename != "":
			has_files = True
		
		post = Post(post_title, post_content)
		db.session.add(post)
		query_post = Post.query.filter(Post.post_title == post_title).first()

		if has_files:
			for file in post_files:
				new_file = File(filename=file.filename, data=file.read())
				db.session.add(new_file)
				added_file = File.query.filter(File.filename == file.filename).first()
				query_post.post_files.append(added_file)

		subforum.sub_posts.append(post)
		user.posts.append(post)
		db.session.commit()
		return redirect("/viewpost?post="+str(post.id))


@app.route("/action_comment", methods=["POST"])
def action_comment():
	if request.method == "POST":
		com_content = request.form["com_content"]

		if not valid_comment(com_content):
			pass

		post_id = request.args.get("post", None)
		post = Post.query.filter(Post.id == post_id).first()
		if not post:
			return redirect("/subforums")

		if current_user.is_authenticated:
			user = current_user
		else:
			user = User.query.filter(User.user_id == 0).first()  

		new_com = Comment(com_content)
		#user.users.append(new_com)
		post.post_comments.append(new_com)
		user.comments.append(new_com)
		db.session.commit()

		return redirect(f'/viewpost?post={post.id}')


@app.route('/download/<id>')
def download(id):
	file_data = File.query.filter(File.id == id).first()
	if file_data:
		return send_file(BytesIO(file_data.data),    download_name=f'{file_data.filename}',) 
	else: 
		return redirect("/")

@app.route('/post/<post>/')
def post(post):
	return f"{post}"

with app.app_context():
	db.create_all()
	# Adding anonymous user
	anon_user = User(user_id=0,username="anonymous", password="ANONYMOUS", email="anonymous@anon.anon")
	if not User.query.filter(User.user_id == 0).first():
		db.session.add(anon_user)
		db.session.commit()
	

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=4000)

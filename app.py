from flask import Flask, render_template, redirect, url_for, flash,request,get_flashed_messages
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user 
from forms import CreatePostForm,RegForm,LogForm,CommentForm
from flask_migrate import Migrate
from datetime import datetime
from flask import abort
from functools import wraps
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app,db,render_as_batch=True)
##CONFIGURE TABLES
login_manager = LoginManager(app)
login_manager.login_view = "login"
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

 
class User(UserMixin,db.Model):
     
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(32),nullable=False)
    email = db.Column(db.String(256),nullable=False,unique=True)
    password = db.Column(db.String(),nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    posts = db.relationship("Post",backref="owner",lazy="dynamic")
    comt = db.relationship("Comment",backref="owner",lazy="dynamic")
    def __repr__(self):
        return f"User is {self.name}"
    def hash(self,word):
        self.password = generate_password_hash(word,salt_length=8,method="pbkdf2:SHA256")
    def check(self,word):
        return check_password_hash(self.password,word)        
class Post(db.Model): 
     
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey("user.id"))
    comt = db.relationship("Comment",backref="commenter",lazy="dynamic")
    def __repr__(self):
        return f"Post is {self.body}"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer,db.ForeignKey("user.id"))
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    
with app.app_context():
    db.create_all()   
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)        
    return decorated_function
    

@app.route('/',methods=["GET"])
def get_all_posts():
    posts = Post.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=["GET","POST"])
def register():
    form = RegForm()
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        new_user = User(name=name,email=email )
        new_user.hash(password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html",form=form)


@app.route('/login',methods=["POST","GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("get_all_posts"))
    form  = LogForm()
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()  
        if user:

            if user.check(password) :
                login_user(user)
                return redirect(url_for("get_all_posts")) 
            flash("Password is incorrect") 
            return render_template("login.html",form=form)
            
        flash("No user found")
        return render_template("login.html",form=form)
            
            

    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["POST","GET"])
def show_post(post_id):
    requested_post = Post.query.get(post_id)
  
    form=CommentForm()
    if request.method == "POST":
        word = request.form.get("comment_text")
        if not current_user.is_authenticated():
            return redirect(url_for("login"))

        comm = Comment(author=current_user.name,body=word,post_id=requested_post.id,user_id=current_user.id)
        db.session.add(comm)
        db.session.commit()
        return redirect(url_for("about"))
        
    return render_template("post.html", post=requested_post,form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=["POST","GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = Post(
            author=current_user.name,
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            owner=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = Post.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = Post.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True)

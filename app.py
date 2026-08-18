from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///blog.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author = db.relationship("User", backref="posts")

with app.app_context():
    db.create_all()

def logged_in():
    return "user_id" in session

@app.route("/")
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("index.html", posts=posts)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Username and password are required.")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for("register"))
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"].strip()).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))
    posts = Post.query.filter_by(author_id=session["user_id"]).order_by(Post.created_at.desc()).all()
    return render_template("dashboard.html", posts=posts)

@app.route("/post/new", methods=["GET", "POST"])
def new_post():
    if not logged_in():
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()
        if title and content:
            db.session.add(Post(title=title, content=content, author_id=session["user_id"]))
            db.session.commit()
            return redirect(url_for("dashboard"))
    return render_template("post_form.html", post=None)

@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
def edit_post(post_id):
    if not logged_in():
        return redirect(url_for("login"))
    post = Post.query.get_or_404(post_id)
    if post.author_id != session["user_id"]:
        return "Forbidden", 403
    if request.method == "POST":
        post.title = request.form["title"].strip()
        post.content = request.form["content"].strip()
        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("post_form.html", post=post)

@app.route("/post/<int:post_id>/delete", methods=["POST"])
def delete_post(post_id):
    if not logged_in():
        return redirect(url_for("login"))
    post = Post.query.get_or_404(post_id)
    if post.author_id != session["user_id"]:
        return "Forbidden", 403
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)


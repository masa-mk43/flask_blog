# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flaskext.markdown import Markdown
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os
import uuid

app = Flask(__name__)
Markdown(app)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 画像アップロード設定
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB制限

# アップロードフォルダが存在しなければ作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# モデル定義
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 管理者認証デコレータ
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('管理者ログインが必要です', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ルート設定
@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post_detail.html', post=post)

# 管理者ログイン
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('ログインしました', 'success')
            return redirect(url_for('admin_dashboard'))
        
        flash('ユーザー名またはパスワードが間違っています', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('user_id', None)
    flash('ログアウトしました', 'info')
    return redirect(url_for('index'))

# 管理者ダッシュボード
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin/dashboard.html', posts=posts)

# 記事投稿
@app.route('/admin/post/new', methods=['GET', 'POST'])
@admin_required
def admin_new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('タイトルと内容を入力してください', 'danger')
            return render_template('admin/post_form.html')
        
        # 画像アップロード処理
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # ファイル名の衝突を避けるためにUUIDを使用
                filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_filename = filename
        
        post = Post(title=title, content=content, image_filename=image_filename)
        db.session.add(post)
        db.session.commit()
        
        flash('記事を投稿しました', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin/post_form.html')

# 記事編集
@app.route('/admin/post/edit/<int:post_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('タイトルと内容を入力してください', 'danger')
            return render_template('admin/post_form.html', post=post)
        
        # 画像アップロード処理
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                # 古い画像があれば削除
                if post.image_filename:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                # 新しい画像を保存
                filename = str(uuid.uuid4()) + '_' + secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                post.image_filename = filename
        
        post.title = title
        post.content = content
        db.session.commit()
        
        flash('記事を更新しました', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template('admin/post_form.html', post=post)

# 記事削除
@app.route('/admin/post/delete/<int:post_id>', methods=['POST'])
@admin_required
def admin_delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # 投稿に関連する画像も削除
    if post.image_filename:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(post)
    db.session.commit()
    
    flash('記事を削除しました', 'info')
    return redirect(url_for('admin_dashboard'))

# 初期管理者ユーザー作成（初回実行時のみ）
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.count() > 0:
        flash('セットアップは既に完了しています', 'info')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('ユーザー名とパスワードを入力してください', 'danger')
            return render_template('admin/setup.html')
        
        user = User(username=username)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('管理者アカウントを作成しました。ログインしてください。', 'success')
        return redirect(url_for('admin_login'))
        
    return render_template('admin/setup.html')

# アップロードされた画像を提供するルート
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
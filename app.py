from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'kerudung123'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'db.sqlite')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'img')
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
with open(DB_PATH, 'a'):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ===================== MODELS =====================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # admin / user

class Produk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    jenis_kain = db.Column(db.String(100), nullable=False)
    warna = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.Integer, nullable=False)
    deskripsi = db.Column(db.Text)
    gambar = db.Column(db.String(100))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produk_id = db.Column(db.Integer, db.ForeignKey('produk.id'), nullable=False)
    produk = db.relationship('Produk', backref=db.backref('orders', lazy=True))
    nama_pemesan = db.Column(db.String(100), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    total_harga = db.Column(db.Integer, nullable=False)
    warna_dipilih = db.Column(db.String(100), nullable=False)

# ===================== AUTH =====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===================== ROUTES =====================

@app.route('/')
def index():
    produk = Produk.query.all()
    total_pesanan = db.session.query(db.func.sum(Order.jumlah)).scalar() or 0
    return render_template('index.html', produk=produk, total_pesanan=total_pesanan)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Login gagal!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form.get('role', 'user')
        user = User(username=username, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        flash('Pendaftaran berhasil, silakan login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/produk/tambah', methods=['GET', 'POST'])
@login_required
def tambah_produk():
    if current_user.role != 'admin':
        flash('Hanya admin yang bisa menambahkan produk.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        nama = request.form['nama']
        jenis_kain = request.form['jenis_kain']
        warna = request.form['warna']
        harga = request.form['harga']
        deskripsi = request.form.get('deskripsi', '')
        gambar_file = request.files.get('gambar')

        if not nama or not jenis_kain or not harga or not warna:
            flash('Field wajib tidak boleh kosong!')
            return redirect(url_for('tambah_produk'))

        filename = None
        if gambar_file and gambar_file.filename:
            filename = secure_filename(gambar_file.filename)
            gambar_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        p = Produk(
            nama=nama,
            jenis_kain=jenis_kain,
            warna=warna,
            harga=int(harga),
            deskripsi=deskripsi,
            gambar=filename
        )
        db.session.add(p)
        db.session.commit()
        flash('Produk berhasil ditambahkan!')
        return redirect(url_for('index'))

    return render_template('produk_form.html')

@app.route('/produk/hapus/<int:id>')
@login_required
def hapus_produk(id):
    if current_user.role != 'admin':
        flash('Hanya admin yang bisa menghapus produk.')
        return redirect(url_for('index'))

    p = Produk.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/pesan/<int:id>', methods=['GET', 'POST'])
@login_required
def pesan_produk(id):
    produk = Produk.query.get_or_404(id)
    if request.method == 'POST':
        nama_pemesan = request.form['nama_pemesan']
        jumlah = int(request.form['jumlah'])
        warna_dipilih = request.form['warna']
        total_harga = jumlah * produk.harga

        order = Order(
            produk_id=produk.id,
            nama_pemesan=nama_pemesan,
            jumlah=jumlah,
            total_harga=total_harga,
            warna_dipilih=warna_dipilih
        )
        db.session.add(order)
        db.session.commit()
        flash('Pesanan berhasil disimpan!')
        return redirect(url_for('index'))
    return render_template('pesan_form.html', produk=produk)

@app.route('/pesanan')
@login_required
def daftar_pesanan():
    if current_user.role != 'admin':
        flash('Hanya admin yang bisa melihat daftar pesanan.')
        return redirect(url_for('index'))

    pesanan = Order.query.all()
    return render_template('daftar_pesanan.html', pesanan=pesanan)

# ===================== MAIN =====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Tambah user admin jika belum ada
        if not User.query.filter_by(username='admin').first():
            user = User(username='admin', password=generate_password_hash('admin'), role='admin')
            db.session.add(user)
            db.session.commit()
    app.run(debug=True)
    import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
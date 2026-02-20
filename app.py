import json, os, datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'clave_secreta_muy_segura' # Cambia esto

# --- CONFIGURACIÓN DE CORREO (GMAIL) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tu-correo@gmail.com'
app.config['MAIL_PASSWORD'] = 'tu-contraseña-de-aplicacion' # No es tu clave normal
mail = Mail(app)

DATA_DIR = 'data'
REGISTROS_FILE = os.path.join(DATA_DIR, 'registros.json')
USUARIOS_FILE = os.path.join(DATA_DIR, 'usuarios.json')

# Crear carpeta y archivos si no existen
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
if not os.path.exists(USUARIOS_FILE):
    with open(USUARIOS_FILE, 'w') as f: json.dump([{"username": "admin", "pass": "123"}, {"username": "empleado1", "pass": "123"}], f)
if not os.path.exists(REGISTROS_FILE):
    with open(REGISTROS_FILE, 'w') as f: json.dump([], f)

# --- GESTIÓN DE SESIONES ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id): self.id = id

@login_manager.user_loader
def load_user(user_id): return User(user_id)

def leer_json(archivo):
    with open(archivo, 'r') as f: return json.load(f)

def guardar_json(archivo, datos):
    with open(archivo, 'w') as f: json.dump(datos, f, indent=4)

# --- RUTAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form['username']
        pass_input = request.form['password']
        usuarios = leer_json(USUARIOS_FILE)
        if any(u['username'] == user_input and u['pass'] == pass_input for u in usuarios):
            login_user(User(user_input))
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos')
    return render_template('login.html')

@app.route('/')
@login_required
def index():
    return render_template('index.html', usuario=current_user.id)

@app.route('/update-location', methods=['POST'])
@login_required
def update_location():
    data = request.json
    registros = leer_json(REGISTROS_FILE)
    nuevo = {
        "usuario": current_user.id,
        "lat": data['lat'],
        "lon": data['lon'],
        "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    registros.append(nuevo)
    guardar_json(REGISTROS_FILE, registros)
    return jsonify({"status": "Ubicación guardada"})

@app.route('/monitor')
@login_required
def monitor():
    registros = leer_json(REGISTROS_FILE)
    return render_template('monitor.html', registros=registros)

@app.route('/send-reminders')
def send_reminders():
    # Esta ruta la llamarás con un Cron Job a las 8 AM
    msg = Message("¡Inicia tu turno!", sender=app.config['MAIL_USERNAME'], recipients=["empleado1@gmail.com"])
    msg.body = "Buenos días. Por favor entra a la App y presiona 'Iniciar Turno'."
    mail.send(msg)
    return "Correos enviados"

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
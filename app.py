import json, os, datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import threading
# Librería para la tarea automática a las 8 AM
from apscheduler.schedulers.background import BackgroundScheduler
import socket
socket.AddressFamily = socket.AF_INET # Fuerza el uso de IPv4
app = Flask(__name__)
app.secret_key = 'clave_secreta_muy_segura' 

# --- CONFIGURACIÓN DE CORREO (GMAIL) --- xddd
app.config['MAIL_SERVER'] = 'smtp-relay.gmail.com' # Versión relay (más permisiva)
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'hiram060220@gmail.com'
app.config['MAIL_PASSWORD'] = 'mcgc unmv wkci dbrr'
mail = Mail(app)

DATA_DIR = 'data'
REGISTROS_FILE = os.path.join(DATA_DIR, 'registros.json')
USUARIOS_FILE = os.path.join(DATA_DIR, 'usuarios.json')

# --- INICIALIZACIÓN DE ARCHIVOS ---
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

if not os.path.exists(USUARIOS_FILE):
    with open(USUARIOS_FILE, 'w') as f:
        json.dump([
            {"username": "admin", "pass": "123", "email": "admin@test.com"},
            {"username": "empleado1", "pass": "123", "email": "empleado1@test.com"}
        ], f, indent=4)

if not os.path.exists(REGISTROS_FILE) or os.stat(REGISTROS_FILE).st_size == 0:
    with open(REGISTROS_FILE, 'w') as f:
        json.dump([], f)

# --- GESTIÓN DE SESIONES ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id): self.id = id

@login_manager.user_loader
def load_user(user_id): return User(user_id)

def leer_json(archivo):
    try:
        if not os.path.exists(archivo) or os.stat(archivo).st_size == 0:
            return []
        with open(archivo, 'r') as f:
            return json.load(f)
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        return []

def guardar_json(archivo, datos):
    with open(archivo, 'w') as f:
        json.dump(datos, f, indent=4)

def enviar_recordatorio_automatizado():
    with app.app_context():
        try:
            usuarios = leer_json(USUARIOS_FILE)
            registros = leer_json(REGISTROS_FILE)
            hoy = datetime.datetime.now().strftime("%Y-%m-%d")
            quienes_registraron = {r['usuario'] for r in registros if r.get('fecha') == hoy}
            
            destinatarios = list(set([u['email'] for u in usuarios if u['username'] != 'admin' and u['username'] not in quienes_registraron]))

            if not destinatarios:
                return

            # Abrimos una sola conexión para todos los correos
            with mail.connect() as conn:
                for email in destinatarios:
                    msg = Message("⚠️ Recordatorio", 
                                  sender=app.config['MAIL_USERNAME'], 
                                  recipients=[email])
                    msg.body = "Hola, no olvides registrar tu entrada hoy."
                    conn.send(msg)
                    print(f"✅ Enviado individual a: {email}")

        except Exception as e:
            print(f"❌ Error de red: {e}")




scheduler = BackgroundScheduler(daemon=True)
# Ajustar hora aquí (hour=8, minute=0)
scheduler.add_job(enviar_recordatorio_automatizado, 'cron', hour=8, minute=0)
scheduler.start()

# --- RUTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_input = request.form['username']
        pass_input = request.form['password']
        usuarios = leer_json(USUARIOS_FILE)
        
        if any(u['username'] == user_input and u['pass'] == pass_input for u in usuarios):
            login_user(User(user_input))
            if user_input == 'admin':
                return redirect(url_for('monitor'))
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
    ahora = datetime.datetime.now()
    
    nuevo = {
        "usuario": current_user.id,
        "lat": data['lat'],
        "lon": data['lon'],
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora": ahora.strftime("%H:%M:%S")
    }
    registros.append(nuevo)
    guardar_json(REGISTROS_FILE, registros)
    return jsonify({"status": "OK"})

@app.route('/monitor')
@login_required
def monitor():
    if current_user.id != 'admin':
        return redirect(url_for('index'))
    
    usuarios = leer_json(USUARIOS_FILE)
    todos_registros = leer_json(REGISTROS_FILE)
    hoy = datetime.datetime.now().strftime("%Y-%m-%d")
    
    asistencia = []
    quienes_registraron_hoy = set()
    
    for reg in todos_registros:
        hora_reg = reg.get('hora', '00:00:00')
        es_retardo = hora_reg > "08:30:00"
        
        asistencia.append({
            "usuario": reg.get('usuario', 'S/N'),
            "fecha": reg.get('fecha', 'S/F'),
            "hora": hora_reg,
            "status": "RETARDO" if es_retardo else "PUNTUAL"
        })
        
        if reg.get('fecha') == hoy:
            quienes_registraron_hoy.add(reg.get('usuario'))

    activos = []
    faltantes = []
    
    for u in usuarios:
        if u['username'] == 'admin': continue
        reg_user = [r for r in todos_registros if r['usuario'] == u['username']]
        if reg_user:
            activos.append(reg_user[-1])
        if u['username'] not in quienes_registraron_hoy:
            faltantes.append(u['username'])

    return render_template('monitor.html', 
                           asistencia=asistencia, 
                           activos=activos, 
                           faltantes=faltantes)

import threading

@app.route('/send-reminders')
@login_required
def send_reminders():
    # Lanzamos el proceso en un hilo separado
    proceso = threading.Thread(target=enviar_recordatorio_automatizado)
    proceso.start()
    return "El proceso de recordatorios se está ejecutando en segundo plano. Revisa los logs para ver el estado."

@app.route('/reporte-pdf')
@login_required
def reporte_pdf():
    registros = leer_json(REGISTROS_FILE)
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setTitle("Reporte de Asistencia Maestros")
    
    p.drawString(100, 750, f"REPORTE DE ASISTENCIA - GENERADO: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p.line(100, 745, 520, 745)
    
    y = 710
    p.drawString(100, y, "Maestro")
    p.drawString(200, y, "Fecha")
    p.drawString(300, y, "Hora")
    p.drawString(400, y, "Estado")
    y -= 25
    
    stats = {}
    
    for r in registros:
        hora = r.get('hora', '00:00:00')
        estado = "RETARDO" if hora > "08:30:00" else "PUNTUAL"
        p.drawString(100, y, str(r.get('usuario', 'S/N')))
        p.drawString(200, y, str(r.get('fecha', 'S/F')))
        p.drawString(300, y, str(hora))
        p.drawString(400, y, estado)
        
        if estado == "RETARDO":
            usr = r.get('usuario', 'S/N')
            stats[usr] = stats.get(usr, 0) + 1
        
        y -= 15
        if y < 80: 
            p.showPage()
            y = 750

    y -= 40
    p.drawString(100, y, "RESUMEN TOTAL DE RETARDOS ACUMULADOS:")
    p.line(100, y-5, 380, y-5)
    y -= 25
    for user, count in stats.items():
        p.drawString(120, y, f"• {user}: {count} retardos.")
        y -= 15

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="reporte_asistencia.pdf", mimetype='application/pdf')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_input = request.form['username']
        pass_input = request.form['password']
        email_input = request.form['email']
        
        usuarios = leer_json(USUARIOS_FILE)
        
        # Validar si el usuario ya existe
        if any(u['username'] == user_input for u in usuarios):
            flash('El nombre de usuario ya está en uso.')
            return redirect(url_for('register'))
        
        # Crear nuevo usuario y guardar
        nuevo_usuario = {
            "username": user_input,
            "pass": pass_input,
            "email": email_input
        }
        usuarios.append(nuevo_usuario)
        guardar_json(USUARIOS_FILE, usuarios)
        
        flash('Registro exitoso. Ahora puedes iniciar sesión.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)
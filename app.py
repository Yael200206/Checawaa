from flask import Flask, render_template, request, jsonify
from geopy.distance import geodesic
import datetime

app = Flask(__name__)

# CONFIGURACIÓN: Cambia esto por las coordenadas de tu obra/oficina
COORD_OFICINA = (21.942237, -102.247334) 
RADIO_PERMITIDO = 100 # metros

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check-location', methods=['POST'])
def check_location():
    data = request.json
    user_coords = (data['lat'], data['lon'])
    
    # Cálculo de distancia
    distancia = geodesic(COORD_OFICINA, user_coords).meters
    status = "DENTRO" if distancia <= RADIO_PERMITIDO else "FUERA"
    
    # Aquí podrías guardar en Google Sheets o DB
    print(f"Usuario: {data['user']} | Status: {status} | Distancia: {distancia:.2f}m")
    
    return jsonify({
        "status": status,
        "distancia": round(distancia, 2),
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
    })

if __name__ == '__main__':
    app.run(debug=True)
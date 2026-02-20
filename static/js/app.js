const startBtn = document.getElementById('start-btn');
const statusText = document.getElementById('status');
const distText = document.getElementById('distancia');

startBtn.addEventListener('click', () => {
    startBtn.disabled = true;
    startBtn.innerText = "Turno Activo";

    if (navigator.geolocation) {
        // watchPosition rastrea el movimiento
        navigator.geolocation.watchPosition(sendLocation, handleError, {
            enableHighAccuracy: true,
            maximumAge: 0
        });
    } else {
        alert("Tu celular no soporta GPS");
    }
});

function sendLocation(position) {
    const coords = {
        lat: position.coords.latitude,
        lon: position.coords.longitude,
        user: "Empleado_01" // Esto lo podrías sacar de un login
    };

    fetch('/check-location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(coords)
    })
    .then(res => res.json())
    .then(data => {
        statusText.innerText = data.status;
        distText.innerText = data.distancia;
        
        // Cambiar color si se sale
        const card = document.getElementById('status-card');
        card.style.backgroundColor = data.status === "DENTRO" ? "#d4edda" : "#f8d7da";
    });
}

function handleError(err) {
    console.warn('ERROR(' + err.code + '): ' + err.message);
}
function iniciarRastreo() {
    // Primera ejecución
    obtenerYEnviar();
    
    // Intervalo: 50 minutos = 50 * 60 * 1000 ms
    setInterval(obtenerYEnviar, 3000000); 
}

function obtenerYEnviar() {
    navigator.geolocation.getCurrentPosition((pos) => {
        fetch('/update-location', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                lat: pos.coords.latitude,
                lon: pos.coords.longitude
            })
        });
    }, null, { enableHighAccuracy: true });
}
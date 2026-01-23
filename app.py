import os
import requests
from flask import Flask, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# URL copiée de ta capture d'écran (on ajoute /logs.json à la fin)
FIREBASE_URL = "https://aquaguard-e5ecf-default-rtdb.firebaseio.com/logs.json"

@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'index.html')

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        
        # Vérification de la clé API [cite: 3, 14]
        if not data or data.get('api_key') != "AquaGuard_Secret_Key_2026":
            return {"error": "Unauthorized"}, 401

        # Préparation des données [cite: 10, 11, 14]
        f_up = float(data.get('flow_up', 0))
        f_down = float(data.get('flow_down', 0))
        
        payload = {
            "flow_up": f_up,
            "flow_down": f_down,
            "status": "FUITE" if f_up > (f_down + 1.0) else "NORMAL",
            "timestamp": {".sv": "timestamp"} # Heure automatique Firebase
        }

        # Envoi direct sans certificat lourd
        r = requests.post(FIREBASE_URL, json=payload)

        if r.status_code == 200:
            print(f"✅ Succès: Amont {f_up} L/min")
            return {"status": "success"}, 200
        else:
            return {"error": r.text}, 500

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

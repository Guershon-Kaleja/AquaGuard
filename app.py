from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import os

app = Flask(__name__)
CORS(app)  # Indispensable pour que le navigateur accepte les requêtes

# 1. INITIALISATION FIREBASE
# Vérifiez que le fichier serviceAccountKey.json est bien dans le dossier AquaGuard
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Connexion à Firebase réussie !")
except Exception as e:
    print(f"❌ Erreur d'initialisation Firebase : {e}")

# CONFIGURATION
API_KEY_ESP32 = "AquaGuard_Secret_Key_2026"
SEUIL_FUITE = 0.5 

# --- ROUTE POUR AFFICHER LE DASHBOARD ---
@app.route('/')
def serve_dashboard():
    # Envoie le fichier index.html situé au même niveau que app.py
    return send_from_directory('.', 'index.html')

# --- ROUTE POUR RECEVOIR LES DONNÉES (ESP32) ---
@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()

        # Sécurité
        if not data or data.get('api_key') != API_KEY_ESP32:
            return jsonify({"message": "Accès non autorisé"}), 401

        flow_up = float(data.get('flow_up', 0))
        flow_down = float(data.get('flow_down', 0))
        
        difference = abs(flow_up - flow_down)
        status = "FUITE" if difference > SEUIL_FUITE else "NORMAL"

        document = {
            "flow_up": flow_up,
            "flow_down": flow_down,
            "difference": round(difference, 2),
            "status": status,
            "timestamp": firestore.SERVER_TIMESTAMP 
        }

        # Enregistrement dans Firestore
        db.collection('logs').add(document)
        print(f"📡 Données reçues : Up={flow_up} | Down={flow_down} | Status={status}")
        
        return jsonify({"status": "success", "leak_detected": status == "FUITE"}), 201

    except Exception as e:
        print(f"❌ Erreur POST : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# --- ROUTE POUR LIRE LE DERNIER STATUT (OPTIONNEL POUR LE DASHBOARD) ---
@app.route('/api/status', methods=['GET'])
def get_latest_status():
    try:
        docs = db.collection('logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).stream()
        
        result = {}
        for doc in docs:
            result = doc.to_dict()
            if 'timestamp' in result and result['timestamp'] is not None:
                result['timestamp'] = result['timestamp'].isoformat()
        
        if not result:
            return jsonify({"message": "Aucune donnée"}), 404
            
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Écoute sur toutes les interfaces réseau (0.0.0.0) sur le port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
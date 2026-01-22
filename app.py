import os
import json
import firebase_admin
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from firebase_admin import credentials, firestore

# 1. FORCER LE MODE REST (Consomme moins de RAM, évite les erreurs gRPC sur Render)
os.environ["GOOGLE_CLOUD_FIRESTORE_FORCE_REST"] = "true"

app = Flask(__name__)
CORS(app)

# 2. INITIALISATION FIREBASE
# On essaie d'abord de lire la clé depuis la variable d'environnement (plus sûr)
# Sinon on cherche le fichier local
if not firebase_admin._apps:
    try:
        firebase_json = os.environ.get("FIREBASE_CONFIG_JSON")
        if firebase_json:
            # Charger la clé depuis la variable Render (avec les accolades { })
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialisé via Variable d'Environnement")
        elif os.path.exists("serviceAccountKey.json"):
            # Charger la clé depuis le fichier si pas de variable
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialisé via fichier JSON")
        else:
            print("❌ ERREUR : Aucune configuration Firebase trouvée !")
    except Exception as e:
        print(f"❌ ERREUR INITIALISATION : {e}")

db = firestore.client()

# --- ROUTES ---

@app.route('/')
def serve_dashboard():
    """Affiche ton interface index.html"""
    return send_from_directory('.', 'index.html')

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    """Reçoit les données de l'ESP32 ou du test PowerShell"""
    try:
        data = request.get_json()
        if not data:
            return {"error": "JSON vide"}, 400

        # Vérification de la clé API sécurisée
        if data.get('api_key') != "AquaGuard_Secret_Key_2026":
            return {"error": "Clé API invalide"}, 401

        # Récupération et conversion des données
        f_up = float(data.get('flow_up', 0))
        f_down = float(data.get('flow_down', 0))
        
        # Calcul du statut (Fuite si Amont > Aval + 1.0 L/min)
        status = "FUITE" if f_up > (f_down + 1.0) else "NORMAL"

        # Création du document pour Firestore
        document = {
            "flow_up": f_up,
            "flow_down": f_down,
            "status": status,
            "timestamp": firestore.SERVER_TIMESTAMP
        }

        # Écriture dans la collection 'logs'
        db.collection('logs').add(document)
        
        print(f"📡 Donnée enregistrée : Amont={f_up}, Aval={f_down}, Statut={status}")
        return {"status": "success", "message": "Données envoyées à Firebase"}, 200

    except Exception as e:
        print(f"❌ ERREUR LORS DE L'ENREGISTREMENT : {e}")
        return {"error": str(e)}, 500

# --- LANCEMENT ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

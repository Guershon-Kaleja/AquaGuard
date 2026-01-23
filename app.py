import os
import firebase_admin
from flask import Flask, request, send_from_directory
from flask_cors import CORS
from firebase_admin import credentials, firestore

# Force le mode REST pour éviter que Render ne crash par manque de RAM
os.environ["GOOGLE_CLOUD_FIRESTORE_FORCE_REST"] = "true"

app = Flask(__name__)
CORS(app)

# INITIALISATION SANS FICHIER JSON
if not firebase_admin._apps:
    try:
        # Récupération des variables depuis Render
        proj_id = os.environ.get("FIREBASE_PROJECT_ID")
        client_email = os.environ.get("FIREBASE_CLIENT_EMAIL")
        private_key = os.environ.get("FIREBASE_PRIVATE_KEY")

        if private_key and client_email and proj_id:
            # Correction automatique des sauts de ligne (\n)
            if "\\n" in private_key:
                private_key = private_key.replace("\\n", "\n")
            
            # Reconstruction du certificat en mémoire
            cred_dict = {
                "type": "service_account",
                "project_id": proj_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ CONNEXION FIREBASE RÉUSSIE !")
        else:
            print("❌ ERREUR : Variables d'environnement manquantes sur Render")
    except Exception as e:
        print(f"❌ ERREUR INITIALISATION : {e}")

db = firestore.client()

@app.route('/')
def serve_dashboard():
    return send_from_directory('.', 'index.html')

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        if not data or data.get('api_key') != "AquaGuard_Secret_Key_2026":
            return {"error": "Clé API invalide"}, 401

        f_up = float(data.get('flow_up', 0))
        f_down = float(data.get('flow_down', 0))
        
        # Enregistrement
        document = {
            "flow_up": f_up,
            "flow_down": f_down,
            "status": "FUITE" if f_up > (f_down + 1.0) else "NORMAL",
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        
        db.collection('logs').add(document)
        return {"status": "success"}, 200
    except Exception as e:
        print(f"❌ ERREUR DATA : {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

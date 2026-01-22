import os
os.environ["GOOGLE_CLOUD_FIRESTORE_FORCE_REST"] = "true"
from flask import Flask, request, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION FIREBASE ---
# Remplace 'aquaguard-e5ecf' par ton ID de projet réel si différent
PROJECT_ID = "aquaguard-e5ecf"

try:
    if not firebase_admin._apps:
        # Vérifie si le fichier JSON existe pour éviter un crash au démarrage
        cert_path = "serviceAccountKey.json"
        if os.path.exists(cert_path):
            cred = credentials.Certificate(cert_path)
            firebase_admin.initialize_app(cred, {
                'projectId': PROJECT_ID
            })
            print("✅ Connexion à Firebase réussie !")
        else:
            print(f"❌ Erreur : Le fichier {cert_path} est introuvable à la racine.")
except Exception as e:
    print(f"❌ Erreur lors de l'initialisation Firebase : {e}")

db = firestore.client()

# --- ROUTES ---

@app.route('/')
def serve_dashboard():
    """Sert l'interface HTML située à la racine."""
    return send_from_directory('.', 'index.html')

@app.route('/api/data', methods=['POST'])
def receive_sensor_data():
    """Reçoit les données de l'ESP32 et les stocke dans Firestore."""
    try:
        data = request.get_json()
        
        if not data:
            return {"error": "JSON manquant"}, 400

        # Vérification de la clé API (doit correspondre au code ESP32)
        # Source : [cite: 3]
        if data.get('api_key') != "AquaGuard_Secret_Key_2026":
            return {"error": "Clé API invalide"}, 401

        # Préparation du document pour Firestore
        # On convertit en float pour s'assurer que ce sont des nombres
        # Source : [cite: 10, 11]
        f_up = float(data.get('flow_up', 0))
        f_down = float(data.get('flow_down', 0))
        
        # Logique de détection de fuite (seuil de 1.0 L/min de différence)
        status = "FUITE" if f_up > (f_down + 1.0) else "NORMAL"

        document = {
            "flow_up": f_up,
            "flow_down": f_down,
            "status": status,
            "timestamp": firestore.SERVER_TIMESTAMP
        }

        # Ajout à la collection 'logs'
        db.collection('logs').add(document)
        
        print(f"📡 Donnée enregistrée : Amont={f_up}, Aval={f_down}, Statut={status}")
        return {"status": "success", "message": "Données enregistrées"}, 200

    except ValueError as ve:
        print(f"❌ Erreur de format (Float) : {ve}")
        return {"error": "Les valeurs de flux doivent être des nombres"}, 400
    except Exception as e:
        print(f"❌ Erreur serveur : {e}")
        return {"error": str(e)}, 500

# --- LANCEMENT ---

if __name__ == '__main__':
    # Render utilise la variable d'environnement PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

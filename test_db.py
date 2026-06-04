# test_prix.py
from models.prix_predictor import PrixPredictor
from database import Session, fetch_annonces
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import random

print("🧪 Test prédicteur de prix...")

db = Session()
annonces = fetch_annonces(db)
db.close()

# Si pas assez de données réelles, on génère du fictif avec du bruit
if len(annonces) < 10:
    print(f"⚠️ Seulement {len(annonces)} annonce(s) en BD")
    print("→ Génération de données fictives avec bruit pour test réaliste...")
    
    villes = ['Yaoundé', 'Douala', 'Bafoussam']
    categories = ['studio', 'appartement', 'villa', 'chambre']
    transactions = ['location', 'vente']
    
    random.seed(42)
    annonces_fictives = []
    
    for i in range(200):  # 200 au lieu de 30 = plus fiable
        ville = random.choice(villes)
        cat = random.choice(categories)
        trans = random.choice(transactions)
        surface = random.randint(15, 300)
        chambres = random.randint(1, 6)
        meuble = random.choice([True, False])
        
        # Prix réaliste + bruit gaussien pour éviter R²=1.00 parfait
        base = 50000 if trans == 'location' else 5000000
        prix = base + (surface * 1000) + (chambres * 20000)
        if meuble: prix *= 1.2
        if ville == 'Douala': prix *= 1.1
        prix += random.gauss(0, 40000)  # bruit de 40k F CFA
        
        annonces_fictives.append({
            'id': i + 1,
            'prix': max(30000, round(prix)),  # prix min 30k
            'surface_m2': surface,
            'nb_chambres': chambres,
            'meuble': meuble,
            'ville': ville,
            'categorie': cat,
            'type_transaction': trans
        })
    annonces = annonces_fictives

# Séparation Train 80% / Test 20%
x = annonces
y =  [a['prix'] for a in annonces]
X_train, X_test, y_train, y_test = train_test_split(
    x, y, 
    test_size=0.2, 
    random_state=42
)

print(f"📊 Dataset: {len(X_train)} train / {len(X_test)} test")

# Entraînement
print("\n🧠 Entraînement du modèle...")
predictor = PrixPredictor()
predictor.entrainer(X_train)

if not predictor.est_entraine:
    print("❌ Modèle non entraîné")
    exit()

print("✅ Modèle entraîné !")

# Évaluation sur Test Set
   # Évaluation sur Test Set
y_pred = []
for a in X_test:
    prix_pred = predictor.predire_prix(**a)  # **a au lieu de a
    y_pred.append(prix_pred)

    r2_test = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    print(f"\n📈 Résultats sur données JAMAIS vues:")
    print(f"Score R² Test: {r2_test:.3f}")
    print(f"Erreur Moyenne MAE: {mae:,.0f} F CFA")
# Test sur 3 cas concrets Douala
print("\n🧪 Tests de prédiction de prix:\n")
cas_test = [
    {'desc': 'Studio meublé à Douala (25m², 1 ch)', 'ville': 'Douala', 'categorie': 'studio', 'surface_m2': 25, 'nb_chambres': 1, 'meuble': True, 'type_transaction': 'location'},
    {'desc': 'Appart 3 chambres Douala (120m²)', 'ville': 'Douala', 'categorie': 'appartement', 'surface_m2': 120, 'nb_chambres': 3, 'meuble': False, 'type_transaction': 'location'},
    {'desc': 'Villa 4 chambres Douala (250m²)', 'ville': 'Douala', 'categorie': 'villa', 'surface_m2': 250, 'nb_chambres': 4, 'meuble': True, 'type_transaction': 'vente'}
]

for cas in cas_test:
    resultat = predictor.predire_prix(cas)
    print(f"{cas['desc']}")
    print(f"→ Prix estimé: {resultat['prix_estime']:,.0f} F CFA")
    print(f"→ Fiabilité: {resultat['fiabilite']}\n")

print("✅ Tests terminés !")
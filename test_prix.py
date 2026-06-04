from models.prix_predictor import PrixPredictor
from database import SessionLocal, fetch_annonces
import random

print("🧪 Test prédicteur de prix...")

predictor = PrixPredictor()

# 1. Ouvre une session MySQL et charge les annonces
db = SessionLocal()
try:
    annonces = fetch_annonces(db)
finally:
    db.close()
    
    prix_list = [a['prix'] for a in annonces if a['prix'] > 0]
if prix_list:
    print(f"Prix min: {min(prix_list):,.0f} F CFA")
    print(f"Prix max: {max(prix_list):,.0f} F CFA")
    print(f"Prix moyen: {sum(prix_list)/len(prix_list):,.0f} F CFA")

quartiers_count = {}
for a in annonces:
    q = a['quartier'] or 'Inconnu'
    quartiers_count[q] = quartiers_count.get(q, 0) + 1

print("Top quartiers avant nettoyage:")
for q, count in sorted(quartiers_count.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f" {q}: {count}")

print(f"Avant nettoyage: {len(annonces)} annonces")
annonces_clean = []
for a in annonces:
    if a['surface_m2'] and a['surface_m2'] > 15:
        prix_m2 = a['prix'] / a['surface_m2']
        # Garde seulement prix réalistes Cameroun: 5k à 2M F/m²
        if 3000 <= prix_m2 <= 3000000:  
            annonces_clean.append(a)
    else:
        # Garde quand même si pas de surface mais prix raisonnable
        if 25000 <= a['prix'] <= 2000000:
            annonces_clean.append(a)

annonces = annonces_clean
print(f"Après nettoyage: {len(annonces)} annonces")

# 2. Fallback données fictives si BD vide
if len(annonces) < 5:
    print(f"⚠️ Seulement {len(annonces)} annonce(s) active(s) en BD")
    print("→ Génération de 200 données fictives pour tester...")
    
    villes = ['Douala', 'Yaoundé']
    categories = ['studio', 'appartement', 'villa']
    quartiers_dla = ['Bonapriso', 'Akwa', 'Bonamoussadi', 'Ndogbong', 'Cité-SIC', 'Makepe']
    quartiers_ydé = ['Bastos', 'Mendong', 'Essos', 'Odza', 'Biyem-Assi']
    
    for i in range(200):
        surface = random.randint(20, 250)
        chambres = random.randint(1, 5)
        meuble = random.choice([True, False])
        ville = random.choice(villes)
        cat = random.choice(categories)
        trans = random.choice(['location', 'vente'])
        quartier = random.choice(quartiers_dla if ville == 'Douala' else quartiers_ydé)
        
        # Prix réaliste Cameroun + effet quartier
        base = 50000 if ville == 'Douala' else 45000
        prix = base + surface*1300 + chambres*28000 + (35000 if meuble else 0)
        
        # Multiplicateurs quartier Douala
        mult_quartier = {'Bonapriso': 1.9, 'Akwa': 1.6, 'Bonamoussadi': 1.2, 'Ndogbong': 0.65, 'Cité-SIC': 0.8, 'Makepe': 1.0}
        prix *= mult_quartier.get(quartier, 1.0)
        
        # Bruit réaliste pour éviter R²=1.00
        prix += random.gauss(0, 70000)
        
        annonces.append({
            'prix': max(35000, prix),
            'surface_m2': surface,
            'nb_chambres': chambres,
            'meuble': meuble,
            'ville': ville,
            'categorie': cat,
            'type_transaction': trans,
            'quartier': quartier
        })

print("🎯 Entraînement du modèle...")
predictor.entrainer(annonces)

# 3. Test seulement si entraîné
if predictor.est_entraine:
    print(f"\n📊 MAE du modèle: {predictor.mae:,.0f} F CFA | R²: OK\n")
    print("\nPrédictions test avec quartiers Douala:")

prix1, min1, max1, fiab1 = predictor.predire_prix(
    surface_m2=24, 
    nb_chambres=1, 
    meuble=False, 
    quartier='Luxe',
    ville='Douala',              # <- Ajouté
    categorie='Appartement',     # <- Ajouté
    type_transaction='location'  # <- Ajouté
)
# print(f"1. Studio 24m² Bonapriso/Luxe → {prix1:,.0f} F CFA | Fourchette: {min1:,.0f} - {max1:,.0f} | Fiabilité: {fiab1}")

# Test 2: Populaire = Ndogbong/Biyem
prix2, min2, max2, fiab2 = predictor.predire_prix(
    surface_m2=24, 
    nb_chambres=1, 
    meuble=False, 
    quartier='Populaire',
    ville='Douala',              
    categorie='Appartement',     
    type_transaction='location'  
)


prix1, min1, max1, fiab1 = predictor.predire_prix(
    'Douala', 'Appartement', 24, 1, False, 'location', 'Luxe'
)
prix2, min2, max2, fiab2 = predictor.predire_prix(
    'Douala', 'Appartement', 24, 1, False, 'location', 'Populaire'
)

print(f"1. Studio 24m² Bonapriso/Luxe → {prix1:,.0f} F CFA | {min1:,.0f} - {max1:,.0f} | {fiab1}")
print(f"2. Studio 24m² Ndogbong/Populaire → {prix2:,.0f} F CFA | {min2:,.0f} - {max2:,.0f} | {fiab2}")
print(f"\nDifférence quartier: {((prix1-prix2)/prix2)*100:+.0f}%")

diff = ((float(prix1) - float(prix2)) / float(prix2)) * 100
print(f"\nDifférence quartier: {diff:+.0f}%")
print("❌ Modèle non entraîné")


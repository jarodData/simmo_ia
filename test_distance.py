# test_distance.py
from models.scoring_distance import ScoringDistance

print("🔄 Test scoring distance...")
scorer = ScoringDistance()

# ── Test calcul distance ─────────────────────
print("\n📊 Test 1 — Calcul de distance Haversine")

points = [
    ('Yaoundé Centre → Bastos',   3.8480, 11.5021, 3.8667, 11.5167),
    ('Yaoundé → Douala',          3.8480, 11.5021, 4.0483, 9.7043),
    ('Même point',                3.8480, 11.5021, 3.8480, 11.5021),
    ('Yaoundé → Bafoussam',       3.8480, 11.5021, 5.4737, 10.4176),
]

for nom, lat1, lon1, lat2, lon2 in points:
    dist = scorer.haversine(lat1, lon1, lat2, lon2)
    print(f"  {nom:<35} : {dist:.1f} km")

# ── Test scoring annonces ────────────────────
print("\n📊 Test 2 — Score de proximité")

# Lieu de référence : Université de Yaoundé I
lat_ref = 3.8667
lon_ref = 11.5021

annonces_test = [
    {'id': 1, 'titre': 'Studio Ngoa-Ekelle (très proche)', 'latitude': 3.8650, 'longitude': 11.5000},
    {'id': 2, 'titre': 'Appart Bastos (2km)',               'latitude': 3.8800, 'longitude': 11.5200},
    {'id': 3, 'titre': 'Villa Biyem-Assi (5km)',            'latitude': 3.8300, 'longitude': 11.4800},
    {'id': 4, 'titre': 'Chambre Melen (8km)',               'latitude': 3.9000, 'longitude': 11.5500},
    {'id': 5, 'titre': 'Appart Douala (250km)',             'latitude': 4.0483, 'longitude': 9.7043},
    {'id': 6, 'titre': 'Sans coordonnées GPS',              'latitude': None,   'longitude': None},
]

scores = scorer.calculer_score(lat_ref, lon_ref, annonces_test)

print(f"\n  Référence : Université de Yaoundé I")
print(f"  ({lat_ref}, {lon_ref})\n")

for annonce, score in zip(annonces_test, scores):
    if annonce['latitude'] and annonce['longitude']:
        dist = scorer.haversine(
            lat_ref, lon_ref,
            annonce['latitude'], annonce['longitude']
        )
        barre = '█' * int(score * 20)
        print(f"  [{barre:<20}] {score:.2f} ({dist:.1f}km) — {annonce['titre']}")
    else:
        print(f"  [{'?'*20}] {score:.2f} (GPS manquant) — {annonce['titre']}")

# ── Test filtre par rayon ────────────────────
print("\n📊 Test 3 — Filtre par rayon de 3km")
proches = scorer.filtrer_par_rayon(lat_ref, lon_ref, annonces_test, rayon_km=3)
print(f"  {len(proches)} annonce(s) dans un rayon de 3km :")
for a in proches:
    print(f"    ✅ {a['titre']}")

print("\n✅ Tests distance terminés !")
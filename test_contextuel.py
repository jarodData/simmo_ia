# test_contextuel.py
from models.scoring_contextuel import ScoringContextuel

print("🔄 Test scoring contextuel...")
scorer = ScoringContextuel()

# ── Test 1 : Géocodage ───────────────────────
print("\n📊 Test 1 — Géocodage de lieux (Nominatim)")
lieux_test = [
    ('Université de Yaoundé I',   'Yaoundé'),
    ('Total Cameroun',             'Douala'),
    ('Marché Mokolo',              'Yaoundé'),
    ('Lieu inexistant xyz123',     'Yaoundé'),
]

for nom, ville in lieux_test:
    print(f"\n  Recherche : '{nom}' à {ville}...")
    result = scorer.geocoder_lieu(nom, ville)
    if result:
        print(f"  ✅ Trouvé  : {result['nom'][:60]}...")
        print(f"     GPS     : {result['latitude']:.4f}, {result['longitude']:.4f}")
    else:
        print(f"  ❌ Introuvable")

# ── Test 2 : Lieux de culte ──────────────────
print("\n\n📊 Test 2 — Recherche lieux de culte")
print("  (Yaoundé centre — rayon 3km)")

religions_test = [
    ('musulman',   'mosquée'),
    ('catholique', 'église catholique'),
    ('protestant', 'église protestante'),
]

lat_yaounde = 3.8667
lon_yaounde = 11.5167

for religion, label in religions_test:
    print(f"\n  Recherche {label}s...")
    lieux = scorer.chercher_lieux_proches(
        lat      = lat_yaounde,
        lon      = lon_yaounde,
        type_lieu= 'place_of_worship',
        religion = religion,
        rayon_km = 3
    )
    if lieux:
        print(f"  ✅ {len(lieux)} {label}(s) trouvé(s) :")
        for l in lieux[:3]:
            print(f"     📍 {l['nom']} — {l['distance_km']} km")
    else:
        print(f"  ⚠️  Aucun(e) {label} trouvé(e) dans ce rayon")

# ── Test 3 : Analyse quartier ────────────────
print("\n\n📊 Test 3 — Analyse d'un quartier")
print("  Quartier Bastos — Yaoundé")

analyse = scorer.analyser_contexte_quartier(
    lat = 3.8800,
    lon = 11.5200
)

if analyse:
    print(f"\n  Services trouvés dans un rayon de 2km :")
    print(f"  🕌 Lieux de culte : {analyse.get('lieux_culte', 0)}")
    print(f"     dont mosquées  : {analyse.get('mosquees', 0)}")
    print(f"     dont églises   : {analyse.get('eglises', 0)}")
    print(f"  🎓 Écoles/Univers.: {analyse.get('ecoles', 0)}")
    print(f"  🏥 Hôpitaux/clinic: {analyse.get('hopitaux', 0)}")
    print(f"  💊 Pharmacies     : {analyse.get('pharmacies', 0)}")
    print(f"  🛒 Marchés/Super. : {analyse.get('marches', 0)}")
    print(f"  🏦 Banques        : {analyse.get('banques', 0)}")
    print(f"  ⭐ Score services : {analyse.get('score_services', 0):.2f}/1.0")
else:
    print("  ⚠️  Analyse indisponible")

print("\n✅ Tests contextuels terminés !")
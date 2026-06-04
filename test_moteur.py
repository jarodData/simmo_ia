# test_moteur.py
from utils.hybrid_engine import MoteurHybride
from database import Session, fetch_annonces

print("🔄 Test moteur hybride complet...")
print("=" * 50)

# Charger les données
db       = Session()
annonces = fetch_annonces(db)
db.close()

print(f"📦 {len(annonces)} annonce(s) chargée(s)")

if len(annonces) == 0:
    print("❌ Aucune annonce — créez des annonces d'abord")
    exit()

# Initialiser et entraîner
moteur = MoteurHybride()
moteur.entrainer(annonces)

# ── Test 1 : Recherche standard ──────────────
print("\n" + "=" * 50)
print("📊 Test 1 — Recherche standard")
print("=" * 50)

requete1 = {
    'ville'          : 'Yaoundé',
    'type_transaction': 'location',
    'budget_max'     : 200000,
    'limite'         : 5,
}

print(f"\n  Critères : {requete1}")
resultats = moteur.recommander(annonces, requete1)

if resultats:
    print(f"\n  ✅ {len(resultats)} résultat(s) :\n")
    for i, r in enumerate(resultats, 1):
        print(f"  {i}. {r['titre']}")
        print(f"     Prix    : {r['prix']:,.0f} F CFA")
        print(f"     Score   : {r['score_final']:.2f} "
              f"(NLP:{r['score_nlp']:.2f} | "
              f"Prix:{r['score_prix']:.2f} | "
              f"Dist:{r['score_distance']:.2f})")
        print(f"     Raison  : {r['raison']}")
        print()
else:
    print("  ⚠️  Aucun résultat")

# ── Test 2 : Différents profils ──────────────
print("=" * 50)
print("📊 Test 2 — Différents profils utilisateurs")
print("=" * 50)

profils = [
    {
        'nom'    : '🎓 Étudiant',
        'criteres': {
            'type_bien'       : 'chambre',
            'type_transaction': 'location',
            'budget_max'      : 80000,
            'nb_chambres'     : 1,
            'limite'          : 3,
        }
    },
    {
        'nom'    : '👨‍👩‍👧 Famille',
        'criteres': {
            'type_bien'       : 'villa',
            'type_transaction': 'location',
            'nb_chambres'     : 3,
            'budget_max'      : 500000,
            'limite'          : 3,
        }
    },
    {
        'nom'    : '💼 Professionnel',
        'criteres': {
            'type_bien'       : 'appartement',
            'type_transaction': 'location',
            'meuble'          : True,
            'budget_max'      : 300000,
            'limite'          : 3,
        }
    },
]

for profil in profils:
    print(f"\n  {profil['nom']} :")
    res = moteur.recommander(annonces, profil['criteres'])
    if res:
        for r in res:
            print(f"    ✅ {r['titre']} — {r['prix']:,.0f} F | Score: {r['score_final']:.2f}")
    else:
        print(f"    ⚠️  Aucun résultat pour ce profil")

print("\n✅ Tests moteur terminés !")
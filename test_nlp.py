# test_nlp.py
from models.nlp_analyser import NLPAnalyser
from generer_annonces_test import generer_annonces_test
from generer_annonces_douala import generer_annonces_douala

print("🔄 Chargement du modèle NLP...")
nlp = NLPAnalyser()

# ── Test 1 : Similarité ──────────────────────
print("\n📊 Test 1 — Similarité entre textes")

# annonces_test = [
#     {'titre': 'Studio meublé à Bastos', 'description': 'Beau studio climatisé avec parking sécurisé'},
#     {'titre': 'Villa à Biyem-Assi',     'description': 'Grande villa avec jardin et piscine'},
#     {'titre': 'Chambre chez habitant',  'description': 'Chambre simple dans résidence calme proche université'},
#     {'titre': 'Appartement 3 pièces',   'description': 'Appartement moderne lumineux avec balcon'},
# ]

annonces_test =   generer_annonces_douala(200)
nlp.entrainer_sur_corpus(annonces_test)
# annonces_test = [
#     {'titre': 'Studio meublé à Bastos', 'description': 'Beau studio climatisé avec parking sécurisé. Idéal pour étudiant célibataire proche université'},
#     {'titre': 'Villa à Biyem-Assi', 'description': 'Grande villa familiale avec jardin, piscine, 4 chambres, salon, cuisine équipée'},
#     {'titre': 'Chambre chez habitant', 'description': 'Chambre simple dans résidence calme proche université. Pour étudiant ou jeune actif'},
#     {'titre': 'Appartement 3 pièces', 'description': 'Appartement familial 3 chambres moderne lumineux avec balcon, cuisine équipée, 2 salles de bain'},
# ]

requetes_test = [
    "studio meublé proche université",
    "villa avec jardin",
    "logement famille avec plusieurs chambres",
]

for requete in requetes_test:
    
    scores = nlp.calculer_similarite(requete, annonces_test)
    resultats = sorted(zip(annonces_test, scores), key=lambda x: x[1], reverse=True)[:5]
    print(f"\n  Requête : '{requete}'")
    for ann , scores in resultats :
        # barre = '█' * int(s * 20)
        # print(f"    [{barre:<20}] {s:.2f} — {a['titre']}")
        score_affiche = min(scores * 2.5 , 0.99)
    # score = nlp.analyser_qualite_description(desc)
    barre = '█' * int(score_affiche * 20)
    print(f"[{barre:<20}] {score_affiche:.2f} — {ann['titre']}")


# ── Test 2 : Qualité description ─────────────
print("\n📊 Test 2 — Qualité des descriptions")

descriptions = [
    "ok",
    "Beau studio",
    "Studio moderne et lumineux situé au quartier Bastos. Entièrement meublé avec cuisine équipée, climatisation et sécurité 24h. Proche de tous commerces.",
    "Villa spacieuse avec jardin, piscine, parking sécurisé, gardien, terrasse, cuisine équipée et climatisation dans tous les pièces.",
]

for desc in descriptions:
    score = nlp.analyser_qualite_description(desc)
    # barre = '█' * int(score * 20)
    # print(f"  [{barre:<20}] {score:.2f} — '{desc[:50]}...'")

    score_affiche = min(score * 2.5 , 0.99)
    # score = nlp.analyser_qualite_description(desc)
    barre = '█' * int(score_affiche * 20)
    print(f"[{barre:<20}] {score_affiche:.2f} — {ann['titre']}")

print("\n✅ Tests NLP terminés !")
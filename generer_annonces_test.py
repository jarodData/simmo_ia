import random

def generer_annonces_test(n=20):
    """Génère n annonces fictives pour tester le NLP"""
    
    quartiers_dla = ['Bonanjo', 'Bastos', 'Makepe', 'Kotto', 'Bonamoussadi', 'Akwa']
    quartiers_yde = ['Bastos', 'Biyem-Assi', 'Odza', 'Mvog-Ada', 'Essos', 'Nkolndongo']
    villes = ['Douala', 'Yaoundé']
    categories = ['Appartement', 'Studio', 'Villa', 'Chambre']
    
    titres = {
        'Studio': ['Studio meublé', 'Studio moderne', 'Petit studio', 'Studio climatisé'],
        'Appartement': ['Appartement 2 pièces', 'Appartement 3 pièces', 'Bel appartement', 'Appartement standing'],
        'Villa': ['Villa avec jardin', 'Belle villa', 'Villa familiale', 'Villa moderne'],
        'Chambre': ['Chambre meublée', 'Chambre chez habitant', 'Grande chambre', 'Chambre climatisée']
    }
    
    descriptions = [
        'Lumineux et calme, proche commerces et transports. Parking sécurisé, gardien 24h.',
        'Moderne et spacieux avec balcon, cuisine équipée, climatisation. Quartier résidentiel.',
        'Idéal famille nombreuse avec plusieurs chambres, grand salon, jardin, piscine.',
        'Proche université et écoles. Meublé, internet wifi, eau chaude. Résidence sécurisée.',
        'Rénové à neuf, standing élevé, terrasse, vue dégagée. Accès facile, parking privé.',
        'Confortable et bien entretenu. Eau et électricité H24, sécurité, voisinage calme.'
    ]
    
    annonces = []
    for i in range(n):
        ville = random.choice(villes)
        quartier = random.choice(quartiers_dla if ville == 'Douala' else quartiers_yde)
        cat = random.choice(categories)
        nb_chambres = random.randint(1, 5) if cat!= 'Studio' else 1
        surface = random.randint(15, 200)
        meuble = random.choice([True, False])
        
        titre = f"{random.choice(titres[cat])} à {quartier}"
        desc = random.choice(descriptions)
        if nb_chambres > 1:
            desc = f"{nb_chambres} chambres. " + desc
        if meuble:
            desc = "Meublé. " + desc
            
        annonce = {
            'titre': titre,
            'description': desc,
            'categorie': cat,
            'ville': ville,
            'quartier': quartier,
            'nb_chambres': nb_chambres,
            'surface_m2': surface,
            'meuble': meuble,
            'type_transaction': 'Location'
        }
        annonces.append(annonce)
    
    return annonces

# Test
if __name__ == '_main_':
    annonces = generer_annonces_test(20)
    
    from models.nlp_analyser import NLPAnalyser
    
    nlp = NLPAnalyser()
    nlp.entrainer_sur_corpus(annonces) # entraine une fois pour toutes
    
    requetes = [
        "studio meublé proche université",
        "villa avec jardin",
        "logement famille avec plusieurs chambres"
    ]
    
    for req in requetes:
        scores = nlp.calculer_similarite(req, annonces)
        top3 = sorted(zip(annonces, scores), key=lambda x: x[1], reverse=True)[:3]
        
        print(f"\n📍 Requête: '{req}'")
        for ann, score in top3:
            barre = '█' * int(score * 20)
            print(f"[{barre:<20}] {score:.2f} - {ann['titre']}")
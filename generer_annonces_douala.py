import random

def generer_annonces_douala(n=30):
    """Génère n annonces 100% Douala pour entraîner le NLP"""

    quartiers_dla = [
        'Bonanjo', 'Akwa', 'Bali', 'Bonapriso', 'Deido', 'Bonamoussadi',
        'Makepe', 'Kotto', 'Logpom', 'Ndogbong', 'Cité des Palmiers',
        'Bepanda', 'PK8', 'Logbaba', 'Ndokoti', 'Casablanca', 'Dakar',
        'Koukouè', 'New Bell', 'Bessengue'
    ]

    categories = ['Appartement', 'Studio', 'Villa', 'Chambre', 'Duplex']

    titres = {
        'Studio': ['Studio meublé', 'Studio moderne Wouri', 'Petit studio Akwa', 'Studio climatisé Bonapriso'],
        'Appartement': ['Appartement 2 pièces', 'Appartement 3 pièces', 'Appartement standing Bonanjo', 'F3 Meublé'],
        'Villa': ['Villa avec jardin', 'Villa familiale Bonamoussadi', 'Villa duplex Makepe', 'Villa moderne piscine'],
        'Chambre': ['Chambre meublée', 'Chambre chez habitant Akwa', 'Grande chambre Bali', 'Chambre climatisée'],
        'Duplex': ['Duplex standing Bonapriso', 'Duplex meublé Bali', 'Duplex 4 chambres']
    }

    descriptions_dla = [
        'Quartier administratif, proche Plateau, Chambre de commerce. Parking gardien 24h, sécurité renforcée.',
        'Zone résidentielle calme, proche écoles françaises, supermarchés Casino, Carrefour. Climatisation, wifi.',
        'Idéal famille avec enfants, proche écoles bilingues. 4 chambres, grand salon, jardin, piscine, gardien.',
        'Proche Marché Central, Boulevard de la Liberté, transports. Meublé, internet, eau H24, groupe électrogène.',
        'Zone affaires Bonapriso, proche hôtels Sawa, Pullman. Standing élevé, terrasse, vue sur Wouri.',
        'Quartier populaire animé, proche Ndokoti, PK8. Accès facile, bus, taxi. Confortable et sécurisé.',
        'Ville de Douala 3ème, proche hôpital Laquintinie. Moderne, lumineux, balcon, cuisine équipée.',
        'Zone Makepe Dogbong, proche échangeur. Résidence fermée, piscine, salle sport, parking visiteurs.',
        'Proche universite de douala, ENSET, IUT. Meuble, wifi , transport direct. ',
        'Zone etudiante , proche campus, ecoles , bibliotheques. Residence securusee.',
    ]

    annonces = []
    for i in range(n):
        quartier = random.choice(quartiers_dla)
        cat = random.choice(categories)
        nb_chambres = random.randint(1, 5) if cat not in ['Studio', 'Chambre'] else 1
        surface = random.randint(15, 250)
        meuble = random.choice([True, False])
        prix = random.randint(80000, 800000)

        titre = f"{random.choice(titres[cat])} à {quartier}"
        desc = random.choice(descriptions_dla)

        if nb_chambres > 1:
            desc = f"{nb_chambres} chambres, salon, cuisine. " + desc
        if meuble:
            desc = "Entièrement meublé. " + desc
        if 'piscine' in desc and cat!= 'Villa':
            desc = desc.replace('piscine', 'accès piscine résidence')

        annonce = {
            'titre': titre,
            'description': desc,
            'categorie': cat,
            'ville': 'Douala',
            'quartier': quartier,
            'nb_chambres': nb_chambres,
            'surface_m2': surface,
            'meuble': meuble,
            'prix': prix,
            'type_transaction': 'Location'
        }
        annonces.append(annonce)

    return annonces

# Test rapide centré Douala
if __name__ == '_main_':
    annonces = generer_annonces_douala(30)

    from models.nlp_analyser import NLPAnalyser
    nlp = NLPAnalyser()
    nlp.entrainer_sur_corpus(annonces)

    requetes_dla = [
        "appartement meublé Bonapriso",
        "villa avec piscine Bonamoussadi",
        "studio proche Akwa",
        "logement famille 4 chambres Makepe"
    ]

    for req in requetes_dla:
        scores = nlp.calculer_similarite(req, annonces)
        top3 = sorted(zip(annonces, scores), key=lambda x: x[1], reverse=True)[:3]

        print(f"\n📍 Requête: '{req}'")
        for ann, score in top3:
            barre = '█' * int(score * 20)
            print(f"[{barre:<20}] {score:.2f} - {ann['titre']} - {ann['quartier']}")
# ============================================
# MODELE DE RECOMMANDATION — SIMMo IA
# Filtrage hybride :
#   - NLP (TF-IDF + cosinus)
#   - Prediction de prix (Random Forest)
#   - Scoring distance (Haversine)
#   - Scoring popularite
# ============================================
import joblib
import os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import math
import re
import nltk 



class RecommandationNLP:
    """
    Analyse le contenu textuel des annonces
    via TF-IDF et similarite cosinus.
    Fonctionne en francais sans PyTorch.
    """

    
    def __init__(self):
        MOTS_VIDES = [
        'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de',
        'et', 'ou', 'mais', 'donc', 'car', 'ni', 'or',
        'ce', 'cet', 'cette', 'ces', 'mon', 'ma', 'mes',
        'ton', 'ta', 'tes', 'son', 'sa', 'ses', 'notre',
        'votre', 'leur', 'leurs', 'que', 'qui', 'quoi',
        'dont', 'est', 'sont', 'avec', 'sans', 'sur',
        'sous', 'dans', 'par', 'pour', 'en', 'au', 'aux',
        'se', 'si', 'ne', 'pas', 'plus', 'tres', 'bien',
        'il', 'elle', 'ils', 'elles', 'je', 'tu', 'nous',
        'vous', 'on', 'me', 'te', 'lui', 'tout', 'tous',
    ]

        print("Initialisation du modèle NLP TF-IDF...")
        self.vectorizer = TfidfVectorizer(stop_words=MOTS_VIDES, max_features=500)
        self.tfidf_matrix = None
        self.annonces = []
        self.modele_path = 'models/nlp_model.joblib'
        os.makedirs('models', exist_ok=True)
    # def __init__(self):
    #     print("⏳ Initialisation du modèle NLP TF-IDF...")
    #     self.vectorizer = TfidfVectorizer(
    #         ngram_range=(1, 2),
    #         max_features=5000,
    #         strip_accents='unicode',
    #         analyzer='word',
    #         stop_words=None, # on gère nous-mêmes les mots vides
    #         sublinear_tf=True,
    #     )

        self.est_entraine = False
        self.corpus = []
        print(" Modèle NLP prêt!")
        
    def sauvegarder(self):
            """Sauvegarde le vectorizer + matrice + annonces"""
            joblib.dump({
            'vectorizer': self.vectorizer,
            'tfidf_matrix': self.tfidf_matrix,
            'annonces': self.annonces
        }, self.modele_path)
            print(f"Modèle NLP sauvegardé: {self.modele_path}")
    
    def charger(self):
        """Charge le modèle si le fichier existe. Return True si ok"""
        if os.path.exists(self.modele_path):
            data = joblib.load(self.modele_path)
            self.vectorizer = data['vectorizer']
            self.tfidf_matrix = data['tfidf_matrix']
            self.annonces = data['annonces']
            print(f"Modèle NLP chargé: {len(self.annonces)} annonces")
            return True
        return False

    def _nettoyer_texte(self, texte: str) -> str:
        """Nettoie et normalise un texte"""
        if not texte:
            return ''
        texte = texte.lower()
        texte = re.sub(r'[^\w\s]', ' ', texte) # enlève ponctuation
        texte = re.sub(r'\b\d+\b', '', texte) # enlève chiffres isolés
        texte = re.sub(r'(\w+)s\b', r'\1', texte) # singulier: chambres -> chambre
        texte = re.sub(r'\s+', ' ', texte).strip()
        return texte

    def _enrichir_texte(self, annonce: dict) -> str:
        """Enrichit le texte avec tous les attributs de l'annonce"""
        parties = []

        if annonce.get('titre'):
            parties.append(annonce['titre'])
            parties.append(annonce['titre']) # poids x2

        if annonce.get('description'):
            parties.append(annonce['description'])

        if'studio' in annonce.get('categorie','').lower():
            # parties.append(annonce['categorie', ''])
            parties.extend( ['studio']* 3)


        if annonce.get('ville'):
            parties.append(annonce['ville'])
        if annonce.get('quartier'):
            # parties.append(annonce['quartier'])
            parties.extend([annonce['quartier']* 3])

        if annonce.get('meuble'):
            # parties.append('meuble')
            parties.extend(['meuble','meuble','meuble'])
        if annonce.get('nb_chambres'):
            parties.append(f"{annonce['nb_chambres']} chambre")
        if annonce.get('type_transaction'):
            parties.append(annonce['type_transaction'])

        return self._nettoyer_texte(' '.join(parties))

    def entrainer_sur_corpus(self, annonces: list):
        """Entraîne le vectoriseur sur toutes les annonces"""
        if not annonces:
            return

        self.corpus = [self._enrichir_texte(a) for a in annonces]
        textes_valides = [t for t in self.corpus if t.strip()]

        if textes_valides:
            self.vectorizer.fit(textes_valides)
            self.est_entraine = True

    def calculer_similarite(self, texte_requete: str, annonces: list) -> list:
        """Compare la requête avec toutes les annonces"""
        if not texte_requete or not annonces:
            return [0.5] * len(annonces)

        texte_requete = self._nettoyer_texte(texte_requete)
        if not texte_requete:
            return [0.5] * len(annonces)

        textes_annonces = [self._enrichir_texte(a) for a in annonces]

        try:
            tous_textes = [texte_requete] + textes_annonces
            tous_textes = [t if t.strip() else 'vide' for t in tous_textes]

            if not getattr(self,'est_entraine', False):
                self.vectorizer.fit(tous_textes)
                self.est_entraine = True

            matrice = self.vectorizer.transform(tous_textes)
            vecteur_requete = matrice[0]
            vecteurs_annonces = matrice[1:]

            scores = cosine_similarity(vecteur_requete, vecteurs_annonces)[0]
            scores = [float(s) for s in scores]

            # Fallback si tous les scores sont 0
            if max(scores) == 0:
                mots_requete = set(texte_requete.split())
                for i, texte in enumerate(textes_annonces):
                    mots_annonce = set(texte.split())
                    overlap = len(mots_requete & mots_annonce)
                    if len(mots_requete) > 0:
                        scores[i] = min(overlap / len(mots_requete), 0.3)

            return scores

        except Exception as e:
            print(f"Erreur NLP: {e}")
            return [0.5] * len(annonces)

    def analyser_qualite_description(self, description: str) -> float:
        """Score de qualité d'une description"""
        if not description:
            return 0.0

        description = description.lower()
        score_longueur = min(len(description) / 500, 1.0)
        nb_mots = len(description.split())
        score_mots = min(nb_mots / 80, 1.0)

        mots_positifs = [
            'lumineux', 'calme', 'moderne', 'renove', 'parking',
            'securise', 'climatise', 'gardien', 'piscine', 'terrasse',
            'balcon', 'jardin', 'cuisine equipee', 'proche', 'meuble',
            'standing', 'spacieux', 'confortable', 'neuf', 'securite',
            'eau', 'electricite', 'internet', 'wifi',
        ]

        nb_positifs = sum(1 for mot in mots_positifs if mot in description)
        score_positifs = min(nb_positifs / 6, 1.0)
        score_structure = 0.3 if '.' in description or ',' in description else 0.0

        score = (
            score_longueur * 0.30 +
            score_mots * 0.25 +
            score_positifs * 0.35 +
            score_structure * 0.10
        )

        return round(min(score, 1.0), 4)

    def extraire_mots_cles(self, texte: str, n: int = 5) -> list:
        """Extrait les mots clés les plus importants"""
        if not texte:
            return []

        texte_nettoye = self._nettoyer_texte(texte)
        try:
            vecteur = self.vectorizer.transform([texte_nettoye])
            feature_names = self.vectorizer.get_feature_names_out()
            scores = vecteur.toarray()[0]
            indices = scores.argsort()[::-1][:n]
            mots_cles = [feature_names[i] for i in indices if scores[i] > 0]
            return mots_cles
        except Exception:
            return []


class RecommandationPrix:
    def __init__(self):
        self.modele = RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1)
        self.encodeur_ville = LabelEncoder()
        self.encodeur_cat = LabelEncoder()
        self.encodeur_trans = LabelEncoder()
        self.encodeur_quartier = LabelEncoder()
        self.est_entraine = False
        self.mae = 0
        self.score_r2 = 0

        self.dossier_modele = 'simmo_ia/modeles'
        os.makedirs(self.dossier_modele, exist_ok=True)
        self.annonces = [] 

    def group_quartier(self, q):
        q = str(q).lower().strip()
        
        # LUXE
        luxe = ['bonapriso', 'bastos', 'akwa', 'nlongkak', 'kotto', 'logbaba', 
                'mairie', 'plateau joss', 'bonanjo', 'koutaba', 'dragage']
        if any(x in q for x in luxe):
            return 'Luxe'
        
        # MOYEN+
        moyen_plus = ['bonamoussadi', 'makepe', 'essos', 'omnisports', 'deido', 
                    'ndokoti', 'cite sic', 'koula', 'nyalla', 'beedi', 'endef']
        if any(x in q for x in moyen_plus):
            return 'Moyen+'
        
        # MOYEN
        moyen = ['new bell', 'bali', 'village', 'nkololoun', 'bepanda', 'dakar',
                'ndogpassi', 'sodikombo', 'cite des palmiers', 'logpom', 'brazzaville']
        if any(x in q for x in moyen):
            return 'Moyen'
        
        # POPULAIRE
        populaire = ['ndogbong', 'odza', 'biyem', 'mvog-ada', 'nkoldongo', 'mendong',
                    'soa', 'etoug-ebe', 'nsimalen', 'ekoumdoum', 'emana', 'melen',
                    'nkolfou', 'ekounou', 'aze', 'ekoko']
        if any(x in q for x in populaire):
            return 'Populaire'
    
        return 'Moyen' # Par défaut
    ### 3. Multiplicateurs ajustés pour 4 catégories
    MULT = {
        'Luxe': 1.85,      # 400k-500k studio
        'Moyen+': 1.35,    # 250k-300k studio  
        'Moyen': 1.00,     # 180k-220k studio
        'Populaire': 0.65  # 120k-150k studio
    }


    def preparer_features(self, annonces):
        df = pd.DataFrame(annonces)
        df['surface_m2'] = df['surface_m2'].fillna(df['surface_m2'].median() if 'surface_m2' in df.columns else 50)
        df['nb_chambres'] = df['nb_chambres'].fillna(1)
        df['meuble'] = df['meuble'].fillna(False).astype(int)
        df['quartier'] = df['quartier'].fillna('Inconnu').apply(self.group_quartier) # AJOUTÉ
        return df

    def entrainer(self, annonces):
        if len(annonces) < 10:
            print("Pas assez de donnees pour entrainer le modele prix.", len(annonces))
            return

        df = self.preparer_features(annonces)
        df['ville_enc'] = self.encodeur_ville.fit_transform(df['ville'].fillna('Inconnue'))
        df['cat_enc'] = self.encodeur_cat.fit_transform(df['categorie'].fillna('appartement'))
        df['trans_enc'] = self.encodeur_trans.fit_transform(df['type_transaction'].fillna('location'))
        df['quartier_enc'] = self.encodeur_quartier.fit_transform(df['quartier']) # AJOUTÉ

        features = ['surface_m2', 'nb_chambres', 'meuble', 'ville_enc', 'cat_enc', 'trans_enc', 'quartier_enc']
        X = df[features].values
        y = df['prix'].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.modele.fit(X_train, y_train)
        self.est_entraine = True

        y_pred = self.modele.predict(X_test)
        self.mae = np.mean(np.abs(y_test - y_pred))
        self.score_r2 = self.modele.score(X_test, y_test)
        print(f"Modele prix entraine. Score R2: {self.score_r2:.2f} | MAE: {self.mae:,.0f}")

        self.sauvegarder_modele()

    def sauvegarder_modele(self):
        joblib.dump(self.modele, f'{self.dossier_modele}/modele_prix.pkl')
        joblib.dump(self.encodeur_quartier, f'{self.dossier_modele}/enc_quartier.pkl')
        joblib.dump(self.encodeur_ville, f'{self.dossier_modele}/enc_ville.pkl')
        joblib.dump(self.encodeur_cat, f'{self.dossier_modele}/enc_cat.pkl')
        joblib.dump(self.encodeur_trans, f'{self.dossier_modele}/enc_trans.pkl')
        joblib.dump(self.mae, f'{self.dossier_modele}/mae.pkl')
        joblib.dump(self.score_r2, f'{self.dossier_modele}/r2.pkl')

    def charger_modele(self):
        try:
            if not os.path.exists(f'{self.dossier_modele}/modele_prix.pkl'):
                return False
            self.modele = joblib.load(f'{self.dossier_modele}/modele_prix.pkl')
            self.encodeur_quartier = joblib.load(f'{self.dossier_modele}/enc_quartier.pkl')
            self.encodeur_ville = joblib.load(f'{self.dossier_modele}/enc_ville.pkl')
            self.encodeur_cat = joblib.load(f'{self.dossier_modele}/enc_cat.pkl')
            self.encodeur_trans = joblib.load(f'{self.dossier_modele}/enc_trans.pkl')
            self.mae = joblib.load(f'{self.dossier_modele}/mae.pkl')
            self.score_r2 = joblib.load(f'{self.dossier_modele}/r2.pkl')
            self.est_entraine = True
            return True
        except:
            return False

    def predire_prix(self, ville, categorie, surface_m2, nb_chambres, meuble, type_transaction, quartier="Inconnu"):
        if not self.est_entraine:
            return {'prix_estime': None, 'fourchette_min': None, 'fourchette_max': None, 'fiabilite': 'indisponible'}

        try:
            quartier_group = self.group_quartier(quartier)
            ville_enc = self.encodeur_ville.transform([ville])[0] if ville in self.encodeur_ville.classes_ else 0
            cat_enc = self.encodeur_cat.transform([categorie])[0] if categorie in self.encodeur_cat.classes_ else 0
            trans_enc = self.encodeur_trans.transform([type_transaction])[0] if type_transaction in self.encodeur_trans.classes_ else 0
            quartier_enc = self.encodeur_quartier.transform([quartier_group])[0] if quartier_group in self.encodeur_quartier.classes_ else 0

            X = np.array([[surface_m2, nb_chambres, int(meuble), ville_enc, cat_enc, trans_enc, quartier_enc]])
            prix_predit = float(self.modele.predict(X)[0])

            # MULTIPLICATEUR DOUALA - clé pour avoir +200% d'écart
            MULT = {'Luxe': 1.85, 'Moyen+': 1.35, 'Moyen': 1.00, 'Populaire': 0.65, 'Inconnu': 1.00}
            mult = MULT.get(quartier_group, 1.0)
            prix_predit *= mult

            fourchette_min = max(0, prix_predit - self.mae * mult)
            fourchette_max = prix_predit + self.mae * mult

            erreur_rel = self.mae / prix_predit if prix_predit > 0 else 1
            fiabilite = "haute" if erreur_rel < 0.1 else "moyenne" if erreur_rel < 0.2 else "basse"

            return {
                'prix_estime': round(prix_predit, 0),
                'fourchette_min': round(fourchette_min, 0),
                'fourchette_max': round(fourchette_max, 0),
                'fiabilite': fiabilite
            }
        except Exception as e:
            print("Erreur prediction prix:", e)
            return {'prix_estime': None, 'fourchette_min': None, 'fourchette_max': None, 'fiabilite': 'erreur'}


class RecommandationDistance:
    """
    Calcule le score de proximite geographique
    via la formule de Haversine.
    """

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R    = 6371
        lat1 = math.radians(float(lat1))
        lon1 = math.radians(float(lon1))
        lat2 = math.radians(float(lat2))
        lon2 = math.radians(float(lon2))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a    = (math.sin(dlat / 2) ** 2 +
                math.cos(lat1) * math.cos(lat2) *
                math.sin(dlon / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(a))

    def calculer_score(self, lat_user, lon_user, annonces):
        scores = []
        for annonce in annonces:
            lat_a = annonce.get('latitude')
            lon_a = annonce.get('longitude')

            if not lat_a or not lon_a or \
               not lat_user or not lon_user:
                scores.append(0.5)
                continue

            try:
                distance = self.haversine(
                    lat_user, lon_user,
                    float(lat_a), float(lon_a)
                )

                if   distance <= 0.5: score = 1.0
                elif distance <= 1:   score = 0.9
                elif distance <= 2:   score = 0.75
                elif distance <= 3:   score = 0.6
                elif distance <= 5:   score = 0.4
                elif distance <= 10:  score = 0.2
                else:                 score = 0.0

                scores.append(round(score, 4))

            except Exception:
                scores.append(0.5)

        return scores

    def filtrer_par_rayon(self, lat_user, lon_user,
                           annonces, rayon_km=10):
        if not lat_user or not lon_user:
            return annonces

        resultat = []
        for a in annonces:
            if not a.get('latitude') or not a.get('longitude'):
                resultat.append(a)
                continue
            try:
                dist = self.haversine(
                    lat_user, lon_user,
                    float(a['latitude']),
                    float(a['longitude'])
                )
                if dist <= rayon_km:
                    resultat.append(a)
            except Exception:
                resultat.append(a)

        return resultat


class MoteurRecommandation:
    """
    Moteur hybride combinant :
    - NLP        (35% par defaut)
    - Prix       (30% par defaut)
    - Distance   (20% par defaut)
    - Popularite (15% par defaut)
    Les poids sont ajustes dynamiquement selon
    les criteres fournis dans la requete.
    """

    def __init__(self):
        self.nlp      = RecommandationNLP()
        self.prix     = RecommandationPrix()
        self.distance = RecommandationDistance()

    def entrainer(self, annonces):
        print("Entrainement de tous les modeles...")
        self.nlp.entrainer_sur_corpus(annonces)
        self.prix.entrainer(annonces)
        print("Tous les modeles sont prets.")

    def recommander(self, annonces, requete):
        if not annonces:
            return []

        filtrees = self._appliquer_filtres(annonces, requete)

        # Si filtrage trop strict → relache les filtres
        if len(filtrees) < 3:
            filtrees = annonces[:]

        if not filtrees:
            return []

        texte_requete = self._construire_texte(requete)
        scores_nlp    = self.nlp.calculer_similarite(texte_requete, filtrees)
        scores_dist   = self.distance.calculer_score(
            requete.get('latitude'),
            requete.get('longitude'),
            filtrees
        )
        scores_prix   = self._score_prix(filtrees, requete)
        scores_pop    = self._score_popularite(filtrees)

        # Poids dynamiques selon ce que l'utilisateur fournit
        a_budget   = bool(requete.get('budget_max') or requete.get('budget_min'))
        a_position = bool(requete.get('latitude') and requete.get('longitude'))
        a_texte    = bool(requete.get('type_bien') or requete.get('q'))

        if a_position and a_budget:
            poids = {'nlp': 0.25, 'prix': 0.30, 'dist': 0.35, 'pop': 0.10}
        elif a_position:
            poids = {'nlp': 0.20, 'prix': 0.20, 'dist': 0.45, 'pop': 0.15}
        elif a_budget:
            poids = {'nlp': 0.30, 'prix': 0.45, 'dist': 0.10, 'pop': 0.15}
        elif a_texte:
            poids = {'nlp': 0.50, 'prix': 0.20, 'dist': 0.10, 'pop': 0.20}
        else:
            poids = {'nlp': 0.25, 'prix': 0.25, 'dist': 0.25, 'pop': 0.25}

        resultats = []
        for i, annonce in enumerate(filtrees):
            score_final = (
                scores_nlp[i]  * poids['nlp']  +
                scores_prix[i] * poids['prix'] +
                scores_dist[i] * poids['dist'] +
                scores_pop[i]  * poids['pop']
            )

            # Bonus qualite description
            bonus_desc  = self.nlp.analyser_qualite_description(
                annonce.get('description', '')
            ) * 0.05
            score_final = min(score_final + bonus_desc, 1.0)

            prediction = self.prix.predire_prix(
                ville            = annonce.get('ville', ''),
                categorie        = annonce.get('categorie', ''),
                surface_m2       = annonce.get('surface_m2') or 50,
                nb_chambres      = annonce.get('nb_chambres') or 1,
                meuble           = annonce.get('meuble') or False,
                type_transaction = annonce.get('type_transaction', 'location'),
                quartier=annonce.get('quartier', 'Inconnu') ,
            )
      
            photo = annonce.get('photo')
            if photo is None or str(photo) in ('None', 'null', ''):
                photo = None

            resultats.append({
                'id_annonce'      : annonce['id'],
                'titre'           : annonce['titre'],
                'prix'            : float(annonce['prix']),
                'categorie'       : annonce.get('categorie', ''),
                'ville'           : annonce.get('ville', ''),
                'quartier'        : annonce.get('quartier'),
                'photo'           : photo,
                'type_transaction': annonce.get('type_transaction', ''),
                'score_final'     : round(float(score_final), 4),
                'score_nlp'       : round(float(scores_nlp[i]), 4),
                'score_prix'      : round(float(scores_prix[i]), 4),
                'score_distance'  : round(float(scores_dist[i]), 4),
                'score_popularite': round(float(scores_pop[i]), 4),
                'prix_estime'     : prediction.get('prix_estime'),
                'raison'          : self._raison(
                    scores_nlp[i], scores_prix[i],
                    scores_dist[i], annonce
                ),
            })

        resultats.sort(key=lambda x: x['score_final'], reverse=True)
        limite = requete.get('limite', 10)
        return resultats[:limite]

    def _appliquer_filtres(self, annonces, requete):
        filtrees = annonces[:]

        if requete.get('type_transaction'):
            filtrees = [
                a for a in filtrees
                if a.get('type_transaction') ==
                   requete['type_transaction']
            ]
        if requete.get('type_bien'):
            filtrees = [
                a for a in filtrees
                if a.get('categorie') == requete['type_bien']
            ]
        if requete.get('budget_max'):
            filtrees = [
                a for a in filtrees
                if float(a.get('prix', 0)) <=
                   requete['budget_max']
            ]
        if requete.get('budget_min'):
            filtrees = [
                a for a in filtrees
                if float(a.get('prix', 0)) >=
                   requete['budget_min']
            ]
        if requete.get('surface_min'):
            filtrees = [
                a for a in filtrees
                if a.get('surface_m2') and
                   float(a['surface_m2']) >= requete['surface_min']
            ]
        if requete.get('nb_chambres'):
            filtrees = [
                a for a in filtrees
                if a.get('nb_chambres') and
                   int(a['nb_chambres']) >= requete['nb_chambres']
            ]
        if requete.get('ville'):
            ville_lower = requete['ville'].lower()
            filtrees    = [
                a for a in filtrees
                if a.get('ville') and
                   ville_lower in a['ville'].lower()
            ]
        if requete.get('meuble') is True:
            filtrees = [
                a for a in filtrees
                if bool(a.get('meuble'))
            ]

        return filtrees

    def _construire_texte(self, requete):
        parties = []
        if requete.get('type_bien'):
            parties.append(requete['type_bien'])
        if requete.get('ville'):
            parties.append(requete['ville'])
        if requete.get('nb_chambres'):
            parties.append(
                str(requete['nb_chambres']) + ' chambres'
            )
        if requete.get('meuble'):
            parties.append('meuble')
        if requete.get('type_transaction'):
            parties.append(requete['type_transaction'])
        if requete.get('q'):
            parties.append(requete['q'])
        return ' '.join(parties) if parties else 'logement'

    def _score_prix(self, annonces, requete):
        scores     = []
        budget_max = requete.get('budget_max')
        budget_min = requete.get('budget_min')

        # Prix median par categorie comme reference
        prix_medians = {}
        for a in annonces:
            cat  = a.get('categorie', 'autre')
            prix = float(a.get('prix', 0))
            if cat not in prix_medians:
                prix_medians[cat] = []
            prix_medians[cat].append(prix)

        for cat in prix_medians:
            vals = sorted(prix_medians[cat])
            mid  = len(vals) // 2
            prix_medians[cat] = vals[mid]

        for annonce in annonces:
            prix = float(annonce.get('prix', 0))
            cat  = annonce.get('categorie', 'autre')

            if budget_max and budget_min:
                cible = (budget_max + budget_min) / 2
                ecart = abs(prix - cible) / cible if cible else 0
                score = max(0.0, 1.0 - ecart)
            elif budget_max:
                ratio = prix / budget_max if budget_max else 1
                if   ratio <= 0.70: score = 0.9  # tres bon prix
                elif ratio <= 0.85: score = 1.0  # prix ideal
                elif ratio <= 1.00: score = 0.7  # dans le budget
                else:               score = 0.0  # hors budget
            elif budget_min:
                score = 1.0 if prix >= budget_min else 0.3
            else:
                # Sans budget → compare au median de la categorie
                median = prix_medians.get(cat, prix)
                if median > 0:
                    ratio = prix / median
                    score = 1.0 - abs(1.0 - ratio) * 0.5
                    score = max(0.2, min(score, 1.0))
                else:
                    score = 0.5

            scores.append(round(score, 4))

        return scores

    def _score_popularite(self, annonces):
        vues     = [int(a.get('vues', 0)) for a in annonces]
        max_vues = max(vues) if vues and max(vues) > 0 else 1
        return [round(v / max_vues, 4) for v in vues]

    def _raison(self, score_nlp, score_prix, score_dist, annonce):
        raisons = []

        if score_nlp > 0.5:
            raisons.append('correspond a votre recherche')
        if score_prix > 0.7:
            raisons.append('dans votre budget')
        elif score_prix > 0.5:
            raisons.append('prix raisonnable')
        if score_dist > 0.7:
            raisons.append('proche de votre localisation')

        vues = int(annonce.get('vues', 0))
        if vues > 200:
            raisons.append('tres populaire')
        elif vues > 50:
            raisons.append('populaire')

        if annonce.get('meuble'):
            raisons.append('meuble')

        if not raisons:
            raisons.append('suggere pour vous')

        return 'Ce bien ' + ', '.join(raisons) + '.'
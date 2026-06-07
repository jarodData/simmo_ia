# models/recommandation.py — VERSION OPTIMISÉE

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
from functools import lru_cache


class RecommandationNLP:

    MOTS_VIDES = [
        'le','la','les','un','une','des','du','de','et','ou','mais',
        'donc','car','ni','or','ce','cet','cette','ces','mon','ma',
        'mes','ton','ta','tes','son','sa','ses','notre','votre','leur',
        'leurs','que','qui','quoi','dont','est','sont','avec','sans',
        'sur','sous','dans','par','pour','en','au','aux','se','si',
        'ne','pas','plus','tres','bien','il','elle','ils','elles',
        'je','tu','nous','vous','on','me','te','lui','tout','tous',
    ]

    def __init__(self):
        print("Initialisation du modèle NLP TF-IDF...")
        self.vectorizer   = TfidfVectorizer(
            stop_words  = self.MOTS_VIDES,
            max_features= 500,
        )
        self.tfidf_matrix  = None
        self.annonces      = []
        self.modele_path   = 'models/nlp_model.joblib'
        self.est_entraine  = False
        self.corpus        = []

        # OPTIMISATION 1 : cache des textes enrichis
        self._cache_textes = {}

        os.makedirs('models', exist_ok=True)
        print("Modèle NLP prêt!")

    def sauvegarder(self):
        joblib.dump({
            'vectorizer'  : self.vectorizer,
            'tfidf_matrix': self.tfidf_matrix,
            'annonces'    : self.annonces,
        }, self.modele_path)

    def charger(self):
        if os.path.exists(self.modele_path):
            data = joblib.load(self.modele_path)
            self.vectorizer   = data['vectorizer']
            self.tfidf_matrix = data['tfidf_matrix']
            self.annonces     = data['annonces']
            self.est_entraine = True
            print(f"Modèle NLP chargé: {len(self.annonces)} annonces")
            return True
        return False

    def _nettoyer_texte(self, texte: str) -> str:
        if not texte:
            return ''
        texte = texte.lower()
        texte = re.sub(r'[^\w\s]', ' ', texte)
        texte = re.sub(r'\b\d+\b', '', texte)
        texte = re.sub(r'\s+', ' ', texte).strip()
        return texte

    def _enrichir_texte(self, annonce: dict) -> str:
        # OPTIMISATION 2 : cache par id annonce
        annonce_id = annonce.get('id')
        if annonce_id and annonce_id in self._cache_textes:
            return self._cache_textes[annonce_id]

        parties = []
        if annonce.get('titre'):
            parties.extend([annonce['titre'], annonce['titre']])
        if annonce.get('description'):
            parties.append(annonce['description'])
        if 'studio' in annonce.get('categorie', '').lower():
            parties.extend(['studio'] * 3)
        if annonce.get('ville'):
            parties.append(annonce['ville'])
        if annonce.get('quartier'):
            parties.extend([annonce['quartier']] * 3)
        if annonce.get('meuble'):
            parties.extend(['meuble'] * 3)
        if annonce.get('nb_chambres'):
            parties.append(f"{annonce['nb_chambres']} chambre")
        if annonce.get('type_transaction'):
            parties.append(annonce['type_transaction'])

        resultat = self._nettoyer_texte(' '.join(parties))

        if annonce_id:
            self._cache_textes[annonce_id] = resultat
        return resultat

    def entrainer_sur_corpus(self, annonces: list):
        if not annonces:
            return
        self.corpus        = [self._enrichir_texte(a) for a in annonces]
        textes_valides     = [t for t in self.corpus if t.strip()]
        if textes_valides:
            # OPTIMISATION 3 : entraîner + transformer en une passe
            self.tfidf_matrix = self.vectorizer.fit_transform(textes_valides)
            self.est_entraine = True

    def calculer_similarite(self, texte_requete: str, annonces: list) -> list:
        if not texte_requete or not annonces:
            return [0.5] * len(annonces)

        texte_requete = self._nettoyer_texte(texte_requete)
        if not texte_requete:
            return [0.5] * len(annonces)

        textes_annonces = [self._enrichir_texte(a) for a in annonces]

        try:
            tous_textes = [texte_requete] + textes_annonces
            tous_textes = [t if t.strip() else 'vide' for t in tous_textes]

            if not self.est_entraine:
                self.vectorizer.fit(tous_textes)
                self.est_entraine = True

            # OPTIMISATION 4 : transform() au lieu de fit_transform()
            matrice          = self.vectorizer.transform(tous_textes)
            vecteur_requete  = matrice[0]
            vecteurs_annonces= matrice[1:]

            scores = cosine_similarity(vecteur_requete, vecteurs_annonces)[0]
            scores = [float(s) for s in scores]

            if max(scores) == 0:
                mots_requete = set(texte_requete.split())
                for i, texte in enumerate(textes_annonces):
                    mots_annonce = set(texte.split())
                    overlap = len(mots_requete & mots_annonce)
                    if mots_requete:
                        scores[i] = min(overlap / len(mots_requete), 0.3)

            return scores

        except Exception as e:
            print(f"Erreur NLP: {e}")
            return [0.5] * len(annonces)

    def analyser_qualite_description(self, description: str) -> float:
        # OPTIMISATION 5 : cache LRU pour éviter recalcul
        return self._qualite_cached(description)

    @lru_cache(maxsize=1000)
    def _qualite_cached(self, description: str) -> float:
        if not description:
            return 0.0
        description    = description.lower()
        score_longueur = min(len(description) / 500, 1.0)
        nb_mots        = len(description.split())
        score_mots     = min(nb_mots / 80, 1.0)
        mots_positifs  = [
            'lumineux','calme','moderne','renove','parking',
            'securise','climatise','gardien','piscine','terrasse',
            'balcon','jardin','cuisine equipee','proche','meuble',
            'standing','spacieux','confortable','neuf','securite',
        ]
        nb_positifs   = sum(1 for m in mots_positifs if m in description)
        score_positifs = min(nb_positifs / 6, 1.0)
        score_structure= 0.3 if ('.' in description or ',' in description) else 0.0
        score = (
            score_longueur * 0.30 +
            score_mots     * 0.25 +
            score_positifs * 0.35 +
            score_structure* 0.10
        )
        return round(min(score, 1.0), 4)

    def extraire_mots_cles(self, texte: str, n: int = 5) -> list:
        if not texte:
            return []
        try:
            vecteur       = self.vectorizer.transform([self._nettoyer_texte(texte)])
            feature_names = self.vectorizer.get_feature_names_out()
            scores        = vecteur.toarray()[0]
            indices       = scores.argsort()[::-1][:n]
            return [feature_names[i] for i in indices if scores[i] > 0]
        except Exception:
            return []


class RecommandationPrix:

        # MULT séparé selon le type de transaction
    MULT_VENTE = {
        'Luxe'     : 2.50,   # Bonapriso, Akwa, Bonanjo → 80M+
        'Moyen+'   : 1.80,   # Makepe, Deido → 55-65M
        'Moyen'    : 1.20,   # Bali, New Bell → 45-55M
        'Populaire': 0.70,   # Bepanda → 20-25M
    }

    MULT_LOCATION = {
        'Luxe'     : 1.43,   # différence faible entre zones
        'Moyen+'   : 1.49,
        'Moyen'    : 1.00,
        'Populaire': 1.16,
    }

    def __init__(self):
        self.modele           = RandomForestRegressor(
            n_estimators=150, random_state=42, n_jobs=-1
        )
        self.encodeur_ville   = LabelEncoder()
        self.encodeur_cat     = LabelEncoder()
        self.encodeur_trans   = LabelEncoder()
        self.encodeur_quartier= LabelEncoder()
        self.est_entraine     = False
        self.mae              = 0
        self.score_r2         = 0
        self.dossier_modele   = 'simmo_ia/modeles'
        self.annonces         = []
        os.makedirs(self.dossier_modele, exist_ok=True)

    def group_quartier(self, q: str) -> str:
        q = str(q).lower().strip()
        if any(x in q for x in ['bonapriso','bastos','akwa','nlongkak','bonanjo']):
            return 'Luxe'
        if any(x in q for x in ['bonamoussadi','makepe','essos','omnisports','deido','ndokoti']):
            return 'Moyen+'
        if any(x in q for x in ['new bell','bali','bepanda','logpom','nkoldongo']):
            return 'Moyen'
        if any(x in q for x in ['ndogbong', 'odza', 'biyem', 'mvog-ada', 'nkoldongo', 'mendong',
             'soa', 'etoug-ebe', 'nsimalen', 'ekoumdoum', 'emana', 'melen',
             'nkolfou', 'ekounou', 'aze', 'ekoko',
             'pk14', 'pk12', 'pk10', 'pk8', 'pk6',  
             'bonaberi', 'ndobo', 'ngodi']):
            return 'Populaire'
        return 'Moyen'

    def preparer_features(self, annonces):
        df = pd.DataFrame(annonces)
        df['surface_m2']  = df['surface_m2'].fillna(50)
        df['nb_chambres'] = df['nb_chambres'].fillna(1)
        df['meuble']      = df['meuble'].fillna(False).astype(int)
        df['quartier']    = df['quartier'].fillna('Inconnu').apply(self.group_quartier)
        return df

    def entrainer(self, annonces):
        if len(annonces) < 10:
            return
        df              = self.preparer_features(annonces)
        df['ville_enc'] = self.encodeur_ville.fit_transform(df['ville'].fillna('Inconnue'))
        df['cat_enc']   = self.encodeur_cat.fit_transform(df['categorie'].fillna('appartement'))
        df['trans_enc'] = self.encodeur_trans.fit_transform(df['type_transaction'].fillna('location'))
        df['quartier_enc'] = self.encodeur_quartier.fit_transform(df['quartier'])

        features = ['surface_m2','nb_chambres','meuble','ville_enc','cat_enc','trans_enc','quartier_enc']
        X        = df[features].values
        y        = df['prix'].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.modele.fit(X_train, y_train)
        self.est_entraine = True

        y_pred      = self.modele.predict(X_test)
        self.mae    = np.mean(np.abs(y_test - y_pred))
        self.score_r2 = self.modele.score(X_test, y_test)
        print(f"Modèle prix R2: {self.score_r2:.2f} | MAE: {self.mae:,.0f}")
        self.sauvegarder_modele()

    def sauvegarder_modele(self):
        for nom, obj in [
            ('modele_prix',  self.modele),
            ('enc_quartier', self.encodeur_quartier),
            ('enc_ville',    self.encodeur_ville),
            ('enc_cat',      self.encodeur_cat),
            ('enc_trans',    self.encodeur_trans),
            ('mae',          self.mae),
            ('r2',           self.score_r2),
        ]:
            joblib.dump(obj, f'{self.dossier_modele}/{nom}.pkl')

    def charger_modele(self):
        try:
            if not os.path.exists(f'{self.dossier_modele}/modele_prix.pkl'):
                return False
            self.modele            = joblib.load(f'{self.dossier_modele}/modele_prix.pkl')
            self.encodeur_quartier = joblib.load(f'{self.dossier_modele}/enc_quartier.pkl')
            self.encodeur_ville    = joblib.load(f'{self.dossier_modele}/enc_ville.pkl')
            self.encodeur_cat      = joblib.load(f'{self.dossier_modele}/enc_cat.pkl')
            self.encodeur_trans    = joblib.load(f'{self.dossier_modele}/enc_trans.pkl')
            self.mae               = joblib.load(f'{self.dossier_modele}/mae.pkl')
            self.score_r2          = joblib.load(f'{self.dossier_modele}/r2.pkl')
            self.est_entraine      = True
            return True
        except Exception:
            return False

    def predire_prix_batch(self, annonces: list) -> list:
        """
        OPTIMISATION 6 : prédire tous les prix en UNE SEULE passe
        au lieu d'appeler predict() pour chaque annonce.
        """
        if not self.est_entraine or not annonces:
            return [None] * len(annonces)

        try:
            rows = []
            for a in annonces:
                qg  = self.group_quartier(a.get('quartier', 'Inconnu'))
                v   = a.get('ville', '')
                cat = a.get('categorie', '')
                tr  = a.get('type_transaction', 'location')

                ville_enc   = self.encodeur_ville.transform([v])[0]   if v   in self.encodeur_ville.classes_    else 0
                cat_enc     = self.encodeur_cat.transform([cat])[0]   if cat in self.encodeur_cat.classes_      else 0
                trans_enc   = self.encodeur_trans.transform([tr])[0]  if tr  in self.encodeur_trans.classes_    else 0
                quartier_enc= self.encodeur_quartier.transform([qg])[0] if qg in self.encodeur_quartier.classes_ else 0

                rows.append([
                    a.get('surface_m2') or 50,
                    a.get('nb_chambres') or 1,
                    int(a.get('meuble') or False),
                    ville_enc, cat_enc, trans_enc, quartier_enc,
                ])

            X       = np.array(rows)
            predits = self.modele.predict(X)  # UN SEUL appel predict()

            resultats = []
            for i, (a, prix_predit) in enumerate(zip(annonces, predits)):
                qg   = self.group_quartier(a.get('quartier', 'Inconnu'))
                MULT_VENTE    = {'Luxe': 2.50, 'Moyen+': 1.80, 'Moyen': 1.20, 'Populaire': 0.70}
                MULT_LOCATION = {'Luxe': 1.43, 'Moyen+': 1.49, 'Moyen': 1.00, 'Populaire': 1.16}
                type_tr = a.get('type_transaction', 'location')
                mult    = (MULT_VENTE if type_tr == 'vente' else MULT_LOCATION).get(qg, 1.0)
                prix    = float(prix_predit) * mult

            fourchette_min = round(prix * 0.75, 0)
            fourchette_max = round(prix * 1.25, 0)

            # Corrections
            if fourchette_min < 30_000:
                fourchette_min = 30_000
            if fourchette_max < fourchette_min:
                fourchette_max = round(fourchette_min * 1.3, 0)

            resultats.append({
                'prix_estime'   : round(prix, 0),
                'fourchette_min': fourchette_min,
                'fourchette_max': fourchette_max,
                'fiabilite'     : 'haute' if (self.mae / prix < 0.1 if prix else False) else 'moyenne',
            })
            return resultats

        except Exception as e:
            print("Erreur batch prix:", e)
            return [{'prix_estime': None} for _ in annonces]

    def predire_prix(self, ville, categorie, surface_m2, nb_chambres,
                     meuble, type_transaction, quartier="Inconnu"):
        """Compatibilité — appel unitaire."""
        resultats = self.predire_prix_batch([{
            'ville': ville, 'categorie': categorie,
            'surface_m2': surface_m2, 'nb_chambres': nb_chambres,
            'meuble': meuble, 'type_transaction': type_transaction,
            'quartier': quartier,
        }])
        return resultats[0] if resultats else {'prix_estime': None}


class RecommandationDistance:

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R    = 6371
        lat1, lon1 = math.radians(float(lat1)), math.radians(float(lon1))
        lat2, lon2 = math.radians(float(lat2)), math.radians(float(lon2))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a    = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def calculer_score(self, lat_user, lon_user, annonces):
        if not lat_user or not lon_user:
            return [0.5] * len(annonces)

        scores = []
        for a in annonces:
            lat_a, lon_a = a.get('latitude'), a.get('longitude')
            if not lat_a or not lon_a:
                scores.append(0.5)
                continue
            try:
                d = self.haversine(lat_user, lon_user, float(lat_a), float(lon_a))
                if   d <= 0.5: score = 1.0
                elif d <= 1:   score = 0.9
                elif d <= 2:   score = 0.75
                elif d <= 3:   score = 0.6
                elif d <= 5:   score = 0.4
                elif d <= 10:  score = 0.2
                else:          score = 0.0
                scores.append(round(score, 4))
            except Exception:
                scores.append(0.5)
        return scores

    def filtrer_par_rayon(self, lat_user, lon_user, annonces, rayon_km=10):
        if not lat_user or not lon_user:
            return annonces
        result = []
        for a in annonces:
            if not a.get('latitude') or not a.get('longitude'):
                result.append(a); continue
            try:
                if self.haversine(lat_user, lon_user, float(a['latitude']), float(a['longitude'])) <= rayon_km:
                    result.append(a)
            except Exception:
                result.append(a)
        return result


class MoteurRecommandation:

    def __init__(self):
        self.nlp      = RecommandationNLP()
        self.prix     = RecommandationPrix()
        self.distance = RecommandationDistance()

    def entrainer(self, annonces):
        self.nlp.entrainer_sur_corpus(annonces)
        self.prix.entrainer(annonces)

    def recommander(self, annonces, requete):
        if not annonces:
            return []

        filtrees = self._appliquer_filtres(annonces, requete)
        if len(filtrees) < 3:
            filtrees = annonces[:]
        if not filtrees:
            return []

        texte_requete = self._construire_texte(requete)
        scores_nlp    = self.nlp.calculer_similarite(texte_requete, filtrees)
        scores_dist   = self.distance.calculer_score(
            requete.get('latitude'), requete.get('longitude'), filtrees
        )
        scores_prix   = self._score_prix(filtrees, requete)
        scores_pop    = self._score_popularite(filtrees)

        # OPTIMISATION 6 : prédictions prix en batch
        predictions = self.prix.predire_prix_batch(filtrees)

        # Poids dynamiques
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
            bonus_desc  = self.nlp.analyser_qualite_description(
                annonce.get('description', '')
            ) * 0.05
            score_final = min(score_final + bonus_desc, 1.0)

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
                'prix_estime'     : predictions[i].get('prix_estime'),
                'raison'          : self._raison(
                    scores_nlp[i], scores_prix[i], scores_dist[i], annonce
                ),
            })

        resultats.sort(key=lambda x: x['score_final'], reverse=True)
        return resultats[:requete.get('limite', 10)]

    def _appliquer_filtres(self, annonces, requete):
        filtrees = annonces[:]
        if requete.get('type_transaction'):
            filtrees = [a for a in filtrees if a.get('type_transaction') == requete['type_transaction']]
        if requete.get('type_bien'):
            filtrees = [a for a in filtrees if a.get('categorie') == requete['type_bien']]
        if requete.get('budget_max'):
            filtrees = [a for a in filtrees if float(a.get('prix', 0)) <= requete['budget_max']]
        if requete.get('budget_min'):
            filtrees = [a for a in filtrees if float(a.get('prix', 0)) >= requete['budget_min']]
        if requete.get('surface_min'):
            filtrees = [a for a in filtrees if a.get('surface_m2') and float(a['surface_m2']) >= requete['surface_min']]
        if requete.get('nb_chambres'):
            filtrees = [a for a in filtrees if a.get('nb_chambres') and int(a['nb_chambres']) >= requete['nb_chambres']]
        if requete.get('ville'):
            ville_lower = requete['ville'].lower()
            filtrees = [a for a in filtrees if a.get('ville') and ville_lower in a['ville'].lower()]
        if requete.get('meuble') is True:
            filtrees = [a for a in filtrees if bool(a.get('meuble'))]
        return filtrees

    def _construire_texte(self, requete):
        parties = []
        for cle, suffixe in [
            ('type_bien', ''), ('ville', ''), ('type_transaction', ''), ('q', '')
        ]:
            if requete.get(cle):
                parties.append(requete[cle])
        if requete.get('nb_chambres'):
            parties.append(f"{requete['nb_chambres']} chambres")
        if requete.get('meuble'):
            parties.append('meuble')
        return ' '.join(parties) if parties else 'logement'

    def _score_prix(self, annonces, requete):
        scores     = []
        budget_max = requete.get('budget_max')
        budget_min = requete.get('budget_min')

        prix_medians = {}
        for a in annonces:
            cat = a.get('categorie', 'autre')
            prix_medians.setdefault(cat, []).append(float(a.get('prix', 0)))
        for cat in prix_medians:
            vals = sorted(prix_medians[cat])
            prix_medians[cat] = vals[len(vals) // 2]

        for annonce in annonces:
            prix = float(annonce.get('prix', 0))
            cat  = annonce.get('categorie', 'autre')
            if budget_max and budget_min:
                cible = (budget_max + budget_min) / 2
                ecart = abs(prix - cible) / cible if cible else 0
                score = max(0.0, 1.0 - ecart)
            elif budget_max:
                ratio = prix / budget_max if budget_max else 1
                if   ratio <= 0.70: score = 0.9
                elif ratio <= 0.85: score = 1.0
                elif ratio <= 1.00: score = 0.7
                else:               score = 0.0
            elif budget_min:
                score = 1.0 if prix >= budget_min else 0.3
            else:
                median = prix_medians.get(cat, prix)
                if median > 0:
                    score = max(0.2, min(1.0 - abs(1.0 - prix / median) * 0.5, 1.0))
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
        if score_nlp  > 0.5: raisons.append('correspond à votre recherche')
        if score_prix > 0.7: raisons.append('dans votre budget')
        elif score_prix > 0.5: raisons.append('prix raisonnable')
        if score_dist > 0.7: raisons.append('proche de votre localisation')
        vues = int(annonce.get('vues', 0))
        if vues > 200: raisons.append('très populaire')
        elif vues > 50: raisons.append('populaire')
        if annonce.get('meuble'): raisons.append('meublé')
        if not raisons: raisons.append('suggéré pour vous')
        return 'Ce bien ' + ', '.join(raisons) + '.'
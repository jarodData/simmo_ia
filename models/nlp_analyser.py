import joblib
import os
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class NLPAnalyser:
    def __init__(self):
        print("Initialisation du modèle NLP TF-IDF...")
        self.vectorizer = TfidfVectorizer(stop_words='french', max_features=500)
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
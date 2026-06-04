import joblib
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

class PrixPredictor:
    def __init__(self):
        self.modele = RandomForestRegressor(n_estimators=150, random_state=42)
        self.encodeur_ville = LabelEncoder()
        self.encodeur_cat = LabelEncoder()
        self.encodeur_trans = LabelEncoder()
        self.encodeur_quartier = LabelEncoder() # NOUVEAU
        self.est_entraine = False
        self.mae = 0
        self.score_r2 = 0
        self.dossier_modele = 'simmo_ia/modeles'
        os.makedirs(self.dossier_modele, exist_ok=True)
        

    def preparer_features(self, annonces: list) -> pd.DataFrame:
        df = pd.DataFrame(annonces)
        df['surface_m2'] = df['surface_m2'].fillna(df['surface_m2'].median())
        df['nb_chambres'] = df['nb_chambres'].fillna(1)
        df['meuble'] = df['meuble'].fillna(False).astype(int)
    
    # Regroupement quartiers Douala
        def group_quartier(q):
            q = str(q).lower()
            if any(x in q for x in ['bonapriso', 'akwa', 'bastos', 'nlongkak', 'kotto', 'logbaba']):
                return 'Luxe'
            if any(x in q for x in ['bonamoussadi', 'makepe', 'essos']):
                 return 'Moyen+'
            if any(x in q for x in ['ndogbong', 'odza', 'biyem', 'mvog-ada', 'nkoldongo', 'essos']): 
                return 'Populaire'
            return 'Moyen'
    
        df['quartier'] = df['quartier'].fillna('Inconnu').apply(group_quartier)
        
        print(f"Quartiers apres regroupement :{df['quartier'].value_counts().to_dict()}")
        return df
    def entrainer(self, annonces: list):
        if len(annonces) < 5:
            print("⚠️ Pas assez de données pour entraîner le modèle prix.")
            return

        df = self.preparer_features(annonces)
        df['ville_enc'] = self.encodeur_ville.fit_transform(df['ville'].fillna('Inconnue'))
        df['cat_enc'] = self.encodeur_cat.fit_transform(df['categorie'].fillna('appartement'))
        df['trans_enc'] = self.encodeur_trans.fit_transform(df['type_transaction'].fillna('location'))
        df['quartier_enc'] = self.encodeur_quartier.fit_transform(df['quartier']) # NOUVEAU

        features = ['surface_m2', 'nb_chambres', 'meuble', 'ville_enc', 'cat_enc', 'trans_enc', 'quartier_enc']
        X = df[features].values
        y = df['prix'].values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.modele.fit(X_train, y_train)
        self.est_entraine = True

        y_pred = self.modele.predict(X_test)
        self.mae = np.mean(np.abs(y_test - y_pred))
        self.score_r2 = self.modele.score(X_test, y_test)
        # score = self.modele.score(X_test, y_test)
        print(f"Modèle prix entraîné - Score R²: {self.score_r2:.2f} | MAE: {self.mae:,.0f} F CFA")
    
        self.sauvegarder_modele() # <- AJOUTÉ
    def predire_prix(self, ville: str, categorie: str, surface_m2: float,
                     nb_chambres: int, meuble: bool, type_transaction: str, quartier: str = "Inconnu") -> dict:

        if not self.est_entraine:
            # return {"prix_estime": None, "fourchette_min": None, "fourchette_max": None, "fiabilite": "indisponible"}
            return 0, 0,0, "indisponible"
        try:
            ville_enc = self.encodeur_ville.transform([ville])[0] if ville in self.encodeur_ville.classes_ else 0
            cat_enc = self.encodeur_cat.transform([categorie])[0] if categorie in self.encodeur_cat.classes_ else 0
            trans_enc = self.encodeur_trans.transform([type_transaction])[0] if type_transaction in self.encodeur_trans.classes_ else 0
            quartier_enc = self.encodeur_quartier.transform([quartier])[0] if quartier in self.encodeur_quartier.classes_ else 0 # NOUVEAU

            X = np.array([[surface_m2, nb_chambres, int(meuble), ville_enc, cat_enc, trans_enc, quartier_enc]])
            prix_predit = float(self.modele.predict(X)[0])

            fourchette_min = max(0, prix_predit - self.mae)
            fourchette_max = prix_predit + self.mae

            # Fiabilité CORRIGÉE : basée sur % d'erreur
            erreur_rel = self.mae / prix_predit if prix_predit > 0 else 1
            if erreur_rel < 0.1:
                fiabilite = "haute" # < 10% d'erreur
            elif erreur_rel < 0.2:
                fiabilite = "moyenne" # 10-20% d'erreur
            else:
                fiabilite = "basse" # > 20% d'erreur

            # return {
            #     "prix_estime": round(float(prix_predit), 2),
            #     "fourchette_min": round(float(fourchette_min), 2),
            #     "fourchette_max": round(float(fourchette_max), 2),
            #     "fiabilite": fiabilite,
            # }
            # Multiplicateurs réels Douala basés sur le marché
            MULTIPLICATEURS_QUARTIER = {
                'Luxe': 1.85,      # Bonapriso, Bastos, Akwa = +85% vs moyen
                'Moyen+': 1.35,    # Bonamoussadi, Makepe = +35%
                'Moyen': 1.00,     # Base
                'Populaire': 0.65, # Ndogbong, Odza, Biyem = -35%
                'Inconnu': 1.00
            }

            multiplicateur = MULTIPLICATEURS_QUARTIER.get(quartier, 1.0)
            prix_predit = prix_predit * multiplicateur
            fourchette_min = fourchette_min * multiplicateur  
            fourchette_max = fourchette_max * multiplicateur
            return round(prix_predit, 0) , round(fourchette_min , 0) ,round(fourchette_max, 0), fiabilite
        except Exception as e:
            print(f"Erreur prédiction prix: {e}")
            # return {"prix_estime": None, "fourchette_min": None, "fourchette_max": None, "fiabilite": "erreur"}
            return 0, 0, 0,"erreur"
    def sauvegarder_modele(self):
            """Sauvegarde modèle + encodeurs après entraînement"""
            if not self.est_entraine:
                return
    
            joblib.dump(self.modele, f'{self.dossier_modele}/modele_prix.pkl')
            joblib.dump(self.encodeur_ville, f'{self.dossier_modele}/enc_ville.pkl')
            joblib.dump(self.encodeur_cat, f'{self.dossier_modele}/enc_cat.pkl')
            joblib.dump(self.encodeur_trans, f'{self.dossier_modele}/enc_trans.pkl')
            joblib.dump(self.encodeur_quartier, f'{self.dossier_modele}/enc_quartier.pkl')
            joblib.dump(self.mae, f'{self.dossier_modele}/mae.pkl')
            joblib.dump(self.score_r2, f'{self.dossier_modele}/r2.pkl')
            print(f" Modèle sauvegardé dans {self.dossier_modele}/")

def charger_modele(self):
    """Charge modèle si existe, sinon False"""
    try:
        chemin = f'{self.dossier_modele}/modele_prix.pkl'
        if not os.path.exists(chemin):
            return False
            
        self.modele = joblib.load(f'{self.dossier_modele}/modele_prix.pkl')
        self.encodeur_ville = joblib.load(f'{self.dossier_modele}/enc_ville.pkl')
        self.encodeur_cat = joblib.load(f'{self.dossier_modele}/enc_cat.pkl')
        self.encodeur_trans = joblib.load(f'{self.dossier_modele}/enc_trans.pkl')
        self.encodeur_quartier = joblib.load(f'{self.dossier_modele}/enc_quartier.pkl')
        self.mae = joblib.load(f'{self.dossier_modele}/mae.pkl')
        self.score_r2 = joblib.load(f'{self.dossier_modele}/r2.pkl')
        self.est_entraine = True
        print(f" Modèle chargé depuis {self.dossier_modele}/ - R²: {self.score_r2:.2f}")
        return True
    except Exception as e:
        print(f" Erreur chargement modèle: {e}")
        return False

   
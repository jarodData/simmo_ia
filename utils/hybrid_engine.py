from models.recommandation import MoteurRecommandation
from utils.photo_pipeline  import appliquer_meilleure_photo
from models.photo_selector import PhotoSelector
from pathlib import Path
import json
import os

class MoteurHybride(MoteurRecommandation):
    def __init__(self):
        super().__init__()  
        self.annonces = []  

    # async def charger_donnees(self):
    #     """Charge les annonces depuis ton fichier JSON/DB"""
    #     chemin = self.BASE_DIR / 'data'/ 'annonces.json'
    #     if not chemin.exists():
    #         print(f"fichier non trouve : {chemin}")
    #         self.annonces = []
    #         return []
    #     with open(chemin, 'r', encoding='utf-8') as f:
    #         self.annonces = json.load(f)
        
    #     # Passe les annonces au modèle de prix aussi
    #     if hasattr(self, 'prix'):
    #         self.prix.annonces = self.annonces
        
    #     print(f"{len(self.annonces)} annonces chargées en mémoire")
    #     return self.annonces

    def recommander(self, annonces, requete):
        annonces = appliquer_meilleure_photo(annonces)
        return super().recommander(annonces, requete)

    def appliquer_meilleure_photo(self, annonces):  
        selector = PhotoSelector()
        for annonce in annonces:
            photos = annonce.get("photos", [])
            annonce["photo"] = selector.choisir_meilleure(photos)
        return annonces
    
    def _calculer_score_prix(self, annonces, requete):
        return self._score_prix(annonces, requete)

    def _calculer_score_popularite(self, annonces):
        return self._score_popularite(annonces)
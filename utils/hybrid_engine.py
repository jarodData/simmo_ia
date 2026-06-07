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
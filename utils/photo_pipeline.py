
from models.photo_selector import PhotoSelector

def appliquer_meilleure_photo(annonces):

    selector = PhotoSelector()

    for annonce in annonces:
        photos = annonce.get("photos", [])

        annonce["photo"] = selector.choisir_meilleure(photos)

    return annonces
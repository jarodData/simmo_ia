import re

class PhotoSelector:

    def score_photo(self, photo):

        if not photo:
            return -1

        score = 0
        chemin = photo.get("chemin_image", "")

        # priorité image principale
        if photo.get("est_principale"):
            score += 100

        # extension valide
        if re.search(r"\.(jpg|jpeg|png|webp)$", chemin):
            score += 10

        # qualité nom fichier
        if len(chemin) > 15:
            score += 5

        # pénalité placeholder
        if "placehold" in chemin:
            score -= 100

        return score

    def choisir_meilleure(self, photos):

        if not photos:
            return None

        best = max(photos, key=self.score_photo)

        return best.get("chemin_image")
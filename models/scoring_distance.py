import math

class ScoringDistance:

    @staticmethod
    def haversine(lat1: float, lon1: float,
                  lat2: float, lon2: float) -> float:
        """
        Calcule la distance en km entre deux points GPS
        Formule de Haversine
        """
        R = 6371  # Rayon de la Terre en km

        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + \
            math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def calculer_score(self, lat_user: float, lon_user: float,
                       annonces: list) -> list:
        """
        Calcule un score de proximité pour chaque annonce
        Plus l'annonce est proche, plus le score est élevé (entre 0 et 1)
        """
        scores = []

        for annonce in annonces:
            lat_annonce = annonce.get('latitude')
            lon_annonce = annonce.get('longitude')

            if not lat_annonce or not lon_annonce or \
               not lat_user or not lon_user:
                scores.append(0.5)  # Score neutre si pas de coordonnées
                continue

            distance_km = self.haversine(
                lat_user, lon_user,
                float(lat_annonce), float(lon_annonce)
            )

            # Convertir la distance en score
            # 0 km = score 1.0 | 5 km = score 0.5 | 20 km+ = score 0.0
            if distance_km <= 1:
                score = 1.0
            elif distance_km <= 5:
                score = 1.0 - ((distance_km - 1) / 4) * 0.5
            elif distance_km <= 20:
                score = 0.5 - ((distance_km - 5) / 15) * 0.5
            else:
                score = 0.0

            scores.append(round(score, 4))

        return scores

    def filtrer_par_rayon(self, lat_user: float, lon_user: float,
                          annonces: list, rayon_km: float = 10) -> list:
        """Filtre les annonces dans un rayon donné"""
        if not lat_user or not lon_user:
            return annonces

        return [
            a for a in annonces
            if a.get('latitude') and a.get('longitude') and
               self.haversine(
                   lat_user, lon_user,
                   float(a['latitude']), float(a['longitude'])
               ) <= rayon_km
        ]
import requests
import math
from typing import Optional

class ScoringContextuel:

    # ── Lieux de culte reconnus ──────────────
    LIEUX_CULTE = {
        'musulman'   : ['mosque', 'place_of_worship'],
        'islam'      : ['mosque', 'place_of_worship'],
        'mosquee'    : ['mosque'],
        'catholique' : ['place_of_worship'],
        'catholic'   : ['place_of_worship'],
        'protestant' : ['place_of_worship'],
        'chretien'   : ['place_of_worship'],
        'eglise'     : ['place_of_worship'],
        'marche'     : ['marketplace', 'market'],
        'hopital'    : ['hospital', 'clinic'],
        'pharmacie'  : ['pharmacy'],
        'ecole'      : ['school', 'university', 'college'],
        'universite' : ['university', 'college'],
        'stade'      : ['stadium', 'sports_centre'],
        'supermarche': ['supermarket', 'mall'],
        'restaurant' : ['restaurant', 'fast_food'],
        'banque'     : ['bank', 'atm'],
    }

    # ── Religion → tag OSM ───────────────────
    RELIGION_TAGS = {
        'musulman'  : 'muslim',
        'islam'     : 'muslim',
        'catholique': 'christian',
        'protestant': 'christian',
        'chretien'  : 'christian',
    }

    # ── Headers communs ──────────────────────
    HEADERS = {'User-Agent': 'SIMMo-App/1.0'}

    def geocoder_lieu(self, nom_lieu: str, ville: str = '') -> Optional[dict]:
        """Géocode un lieu via Nominatim (OpenStreetMap)."""
        try:
            query  = f"{nom_lieu}, {ville}, Cameroun" if ville else f"{nom_lieu}, Cameroun"
            params = {'q': query, 'format': 'json', 'limit': 1, 'addressdetails': 1}
            resp   = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params=params, headers=self.HEADERS, timeout=5
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return {
                    'nom'      : data[0].get('display_name', nom_lieu),
                    'latitude' : float(data[0]['lat']),
                    'longitude': float(data[0]['lon']),
                    'type'     : data[0].get('type', ''),
                }
            return None
        except Exception as e:
            print(f"Erreur géocodage: {e}")
            return None

    def chercher_lieux_proches(self, lat: float, lon: float,
                                type_lieu: str, religion: str = None,
                                rayon_km: float = 3) -> list:
        """Cherche des lieux via Overpass API autour de coordonnées GPS."""
        try:
            rayon_m = int(rayon_km * 1000)

            if religion and religion.lower() in self.RELIGION_TAGS:
                tag_religion = self.RELIGION_TAGS[religion.lower()]
                query = (
                    f'[out:json][timeout:10];'
                    f'('
                    f'node["amenity"="place_of_worship"]["religion"="{tag_religion}"]'
                    f'(around:{rayon_m},{lat},{lon});'
                    f'way["amenity"="place_of_worship"]["religion"="{tag_religion}"]'
                    f'(around:{rayon_m},{lat},{lon});'
                    f');out center;'
                )
            else:
                amenities = self.LIEUX_CULTE.get(type_lieu.lower(), [type_lieu.lower()])
                # CORRECTION : une ligne par amenity, pas de regex multi-lignes
                nodes = ''.join(
                    f'node["amenity"="{a}"](around:{rayon_m},{lat},{lon});'
                    for a in amenities
                )
                query = f'[out:json][timeout:10];({nodes});out center;'

            resp = requests.post(
                'https://overpass-api.de/api/interpreter',
                data={'data': query},
                headers=self.HEADERS,
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            lieux = []
            for element in data.get('elements', [])[:10]:
                lat_lieu = element.get('lat') or element.get('center', {}).get('lat')
                lon_lieu = element.get('lon') or element.get('center', {}).get('lon')
                tags     = element.get('tags', {})
                if lat_lieu and lon_lieu:
                    lieux.append({
                        'nom'        : tags.get('name', type_lieu),
                        'latitude'   : lat_lieu,
                        'longitude'  : lon_lieu,
                        'distance_km': round(self._haversine(lat, lon, lat_lieu, lon_lieu), 2),
                        'type'       : tags.get('amenity', type_lieu),
                    })

            lieux.sort(key=lambda x: x['distance_km'])
            return lieux

        except Exception as e:
            print(f"Erreur Overpass (chercher_lieux_proches): {e}")
            return []

    def scorer_annonces_par_contexte(self, annonces: list,
                                      lat_ref: float, lon_ref: float,
                                      rayon_max_km: float = 5) -> list:
        """Score chaque annonce selon sa proximité avec le point de référence."""
        scores = []
        for annonce in annonces:
            lat_a = annonce.get('latitude')
            lon_a = annonce.get('longitude')

            if not lat_a or not lon_a:
                scores.append(0.3)
                continue

            distance = self._haversine(lat_ref, lon_ref, float(lat_a), float(lon_a))

            if   distance <= 0.5: score = 1.0
            elif distance <= 1:   score = 0.9
            elif distance <= 2:   score = 0.75
            elif distance <= 3:   score = 0.6
            elif distance <= 5:   score = 0.4
            elif distance <= 10:  score = 0.2
            else:                 score = 0.0

            scores.append(round(score, 4))

        return scores

    def analyser_contexte_quartier(self, lat: float, lon: float) -> dict:
        """
        Analyse l'environnement d'un quartier.
        CORRECTION : requête Overpass sans regex multi-lignes — une ligne par amenity.
        """
        try:
            # CORRECTION : regex sur une seule ligne OU liste explicite de nodes
            # La version multi-lignes dans le string causait un JSON vide en retour
            query = (
                '[out:json][timeout:15];'
                '('
                f'node["amenity"="mosque"](around:2000,{lat},{lon});'
                f'node["amenity"="place_of_worship"](around:2000,{lat},{lon});'
                f'node["amenity"="school"](around:2000,{lat},{lon});'
                f'node["amenity"="university"](around:2000,{lat},{lon});'
                f'node["amenity"="hospital"](around:2000,{lat},{lon});'
                f'node["amenity"="clinic"](around:2000,{lat},{lon});'
                f'node["amenity"="pharmacy"](around:2000,{lat},{lon});'
                f'node["amenity"="marketplace"](around:2000,{lat},{lon});'
                f'node["amenity"="supermarket"](around:2000,{lat},{lon});'
                f'node["amenity"="bank"](around:2000,{lat},{lon});'
                ');'
                'out;'
            )

            resp = requests.post(
                'https://overpass-api.de/api/interpreter',
                data={'data': query},
                headers=self.HEADERS,
                timeout=20
            )
            resp.raise_for_status()

            # CORRECTION : vérifier que la réponse n'est pas vide avant de parser
            if not resp.text or not resp.text.strip():
                print("Erreur analyse quartier: réponse Overpass vide")
                return self._analyse_vide()

            data     = resp.json()
            elements = data.get('elements', [])

            analyse = self._analyse_vide()

            for e in elements:
                tags     = e.get('tags', {})
                amenity  = tags.get('amenity', '')
                religion = tags.get('religion', '')

                if amenity == 'place_of_worship':
                    analyse['lieux_culte'] += 1
                    if religion == 'muslim':
                        analyse['mosquees'] += 1
                    elif religion == 'christian':
                        analyse['eglises'] += 1
                elif amenity in ['school', 'university', 'college']:
                    analyse['ecoles'] += 1
                elif amenity in ['hospital', 'clinic']:
                    analyse['hopitaux'] += 1
                elif amenity == 'pharmacy':
                    analyse['pharmacies'] += 1
                elif amenity in ['marketplace', 'supermarket']:
                    analyse['marches'] += 1
                elif amenity == 'bank':
                    analyse['banques'] += 1

            score = min(
                (analyse['ecoles']      * 0.20 +
                 analyse['hopitaux']    * 0.25 +
                 analyse['pharmacies']  * 0.15 +
                 analyse['marches']     * 0.20 +
                 analyse['banques']     * 0.10 +
                 analyse['lieux_culte'] * 0.10) / 3,
                1.0
            )
            analyse['score_services'] = round(score, 4)
            return analyse

        except Exception as e:
            print(f"Erreur analyse quartier: {e}")
            return self._analyse_vide()

    @staticmethod
    def _analyse_vide() -> dict:
        """Retourne une structure vide plutôt qu'un dict {} pour éviter les KeyError."""
        return {
            'lieux_culte'   : 0,
            'mosquees'      : 0,
            'eglises'       : 0,
            'ecoles'        : 0,
            'hopitaux'      : 0,
            'pharmacies'    : 0,
            'marches'       : 0,
            'banques'       : 0,
            'score_services': 0.0,
        }

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
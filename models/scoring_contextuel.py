# models/scoring_contextuel.py — VERSION FINALE OPTIMISÉE
import requests
import math
import json
import os
import time
from typing import Optional

CACHE_FILE = '/tmp/simmo_overpass_cache.json'
CACHE_TTL  = 86400  # 24h


def _charger_cache() -> dict:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _sauvegarder_cache(cache: dict):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass


def _cle_cache(lat: float, lon: float, type_lieu: str,
               religion: str = None, rayon_km: float = 3) -> str:
    lat_r = round(lat / 0.005) * 0.005
    lon_r = round(lon / 0.005) * 0.005
    return f"{lat_r:.3f}_{lon_r:.3f}_{type_lieu}_{religion or ''}_{rayon_km}"


class ScoringContextuel:

    LIEUX_CULTE = {
        'musulman'   : ['mosque', 'place_of_worship'],
        'islam'      : ['mosque', 'place_of_worship'],
        'mosquee'    : ['mosque'],
        'catholique' : ['place_of_worship'],
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

    RELIGION_TAGS = {
        'musulman'  : 'muslim',
        'islam'     : 'muslim',
        'catholique': 'christian',
        'protestant': 'christian',
        'chretien'  : 'christian',
    }

    HEADERS = {'User-Agent': 'SIMMo-App/1.0'}

    # Délai minimum entre appels Overpass (anti-429)
    _dernier_appel: float = 0
    DELAI_MIN = 1.5

    def __init__(self):
        self._cache = _charger_cache()

    def _get_cache(self, cle: str):
        entry = self._cache.get(cle)
        if entry and (time.time() - entry.get('ts', 0)) < CACHE_TTL:
            return entry['data']
        return None

    def _set_cache(self, cle: str, data):
        self._cache[cle] = {'data': data, 'ts': time.time()}
        _sauvegarder_cache(self._cache)

    def _appel_overpass(self, query: str, max_retries: int = 2) -> dict:
        """
        Appel Overpass avec :
        - Délai anti-429
        - Timeout réduit à 8s (au lieu de 15)
        - Retry avec backoff
        - Fallback vide rapide
        """
        maintenant    = time.time()
        delai_attente = self.DELAI_MIN - (maintenant - ScoringContextuel._dernier_appel)
        if delai_attente > 0:
            time.sleep(delai_attente)

        for tentative in range(max_retries):
            try:
                ScoringContextuel._dernier_appel = time.time()
                resp = requests.post(
                    'https://overpass-api.de/api/interpreter',
                    data    = {'data': query},
                    headers = self.HEADERS,
                    timeout = 8,  # CORRECTION : timeout réduit à 8s
                )

                if resp.status_code == 429:
                    attente = 3 * (tentative + 1)
                    print(f"Overpass 429 — attente {attente}s")
                    time.sleep(attente)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.Timeout:
                print(f"Overpass timeout {tentative+1}/{max_retries} — fallback vide")
                # Ne pas retry sur timeout — retourner vide immédiatement
                return {'elements': []}
            except Exception as e:
                print(f"Overpass erreur: {e}")
                if tentative < max_retries - 1:
                    time.sleep(1)

        return {'elements': []}

    def geocoder_lieu(self, nom_lieu: str, ville: str = '') -> Optional[dict]:
        cle    = f"geo_{nom_lieu}_{ville}"
        cached = self._get_cache(cle)
        if cached is not None:
            return cached

        try:
            query = f"{nom_lieu}, {ville}, Cameroun" if ville else f"{nom_lieu}, Cameroun"
            resp  = requests.get(
                'https://nominatim.openstreetmap.org/search',
                params  = {'q': query, 'format': 'json', 'limit': 1, 'addressdetails': 1},
                headers = self.HEADERS,
                timeout = 5,
            )
            resp.raise_for_status()
            data   = resp.json()
            result = {
                'nom'      : data[0].get('display_name', nom_lieu),
                'latitude' : float(data[0]['lat']),
                'longitude': float(data[0]['lon']),
                'type'     : data[0].get('type', ''),
            } if data else None
            self._set_cache(cle, result)
            return result
        except Exception as e:
            print(f"Erreur géocodage: {e}")
            return None

    def chercher_lieux_proches(self, lat: float, lon: float,
                                type_lieu: str, religion: str = None,
                                rayon_km: float = 3) -> list:
        cle    = _cle_cache(lat, lon, type_lieu, religion, rayon_km)
        cached = self._get_cache(cle)
        if cached is not None:
            return cached

        rayon_m = int(rayon_km * 1000)

        if religion and religion.lower() in self.RELIGION_TAGS:
            tag_religion = self.RELIGION_TAGS[religion.lower()]
            query = (
                f'[out:json][timeout:8];'
                f'(node["amenity"="place_of_worship"]["religion"="{tag_religion}"]'
                f'(around:{rayon_m},{lat},{lon});'
                f'way["amenity"="place_of_worship"]["religion"="{tag_religion}"]'
                f'(around:{rayon_m},{lat},{lon}););out center;'
            )
        else:
            amenities = self.LIEUX_CULTE.get(type_lieu.lower(), [type_lieu.lower()])
            nodes = ''.join(
                f'node["amenity"="{a}"](around:{rayon_m},{lat},{lon});'
                for a in amenities
            )
            query = f'[out:json][timeout:8];({nodes});out center;'

        data  = self._appel_overpass(query)
        lieux = []

        for element in data.get('elements', [])[:10]:
            lat_l = element.get('lat') or element.get('center', {}).get('lat')
            lon_l = element.get('lon') or element.get('center', {}).get('lon')
            tags  = element.get('tags', {})
            if lat_l and lon_l:
                lieux.append({
                    'nom'        : tags.get('name', type_lieu),
                    'latitude'   : lat_l,
                    'longitude'  : lon_l,
                    'distance_km': round(self._haversine(lat, lon, lat_l, lon_l), 2),
                    'type'       : tags.get('amenity', type_lieu),
                })

        lieux.sort(key=lambda x: x['distance_km'])
        self._set_cache(cle, lieux)
        return lieux

    def chercher_culte_depuis_reference(
        self, lat_ref: float, lon_ref: float,
        religion: str, rayon_km: float = 5
    ) -> dict:
        """UN SEUL appel Overpass pour tous les lieux de culte."""
        cle    = _cle_cache(lat_ref, lon_ref, 'culte_ref', religion, rayon_km)
        cached = self._get_cache(cle)
        if cached is not None:
            return cached

        lieux  = self.chercher_lieux_proches(lat_ref, lon_ref, 'place_of_worship', religion, rayon_km)
        result = {'lieux': lieux, 'lat_ref': lat_ref, 'lon_ref': lon_ref}
        self._set_cache(cle, result)
        return result

    def lieux_culte_proches_annonce(
        self, lat_annonce: float, lon_annonce: float,
        lieux_ref: list, rayon_km: float = 2
    ) -> list:
        """Filtrage LOCAL sans appel réseau."""
        proches = []
        for lieu in lieux_ref:
            dist = self._haversine(lat_annonce, lon_annonce, lieu['latitude'], lieu['longitude'])
            if dist <= rayon_km:
                proches.append({**lieu, 'distance_km': round(dist, 2)})
        proches.sort(key=lambda x: x['distance_km'])
        return proches[:3]

    def scorer_annonces_par_contexte(self, annonces: list,
                                      lat_ref: float, lon_ref: float,
                                      rayon_max_km: float = 5) -> list:
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
        cle    = _cle_cache(lat, lon, 'quartier', rayon_km=2)
        cached = self._get_cache(cle)
        if cached is not None:
            return cached

        query = (
            '[out:json][timeout:8];('
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
            ');out;'
        )

        data     = self._appel_overpass(query)
        elements = data.get('elements', [])
        analyse  = self._analyse_vide()

        for e in elements:
            tags     = e.get('tags', {})
            amenity  = tags.get('amenity', '')
            religion = tags.get('religion', '')
            if amenity == 'place_of_worship':
                analyse['lieux_culte'] += 1
                if religion == 'muslim':      analyse['mosquees'] += 1
                elif religion == 'christian': analyse['eglises']  += 1
            elif amenity in ['school', 'university', 'college']: analyse['ecoles']     += 1
            elif amenity in ['hospital', 'clinic']:               analyse['hopitaux']   += 1
            elif amenity == 'pharmacy':                           analyse['pharmacies'] += 1
            elif amenity in ['marketplace', 'supermarket']:       analyse['marches']    += 1
            elif amenity == 'bank':                               analyse['banques']    += 1

        score = min(
            (analyse['ecoles']      * 0.20 +
             analyse['hopitaux']    * 0.25 +
             analyse['pharmacies']  * 0.15 +
             analyse['marches']     * 0.20 +
             analyse['banques']     * 0.10 +
             analyse['lieux_culte'] * 0.10) / 3, 1.0
        )
        analyse['score_services'] = round(score, 4)
        self._set_cache(cle, analyse)
        return analyse

    @staticmethod
    def _analyse_vide() -> dict:
        return {
            'lieux_culte': 0, 'mosquees': 0, 'eglises': 0,
            'ecoles': 0, 'hopitaux': 0, 'pharmacies': 0,
            'marches': 0, 'banques': 0, 'score_services': 0.0,
        }

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2) -> float:
        R = 6371
        lat1, lon1 = math.radians(lat1), math.radians(lon1)
        lat2, lon2 = math.radians(lat2), math.radians(lon2)
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
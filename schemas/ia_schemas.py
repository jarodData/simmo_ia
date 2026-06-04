from pydantic import BaseModel
from typing import Dict, Optional, List ,Any

class RequeteRecommandation(BaseModel):
    user_id        : Optional[int]  = None
    ville          : Optional[str]  = None
    quartier       : Optional[str]  = None
    budget_min     : Optional[float]= None
    budget_max     : Optional[float]= None
    type_bien      : Optional[str]  = None  # appartement, studio...
    type_transaction: Optional[str] = None  # location, vente
    surface_min    : Optional[float]= None
    nb_chambres    : Optional[int]  = None
    meuble         : Optional[bool] = None
    latitude       : Optional[float]= None
    longitude      : Optional[float]= None
    limite         : Optional[int]  = 10

class AnnonceRecommandee(BaseModel):
    id_annonce          : int
    titre               : str
    prix                : float
    categorie           : str
    ville               : str
    quartier            : Optional[str]
    score_final         : float
    score_nlp           : float
    score_prix          : float
    score_distance      : float
    score_popularite    : float
    prix_estime         : Optional[float]
    raison              : str
    photo               : Optional[str] = None
    

class ReponseRecommandation(BaseModel):
    total               : int
    recommandations     : List[AnnonceRecommandee]

class RequetePrixPredit(BaseModel):
    ville               : str
    categorie           : str
    surface_m2          : float
    nb_chambres         : int
    meuble              : bool
    type_transaction    : str
    quartier            : str= "Inconnu"

class ReponsePrixPredit(BaseModel):
    prix_estime         : float
    fourchette_min      : float
    fourchette_max      : float
    fiabilite           : str# ── Recherche contextuelle ───────────────────

class RequeteContextuelle(BaseModel):
    # Lieu de référence (travail, école...)
    lieu_reference     : Optional[str]   = None  # "Université de Yaoundé I"
    ville_reference    : Optional[str]   = None  # "Yaoundé"

    # Religion / lieu de culte
    religion           : Optional[str]   = None  # "musulman", "catholique", "protestant"
    distance_culte_max : Optional[float] = 3.0   # km

    # Loisirs / commodités
    commodites         : Optional[list]  = None  # ["marche", "hopital", "pharmacie"]

    # Critères logement (comme avant)
    budget_min         : Optional[float] = None
    budget_max         : Optional[float] = None
    type_bien          : Optional[str]   = None
    type_transaction   : Optional[str]   = None
    nb_chambres        : Optional[int]   = None
    surface_min        : Optional[float] = None
    meuble             : Optional[bool]  = None
    limite             : Optional[int]   = 10

class LieuProche(BaseModel):
    nom          : str
    distance_km  : float
    type         : str

class AnnonceContextuelle(BaseModel):
    id_annonce         : int
    titre              : str
    prix               : float
    categorie          : str
    ville              : str
    quartier           : Optional[str]
    score_final        : float
    score_proximite    : float
    score_nlp          : float
    score_prix         : float
    distance_lieu_ref  : Optional[float]  # Distance du lieu de travail/école
    lieux_culte_proches: Optional[list]   # Mosquées/églises à proximité
    analyse_quartier   : Optional[dict]   # Services du quartier
    prix_estime        : Optional[float]
    raison             : str
    photo               : Optional[str] = None

class ReponseContextuelle(BaseModel):
    total              : int
    lieu_geocode       : Optional[dict]
    lieux_culte_trouves: Optional[list]
    annonces           : list
class RequeteNLP(BaseModel):
    description : str
    limite      : Optional[int] = 12    

class ReponseNLP(BaseModel):
    criteres_extraits : Dict[str, Any]
    mots_cles_nlp     : List[str]
    recommandations   : List[Dict[str, Any]]
    total             : int    
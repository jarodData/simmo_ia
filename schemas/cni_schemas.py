# schemas/cni_schemas.py
# Pydantic schemas pour les endpoints CNI

from pydantic        import BaseModel, Field
from typing          import Optional, List
from datetime        import datetime, date


# ─────────────────────────────────────────────────────
#  Données extraites par l'IA
# ─────────────────────────────────────────────────────

class DonneesExtraitesCNI(BaseModel):
    nom                     : Optional[str]   = None
    prenoms                 : Optional[str]   = None
    date_naissance          : Optional[str]   = None   # "YYYY-MM-DD"
    lieu_naissance          : Optional[str]   = None
    numero_cni              : Optional[str]   = None
    date_emission           : Optional[str]   = None
    date_expiration         : Optional[str]   = None
    sexe                    : Optional[str]   = None   # "M" / "F"
    nationalite             : Optional[str]   = "Camerounaise"
    face_detectee           : Optional[bool]  = None
    age                     : Optional[int]   = None
    jours_avant_expiration  : Optional[int]   = None


# ─────────────────────────────────────────────────────
#  Points de contrôle
# ─────────────────────────────────────────────────────

class VerificationCNI(BaseModel):
    document_authentique              : Optional[bool] = None
    photo_presente                    : Optional[bool] = None
    texte_lisible                     : Optional[bool] = None
    republique_cameroun_mentionnee    : Optional[bool] = None
    numero_format_valide              : Optional[bool] = None
    non_expire                        : Optional[bool] = None
    coherence_donnees                 : Optional[bool] = None


# ─────────────────────────────────────────────────────
#  Résultat complet d'une analyse
# ─────────────────────────────────────────────────────

class AnalyseCNI(BaseModel):
    valide                  : bool
    score_confiance         : float = Field(ge=0.0, le=1.0)
    score_lisibilite        : Optional[float]            = None
    donnees_extraites       : DonneesExtraitesCNI
    verification            : VerificationCNI
    anomalies               : List[str]                  = []
    recommandation          : str   # APPROUVER / REJETER / VERIFIER_MANUELLEMENT
    motif_recommandation    : Optional[str]              = None
    statut_couleur          : Optional[str]              = None
    analyse_at              : Optional[str]              = None


# ─────────────────────────────────────────────────────
#  Réponse endpoint /analyser
# ─────────────────────────────────────────────────────

class ReponseCNIAnalyser(BaseModel):
    succes  : bool
    erreur  : Optional[str]    = None
    analyse : Optional[AnalyseCNI] = None


# ─────────────────────────────────────────────────────
#  Réponse endpoint /valider/{id_agent}
# ─────────────────────────────────────────────────────

class ReponseCNIValider(BaseModel):
    id_agent        : int
    recommandation  : str
    statut_agent    : str
    analyse         : AnalyseCNI


# ─────────────────────────────────────────────────────
#  Body endpoint /decision/{id_agent}
# ─────────────────────────────────────────────────────

class DecisionManuelle(BaseModel):
    action  : str   = Field(..., pattern="^(approuver|rejeter)$")
    motif   : Optional[str] = "Décision manuelle admin"


class ReponseDecision(BaseModel):
    id_agent        : int
    action          : str
    motif           : str
    nouveau_statut  : str

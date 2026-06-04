from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, JSON
from database   import Base
from datetime   import datetime

class Agent(Base):
    __tablename__ = "agents"

    id                      = Column(Integer, primary_key=True, index=True)
    nom                     = Column(String(100), nullable=False)
    prenom                  = Column(String(100), nullable=False)
    email                   = Column(String(200), unique=True, nullable=False)
    telephone               = Column(String(20),  nullable=True)
    statut                  = Column(String(20),  default="en_attente")
    created_at              = Column(DateTime,    default=datetime.utcnow)

    # ── Champs CNI ──
    cni_url                 = Column(String(500), nullable=True)
    cni_valide              = Column(Boolean,     nullable=True)
    cni_score_confiance     = Column(Float,       nullable=True)
    cni_recommandation      = Column(String(30),  nullable=True)
    cni_motif_rejet         = Column(Text,        nullable=True)
    cni_decision_admin      = Column(String(20),  nullable=True)
    cni_motif_admin         = Column(Text,        nullable=True)
    cni_verif_manuelle      = Column(Boolean,     default=False)
    cni_analyse_at          = Column(DateTime,    nullable=True)
    cni_donnees             = Column(JSON,        nullable=True)
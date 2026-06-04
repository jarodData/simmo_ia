# models/cni_verifier.py
# Vérification CNI camerounaise par vision IA (Claude claude-sonnet-4-20250514)

import anthropic
import base64
import json
import re
from pathlib import Path
from datetime import datetime, date


client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY depuis l'env


# ─────────────────────────────────────────────────────
#  Prompt système spécialisé CNI Cameroun
# ─────────────────────────────────────────────────────

PROMPT_SYSTEME = """
Tu es un expert en vérification de documents d'identité camerounais.
Tu analyses des Cartes Nationales d'Identité (CNI) du Cameroun.

Une CNI camerounaise valide contient :
- Recto : photo du titulaire, nom, prénom(s), date de naissance, lieu de naissance,
  numéro CNI (format : XXXXXXXXXX ou XX-XXXXXXXXXX), date d'émission, date d'expiration,
  la mention "REPUBLIQUE DU CAMEROUN / REPUBLIC OF CAMEROON",
  autorité émettrice (DGSN), signature du titulaire.
- Verso : adresse, profession, taille, groupe sanguin, empreinte digitale,
  code-barres ou QR code selon génération.

Réponds UNIQUEMENT en JSON valide, sans texte autour, sans balises markdown.
"""

PROMPT_ANALYSE = """
Analyse cette image de CNI camerounaise et retourne un JSON avec exactement cette structure :

{
  "valide": true/false,
  "score_confiance": 0.0 à 1.0,
  "donnees_extraites": {
    "nom": "",
    "prenoms": "",
    "date_naissance": "YYYY-MM-DD ou null",
    "lieu_naissance": "",
    "numero_cni": "",
    "date_emission": "YYYY-MM-DD ou null",
    "date_expiration": "YYYY-MM-DD ou null",
    "sexe": "M/F ou null",
    "nationalite": "Camerounaise",
    "face_detectee": true/false
  },
  "verification": {
    "document_authentique": true/false,
    "photo_presente": true/false,
    "texte_lisible": true/false,
    "republique_cameroun_mentionnee": true/false,
    "numero_format_valide": true/false,
    "non_expire": true/false,
    "coherence_donnees": true/false
  },
  "anomalies": [],
  "recommandation": "APPROUVER / REJETER / VERIFIER_MANUELLEMENT",
  "motif_recommandation": ""
}

Anomalies possibles à détecter :
- Document expiré
- Photo absente ou masquée
- Texte illisible ou flou
- Signes de falsification (couleurs anormales, texte superposé)
- Document d'un autre pays
- Image trop petite ou de mauvaise qualité
- Document coupé (informations manquantes)
- Incohérence entre les données (ex: date expiration avant émission)
"""


# ─────────────────────────────────────────────────────
#  Classe principale
# ─────────────────────────────────────────────────────

class VerificateurCNI:

    FORMATS_ACCEPTES = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    TAILLE_MAX_MB    = 5

    def analyser(self, source: str | bytes, media_type: str = None) -> dict:
        """
        Analyse une CNI.
        source : chemin fichier (str/Path) OU bytes de l'image
        Retourne un dict structuré avec le résultat complet.
        """
        try:
            image_b64, mime = self._charger_image(source, media_type)
        except ValueError as e:
            return self._erreur(str(e))

        try:
            reponse = client.messages.create(
                model      = "claude-sonnet-4-20250514",
                max_tokens = 1024,
                system     = PROMPT_SYSTEME,
                messages   = [{
                    "role"   : "user",
                    "content": [
                        {
                            "type"  : "image",
                            "source": {
                                "type"       : "base64",
                                "media_type" : mime,
                                "data"       : image_b64,
                            },
                        },
                        {"type": "text", "text": PROMPT_ANALYSE},
                    ],
                }],
            )

            texte = reponse.content[0].text.strip()
            # Nettoyer si l'IA a quand même mis des backticks
            texte = re.sub(r'^```json\s*', '', texte)
            texte = re.sub(r'\s*```$',     '', texte)

            resultat = json.loads(texte)
            resultat = self._enrichir(resultat)
            return {"succes": True, "analyse": resultat}

        except json.JSONDecodeError as e:
            return self._erreur(f"Réponse IA non parseable : {e}")
        except Exception as e:
            return self._erreur(f"Erreur API : {e}")

    # ── Chargement image ──────────────────────────────

    def _charger_image(self, source, media_type=None):
        if isinstance(source, (bytes, bytearray)):
            if not media_type:
                raise ValueError("media_type requis pour les bytes (ex: 'image/jpeg')")
            if len(source) > self.TAILLE_MAX_MB * 1024 * 1024:
                raise ValueError(f"Image trop lourde (max {self.TAILLE_MAX_MB} Mo)")
            return base64.standard_b64encode(source).decode('utf-8'), media_type

        path = Path(source)
        if not path.exists():
            raise ValueError(f"Fichier introuvable : {path}")

        ext = path.suffix.lower()
        if ext not in self.FORMATS_ACCEPTES:
            raise ValueError(f"Format non supporté : {ext}. Acceptés : {self.FORMATS_ACCEPTES}")

        if path.stat().st_size > self.TAILLE_MAX_MB * 1024 * 1024:
            raise ValueError(f"Image trop lourde (max {self.TAILLE_MAX_MB} Mo)")

        mimes = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                 '.png': 'image/png',  '.webp': 'image/webp',
                 '.gif': 'image/gif'}
        mime = mimes[ext]
        data = base64.standard_b64encode(path.read_bytes()).decode('utf-8')
        return data, mime

    # ── Enrichissement post-analyse ───────────────────

    def _enrichir(self, r: dict) -> dict:
        """Calcule statut final + âge + alerte expiration."""
        donnees = r.get("donnees_extraites", {})
        verif   = r.get("verification", {})

        # Âge du titulaire
        dn = donnees.get("date_naissance")
        if dn:
            try:
                naissance    = date.fromisoformat(dn)
                today        = date.today()
                age          = today.year - naissance.year - (
                    (today.month, today.day) < (naissance.month, naissance.day)
                )
                donnees["age"] = age
                if age < 18:
                    r.setdefault("anomalies", []).append("Titulaire mineur (age < 18)")
                    r["recommandation"] = "REJETER"
            except ValueError:
                donnees["age"] = None

        # Jours avant expiration
        de = donnees.get("date_expiration")
        if de:
            try:
                exp   = date.fromisoformat(de)
                delta = (exp - date.today()).days
                donnees["jours_avant_expiration"] = delta
                if delta < 0:
                    r.setdefault("anomalies", []).append(f"CNI expirée depuis {abs(delta)} jours")
                    verif["non_expire"] = False
                elif delta < 30:
                    r.setdefault("anomalies", []).append(f"CNI expire dans {delta} jours")
            except ValueError:
                donnees["jours_avant_expiration"] = None

        # Score lisibilité
        checks_ok = sum(1 for v in verif.values() if v is True)
        total     = len(verif) or 1
        r["score_lisibilite"] = round(checks_ok / total, 2)

        # Statut couleur
        reco = r.get("recommandation", "")
        r["statut_couleur"] = {
            "APPROUVER"             : "success",
            "REJETER"               : "danger",
            "VERIFIER_MANUELLEMENT" : "warning",
        }.get(reco, "secondary")

        r["analyse_at"] = datetime.utcnow().isoformat()
        return r

    @staticmethod
    def _erreur(msg: str) -> dict:
        return {
            "succes" : False,
            "erreur" : msg,
            "analyse": None,
        }


# ─────────────────────────────────────────────────────
#  Singleton global
# ─────────────────────────────────────────────────────
verificateur_cni = VerificateurCNI()

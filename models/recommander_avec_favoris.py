# Dans ia_router.py — remplacer le endpoint /ia/recommander

@router.post("/ia/recommander")
def recommander(
    requete : RequeteRecommandation,
    db      : Session = Depends(get_db),
    _       : None    = Depends(verifier_api_key),
):
    annonces = fetch_annonces(db)
    if not annonces:
        return ReponseRecommandation(total=0, recommandations=[])

    requete_dict = requete.dict()

    # ── Personnalisation via favoris ─────────────────────────
    user_id = requete.user_id  # ajouter ce champ dans RequeteRecommandation
    if user_id:
        favoris = fetch_favoris_user(db, user_id)
        if favoris:
            # Déduire les préférences à partir des favoris
            categories = [f["categorie"] for f in favoris if f["categorie"]]
            villes     = [f["ville"]     for f in favoris if f["ville"]]
            prix_moyen = sum(f["prix"] for f in favoris if f["prix"]) / len(favoris)

            # Enrichir la requête si pas déjà précisé
            if not requete_dict.get("type_bien") and categories:
                from collections import Counter
                requete_dict["type_bien"] = Counter(categories).most_common(1)[0][0]

            if not requete_dict.get("ville") and villes:
                from collections import Counter
                requete_dict["ville"] = Counter(villes).most_common(1)[0][0]

            if not requete_dict.get("budget_max"):
                requete_dict["budget_max"] = prix_moyen * 1.3  # +30% de marge

    resultats = moteur.recommander(annonces, requete_dict)
    return ReponseRecommandation(
        total           = len(resultats),
        recommandations = resultats,
    )

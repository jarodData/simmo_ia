from sqlalchemy         import create_engine, text
from sqlalchemy.orm     import sessionmaker, Session
from config             import settings


DATABASE_URL = (
    "mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"
).format(
    user = settings.DB_USER,
    pwd  = settings.DB_PASSWORD,
    host = settings.DB_HOST,
    port = settings.DB_PORT,
    db   = settings.DB_NAME,
)
# ── Connexion MySQL ────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping   = True,   # vérifie la connexion avant usage
    pool_recycle    = 3600,   # recycle après 1h (évite MySQL gone away)
    pool_size       = 5,
    max_overflow    = 10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Annonces actives avec photo principale ─────────────────
def fetch_annonces(db: Session):
    try:
        sql = text("""
            SELECT
                a.id,
                a.titre,
                a.description,
                CAST(a.prix AS DECIMAL(15,2))  AS prix,
                a.surface_m2,
                a.nb_chambres,
                a.meuble,
                COALESCE(a.vues, 0)  AS vues,
                c.libelle AS categorie,
                l.ville,
                l.quartier,
                l.latitude,
                l.longitude,
                a.type_transaction,
                a.statut,
                a.id_agent  AS user_id ,
                p.chemin_image  AS photo
            FROM annonces a
            INNER JOIN categories_bien c ON a.id_categorie = c.id
            INNER JOIN localisations l ON a.id_localisation = l.id

            LEFT JOIN photos_annonces p
                ON  p.id_annonce = a.id
                AND p.est_principale = 1
            WHERE a.statut = 'active' 
            AND a.prix > 10000
            AND a.prix < 1000000 -- < 1 milliard
            AND a.surface_m2 > 10
            AND a.surface_m2 < 1000
            ORDER BY a.id DESC
        """)

        rows = db.execute(sql).mappings().fetchall()

        return [
            {
                "id"              : int(row["id"]),
                "titre"           : str(row["titre"] or ""),
                "description"     : str(row["description"] or ""),
                "prix"            : float(row["prix"] or 0),
                "categorie"       : str(row["categorie"] or ""),
                "ville"           : str(row["ville"] or ""),
                "quartier"        : row["quartier"] if row["quartier"] else "Inconnue",
                "surface_m2"      : float(row["surface_m2"]) if row["surface_m2"] else None,
                "nb_chambres"     : int(row["nb_chambres"])   if row["nb_chambres"] else None,
                "meuble"          : bool(row["meuble"]),
                "vues"            : int(row["vues"] or 0),
                "latitude"        : float(row["latitude"])    if row["latitude"]    else None,
                "longitude"       : float(row["longitude"])   if row["longitude"]   else None,
                "type_transaction": str(row["type_transaction"] or "location"),
                "user_id"         : int(row["user_id"]) if row["user_id"] else None,
                "photo"           : row["photo"],
            }
            for row in rows
        ]

    except Exception as e:
        print(f"Erreur fetch_annonces: {e}")
        return []


# ── Favoris d'un utilisateur (pour personnalisation IA) ───
def fetch_favoris_user(db: Session, user_id: int):
    try: 
        sql = text("""
            SELECT
                a.id_categorie,
                l.ville,
                a.type_transaction,
                CAST(a.prix AS DECIMAL(15,2)) AS prix
            FROM favoris f
            JOIN annonces a ON a.id = f.annonce_id
            WHERE f.user_id = :user_id
            ORDER BY f.created_at DESC
            LIMIT 20
        """)
        rows = db.execute(sql, {"user_id": user_id}).mappings().fetchall()
        return [dict(r) for r in rows]

    except Exception as e:
        print(f"Erreur fetch_favoris: {e}")
        return []


    
def fetch_historique_user(db, user_id):
    """Recupere l'historique de recherche d'un utilisateur"""
    query = text("""
        SELECT
            terme_recherche,
            filtres_appliques,
            created_at
        FROM historique_recherches
        WHERE id_user = :user_id
        ORDER BY created_at DESC
        LIMIT 20
    """)
    result   = db.execute(query, {"user_id": user_id})
    colonnes = list(result.keys())
    return [
        dict(zip(colonnes, row))
        for row in result.fetchall()
    ]

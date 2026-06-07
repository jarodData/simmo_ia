# update_photos.py
# Lance depuis : python update_photos.py
# Met à jour les photos Unsplash avec des images adaptées
# au marché immobilier camerounais

import pymysql
import random

# ── Connexion DB ─────────────────────────────────────────
# Remplace par tes vraies infos
DB = dict(
    host     = 'brfwtje2ac3dahuqpb1n-mysql.services.clever-cloud.com',
    port     = 3306,
    user     = 'undnyemxtheg4ikc',
    password = 'exYyhSJbqiAc2oo4lNEr',
    database = 'brfwtje2ac3dahuqpb1n',
    charset  = 'utf8mb4',
)



# ── Photos par catégorie ──────────────────────────────────
# Images Unsplash sélectionnées : immeubles africains,
# intérieurs adaptés, quartiers urbains d'Afrique centrale
PHOTOS = {
    'appartement': [
        'https://images.unsplash.com/photo-1574362848149-11496d93a7c7?w=800&q=80',
        'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80',
        'https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?w=800&q=80',
        'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80',
        'https://images.unsplash.com/photo-1555041469-a586c167d37f?w=800&q=80',
    ],
    'studio': [
        'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&q=80',
        'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
        'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800&q=80',
        'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&q=80',
    ],
    'villa': [
        'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&q=80',
        'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80',
        'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&q=80',
        'https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800&q=80',
        'https://images.unsplash.com/photo-1580587771525-78b9be663b27?w=800&q=80',
    ],
    'chambre': [
        'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80',
        'https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&q=80',
        'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800&q=80',
        'https://images.unsplash.com/photo-1588880331179-bc9b93a8cb5e?w=800&q=80',
    ],
    'bureau': [
        'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80',
        'https://images.unsplash.com/photo-1524758631624-e2822e304c36?w=800&q=80',
        'https://images.unsplash.com/photo-1497366754035-f200968a6e72?w=800&q=80',
        'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800&q=80',
    ],
    'terrain': [
        'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=800&q=80',
        'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
        'https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80',
    ],
    'default': [
        'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=800&q=80',
        'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80',
        'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80',
    ],
}


def get_photos_pour_categorie(categorie: str) -> list:
    cat = (categorie or '').lower().strip()
    for key in PHOTOS:
        if key in cat:
            return PHOTOS[key]
    return PHOTOS['default']


def main():
    conn = pymysql.connect(**DB)
    cur  = conn.cursor()

    # Récupérer toutes les photos avec la catégorie de l'annonce
    cur.execute("""
        SELECT p.id, p.chemin_image, p.est_principale,
               c.libelle AS categorie
        FROM photos_annonces p
        JOIN annonces a ON a.id = p.id_annonce
        JOIN categories_bien c ON c.id = a.id_categorie
        WHERE p.chemin_image LIKE '%unsplash%'
        ORDER BY p.id
    """)
    photos = cur.fetchall()
    print(f"📷 {len(photos)} photos Unsplash à mettre à jour...")

    # Garder un index par catégorie pour varier les images
    indices = {}
    updates = []

    for photo_id, chemin, est_principale, categorie in photos:
        liste = get_photos_pour_categorie(categorie)
        idx   = indices.get(categorie, 0)
        nouvelle_url = liste[idx % len(liste)]
        indices[categorie] = idx + 1
        updates.append((nouvelle_url, photo_id))

    # Mettre à jour en batch
    cur.executemany(
        "UPDATE photos_annonces SET chemin_image = %s WHERE id = %s",
        updates
    )
    conn.commit()
    print(f"✅ {len(updates)} photos mises à jour avec succès !")

    # Afficher un résumé par catégorie
    print("\nRésumé par catégorie :")
    for cat, idx in indices.items():
        print(f"  {cat}: {idx} photos")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
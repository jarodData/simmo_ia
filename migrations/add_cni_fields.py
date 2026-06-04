# migrations/add_cni_fields.py
# Alembic migration — ajout des champs CNI sur la table agents

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'cni_001'
down_revision = None   # remplacer par le hash de ta dernière migration
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('agents', sa.Column('cni_url',               sa.String(500), nullable=True))
    op.add_column('agents', sa.Column('cni_valide',            sa.Boolean(),   nullable=True, default=None))
    op.add_column('agents', sa.Column('cni_score_confiance',   sa.Float(),     nullable=True))
    op.add_column('agents', sa.Column('cni_recommandation',    sa.String(30),  nullable=True))
    op.add_column('agents', sa.Column('cni_motif_rejet',       sa.Text(),      nullable=True))
    op.add_column('agents', sa.Column('cni_decision_admin',    sa.String(20),  nullable=True))
    op.add_column('agents', sa.Column('cni_motif_admin',       sa.Text(),      nullable=True))
    op.add_column('agents', sa.Column('cni_verif_manuelle',    sa.Boolean(),   nullable=True, default=False))
    op.add_column('agents', sa.Column('cni_analyse_at',        sa.DateTime(),  nullable=True))
    # Données extraites stockées en JSON
    # PostgreSQL : JSONB  /  SQLite/MySQL : JSON ou Text
    try:
        op.add_column('agents', sa.Column('cni_donnees', JSONB, nullable=True))
    except Exception:
        op.add_column('agents', sa.Column('cni_donnees', sa.JSON(), nullable=True))


def downgrade():
    for col in [
        'cni_url', 'cni_valide', 'cni_score_confiance', 'cni_recommandation',
        'cni_motif_rejet', 'cni_decision_admin', 'cni_motif_admin',
        'cni_verif_manuelle', 'cni_analyse_at', 'cni_donnees',
    ]:
        op.drop_column('agents', col)

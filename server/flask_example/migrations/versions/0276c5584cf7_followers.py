"""followers

Revision ID: 0276c5584cf7
Revises: 44d510241054
Create Date: 2020-02-10 09:33:19.982649

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0276c5584cf7'
down_revision = '44d510241054'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('followers',
    sa.Column('follower_id', sa.Integer(), nullable=True),
    sa.Column('followed_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['followed_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['follower_id'], ['user.id'], )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('followers')
    # ### end Alembic commands ###

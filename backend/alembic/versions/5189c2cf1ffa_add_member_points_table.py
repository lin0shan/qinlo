"""add_member_points_table

Revision ID: 5189c2cf1ffa
Revises: 1542269914d5
Create Date: 2026-07-19 17:56:21.326126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5189c2cf1ffa'
down_revision: Union[str, Sequence[str], None] = '1542269914d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('member_points',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False, comment='会员ID'),
    sa.Column('brand', sa.String(length=50), nullable=False, comment='品牌名称'),
    sa.Column('points', sa.Integer(), nullable=True, comment='品牌积分'),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['member_id'], ['member.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('member_id', 'brand', name='uq_member_brand')
    )
    # 将旧积分迁移为赫莲娜品牌积分
    op.execute("""
        INSERT INTO member_points (member_id, brand, points, created_at, updated_at)
        SELECT id, '赫莲娜', COALESCE(points, 0), datetime('now'), datetime('now')
        FROM "member"
        WHERE COALESCE(points, 0) > 0
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('member_points')

"""add_member_coupon_table

Revision ID: 4fb2f8fd702e
Revises: 5189c2cf1ffa
Create Date: 2026-07-19 19:23:27.218302

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fb2f8fd702e'
down_revision: Union[str, Sequence[str], None] = '5189c2cf1ffa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('member_coupon',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('member_id', sa.Integer(), nullable=False, comment='会员ID'),
    sa.Column('brand', sa.String(length=50), nullable=False, comment='品牌名称'),
    sa.Column('coupon_name', sa.String(length=100), nullable=False, comment='兑换券名称'),
    sa.Column('product_id', sa.Integer(), nullable=True, comment='对应商品ID'),
    sa.Column('status', sa.String(length=20), nullable=True, comment='状态：有效/已兑换/已过期'),
    sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
    sa.Column('used_at', sa.DateTime(), nullable=True, comment='兑换时间'),
    sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['member_id'], ['member.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('member_coupon')

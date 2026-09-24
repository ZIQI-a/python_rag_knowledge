"""修复首次迁移遗漏的文档表结构。

Revision ID: 4be860334543
Revises: b1e713211789
Create Date: 2026-09-24 12:50:35.140731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '4be860334543'
down_revision: Union[str, Sequence[str], None] = 'b1e713211789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """重建首次迁移创建的空表，并创建完整文档与切片表。"""
    connection = op.get_bind()
    # 首次迁移只创建了无列的 documents 表；有数据时停止以避免丢失。
    has_rows = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM documents LIMIT 1)")
    ).scalar_one()
    if has_rows:
        raise RuntimeError("documents 表已有数据，需先制定数据迁移方案")

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.drop_table("documents")
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("storage_provider", sa.String(32), nullable=False),
        sa.Column("cos_bucket", sa.String(128), nullable=False),
        sa.Column("cos_object_key", sa.String(512), nullable=False),
        sa.Column("cos_region", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"], unique=True)

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("section_path", sa.String(1024), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_hash", sa.String(32), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_chunk_hash", "document_chunks", ["chunk_hash"])


def downgrade() -> None:
    """回退到首次迁移创建的无列 documents 表。"""
    op.drop_index("ix_document_chunks_chunk_hash", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_table("documents")
    op.create_table("documents")

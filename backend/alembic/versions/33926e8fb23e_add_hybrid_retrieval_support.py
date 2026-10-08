"""
zhparser 扩展中文检索,这里有自定义PostGRE Dockerfile安装建扩展加文本配置
Revision ID: 33926e8fb23e
Revises: f9942503a12c
Create Date: 2026-10-08 14:59:54.132667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '33926e8fb23e'
down_revision: Union[str, Sequence[str], None] = 'f9942503a12c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # zhparser 扩展由自定义Postgres Dockerfile安装，这里建扩展加文本搜索配置
    op.execute("CREATE EXTENSION IF NOT EXISTS zhparser")
    op.execute(
        "CREATE TEXT SEARCH CONFIGURATION chinese_zh (PARSER = zhparser)"
    )
    # 告诉 PostgreSQL 只把名词 / 动词 / 形容词 / 习用语 / 叹词 / 习惯用语这 6 类 token 拿来建索引，像【的、了、是】这种直接丢掉。
    op.execute(
        "ALTER TEXT SEARCH CONFIGURATION chinese_zh "
        "ADD MAPPING FOR n,v,a,i,e,l WITH simple"
    )
    #给切片表加一列，专门存放"切好的词"。
    op.execute(
        "ALTER TABLE document_chunks "
        "ADD COLUMN content_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('chinese_zh', content)) STORED"
    )

    # GIN 索引：tsvector 全文检索的标配；@@ 操作符走它做倒排查找
    # 指定索引算法是 GIN（专门服务多值列，比如"一行里有很多词"）
    op.execute(
        "CREATE INDEX ix_document_chunks_content_tsv "
        "ON document_chunks USING GIN (content_tsv)"
    )
    # 混合检索调试元数据落库：sources / vector_rank / keyword_rank / *_score / rrf_score
    # 选 JSONB 而不是拆列，因为后续 reranker 章节还会继续往里加字段，schema 不稳定时
    # JSONB 一次到位；这些字段也不参与 SQL 过滤 / 聚合，没必要走列存
    op.add_column(
        "answer_citations",
        sa.Column("retrieval_meta", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("answer_citations", "retrieval_meta")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS chinese_zh")
    op.execute("DROP EXTENSION IF EXISTS zhparser")

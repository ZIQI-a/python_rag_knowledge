""" 文档的数据模型 """
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    Float, Boolean, Index, Column, Table
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PGUUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base


class DocumentStatus(str, Enum):
    """文档生命周期状态。

    uploading: 已写入 COS、入库前
    parsing:   Docling 解析中
    indexing:  切分 + 向量化 + 写 chunks 中
    ready:     可被检索
    failed:    任意阶段失败
    """

    UPLOADING = "uploading"
    PARSING = "parsing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


# 文档表
class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        Index(
            "ix_documents_permission_tags",
            "permission_tags",
            postgresql_using="gin",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)

    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="cos")
    cos_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    cos_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    cos_region: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        String(32), nullable=False, default=DocumentStatus.UPLOADING
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 文档版本号，每次重新索引成功后加一，用于前端标识内容可见
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # 空数组视为公开; 非空数组与用户标签匹配(管理员为 * 通配符)
    permission_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String()), nullable=False, default=list, server_default="{}"
    )
    # 上传者
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    ingestion_tasks: Mapped[list["IngestionTask"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True,
        order_by="IngestionTask.created_at.desc()"
    )

# 文档切片
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    __table_args__ = (
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"}
        ),
        Index(
            "ix_document_chunks_content_tsv",
            "content_tsv",
            postgresql_using="gin",
        )
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dim), nullable=False)

    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    # 全文检索索引列，根据Content自动维护，只读
    content_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        #Computed(persisted=True) 会自动从 INSERT/UPDATE 中排除该列
        Computed("to_tsvector('chinese_zh', content)", persisted=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    document: Mapped[Document] = relationship(back_populates="chunks")

"""会话表,存储具体的历史会话信息"""
# 枚举值，用户、AI和系统提示词
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="新会话")
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )

""" 消息表 """
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[MessageRole] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    citations: Mapped[list["AnswerCitation"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="AnswerCitation.ordinal",
    )

""" 用于消息引用的Chunk快照,避免原来的引用被删除，在历史记录中展示 """
class AnswerCitation(Base):
    __tablename__ = "answer_citations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # 给大模型看的片段编号，从 1 开始
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True
    )
    chunk_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True
    )
    document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    # 混合检索调试源数据 sources 源 / vector_rank向量排名 / keyword_rank关键词排名
    # / *_score 向量或关键词的原始分数 / rrf_score 最终得分
    retrieval_meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    message: Mapped[Message] = relationship(back_populates="citations")

""" 评测run的表模型结构:共两张表，一张一次执行的结果，一张每次执行下的多种分支结果"""
# 评测程序执行的生命周期
class EvaluationRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class EvaluationRun(Base):
    """ 评测执行表 """
    __tablename__ = "evaluation_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EvaluationRunStatus] = mapped_column(String(16), nullable=False)

    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True) # 疑似造假分
    answer_relevancy: Mapped[float | None] = mapped_column(Float, nullable=True) # 答案相关性评分
    context_precision: Mapped[float | None] = mapped_column(Float, nullable=True) # 上下文精度评分
    context_recall: Mapped[float | None] = mapped_column(Float, nullable=True) # 上下文召回评分
    citation_hit_rate: Mapped[float | None] = mapped_column(Float, nullable=True) # 引用命中率
    refusal_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True) # 拒答正确率
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True) # 平均耗时(毫秒)
    # 首个token延迟
    avg_first_token_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),nullable=False)

    items: Mapped[list["EvaluationItem"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True # 不在应用层删，数据库层统一删除
    )

class EvaluationItem(Base):
    """ 评测中每条Case具体表, 输入快照实际输出指标，Case归因 """
    __tablename__ = "evaluation_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    expected_document_names: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    expected_keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    should_refuse: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    actual_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actual_refused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    retrieved_chunks_meta: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    query_route: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    agent_steps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verify_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_token_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 相关的指标:RAGIS四项任意一项异常会落None，前端缺失隐藏单元格
    faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_relevancy: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_hit: Mapped[bool | None] = mapped_column(Boolean, nullable=True) # 引用是否命中
    refusal_correct: Mapped[bool] = mapped_column(Boolean, nullable=True) # 拒答是否正确

    # Badcase归因表，规则自动初判
    is_bad_case: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False) # 是否坏案例
    bad_case_category: Mapped[str | None] = mapped_column(String(64), nullable=True) # 归因类别
    bad_case_note: Mapped[str | None] = mapped_column(Text, nullable=True) # 归因说明

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[EvaluationRun] = relationship(back_populates="items")

""" 用户和权限相关表 """

class UserStatus(str, Enum):
    """ 用户启用状态 """
    ACTIVE = "active"
    DISABLED = "disabled"

# 用户角色多对多关系表
# 不使用ORM类创建表，是本身没有业务字段,纯关系
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "role_id",
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

class User(Base):
    """ 用户表 """
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[UserStatus] = mapped_column(String(16), nullable=False, default=UserStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles_table,
        back_populates="users",
        lazy="selectin"
    )

class Role(Base):
    """ 权限表 """

    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    permission_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String()), nullable=False, default=list, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    users: Mapped[list[User]] = relationship(
        secondary=user_roles_table,
        back_populates="roles",
    )

""" Celery 异步任务相关类型 """

class IngestionTaskType(str, Enum):
    """入库任务类型。

    ingest:  首次入库（解析 → 切分 → 全量 embedding → 写入）
    reindex: 增量重建（按 chunk_hash 对齐，仅对变化 chunk 重新 embedding）
    """

    INGEST = "ingest"
    REINDEX = "reindex"

class IngestionTaskStatus(str, Enum):
    """Celery 任务生命周期。

    pending: 已入库表、还没被 worker 拉走
    running: worker 已开始执行
    success / failed: 终态
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

class IngestionTask(Base):
    """文档入库任务记录。

    Celery 拉起 worker 前先在 DB 落一条 pending 行；worker 内根据生命周期更新
    running → success/failed。前端轮询 documents 接口附带 `latest_task` 即可
    展示进度（progress_total / progress_done）与失败原因。
    """

    __tablename__ = "ingestion_tasks"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[IngestionTaskType] = mapped_column(String(16), nullable=False)
    status: Mapped[IngestionTaskStatus] = mapped_column(
        String(16), nullable=False, default=IngestionTaskStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 进度：reindex 时 total=新增 chunks 数，done=已 embedding 的批次累计
    # ingest 走全量 embedding，total=切分后总 chunks 数
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="ingestion_tasks")
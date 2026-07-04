# AutoPrism - SQLAlchemy Models
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Boolean, Integer, Float, Text, DateTime, ForeignKey, JSON, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SignalType(str, enum.Enum):
    PRICE_WAR = "PRICE_WAR"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    POLICY = "POLICY"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    NEGATIVE_PR = "NEGATIVE_PR"
    OTHER = "OTHER"


class IntelligenceStatus(str, enum.Enum):
    PENDING_AI = "PENDING_AI"
    PROCESSED = "PROCESSED"
    IGNORED_NOISE = "IGNORED_NOISE"


class RawIntelligence(Base):
    """脏数据接收池: 存放抓取回来的全网未结构化数据"""
    __tablename__ = "raw_intelligence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., 'Reuters', 'Weibo'
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[IntelligenceStatus] = mapped_column(Enum(IntelligenceStatus), default=IntelligenceStatus.PENDING_AI, index=True)
    target_panel_ids: Mapped[List[str]] = mapped_column(JSONB, default=list) # Tagging which panel this raw data belongs to
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    
    # Relations
    info_records: Mapped[List["IntelligenceInfo"]] = relationship(back_populates="raw_intelligence", cascade="all, delete-orphan")
    structured_signals: Mapped[List["StructuredSignal"]] = relationship(back_populates="raw_intelligence", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_raw_status", "status"),
        Index("idx_raw_published", "published_at"),
        Index("idx_raw_source", "source_name"),
    )


class IntelligenceInfo(Base):
    """
    INFO 数据库: 27 个面板展示信息的专属存储空间。
    AI 按照 UI 数据格式要求提取出的结构化数据存放在这里。
    """
    __tablename__ = "intelligence_info"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_intelligence.id", ondelete="CASCADE"), nullable=False)
    
    # UI 展示的核心元数据
    title_brief: Mapped[str] = mapped_column(String(255), nullable=False)
    target_panel_ids: Mapped[List[str]] = mapped_column(JSONB, default=list) # 路由到哪些面板
    
    # 核心指标与解读内容
    impact_score: Mapped[int] = mapped_column(Integer, default=50)
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    
    # 动态指标 (根据 27 个面板的需求提取的键值对)
    # 例如: {"brand": "Tesla", "model": "Model 3", "price_change": "-5%"}
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # 地理空间与实体信息
    geolocation: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    involved_entities: Mapped[List[str]] = mapped_column(JSONB, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relations
    raw_intelligence: Mapped["RawIntelligence"] = relationship(back_populates="info_records")

    __table_args__ = (
        Index("idx_info_panels", "target_panel_ids", postgresql_using="gin"),
        Index("idx_info_created", "created_at"),
    )


class StructuredSignal(Base):
    """[DEPRECATED] 请优先使用 IntelligenceInfo"""
    __tablename__ = "structured_signals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_intelligence.id", ondelete="CASCADE"), nullable=False)
    
    title_brief: Mapped[str] = mapped_column(String(255), nullable=False)  # AI condensed title
    summary: Mapped[List[str]] = mapped_column(JSONB, default=list)        # Array of bullet points
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType), default=SignalType.OTHER)
    
    impact_score: Mapped[int] = mapped_column(Integer, default=0)          # 0-100 severity/importance
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)           # -1.0 to 1.0
    
    # Spatial data for map engines
    geolocation: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True) # {"lat": 12.3, "lng": 45.6, "name": "Berlin"}
    
    involved_entities: Mapped[List[str]] = mapped_column(JSONB, default=list) # Array of company/product names
    
    # Visualization mappings
    target_panel_ids: Mapped[List[str]] = mapped_column(JSONB, default=list) # Panel IDs this signal belongs to
    metrics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)    # Extracted numbers for charts
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relations
    raw_intelligence: Mapped["RawIntelligence"] = relationship(back_populates="structured_signals")

    __table_args__ = (
        Index("idx_signal_type", "signal_type"),
        Index("idx_signal_score", "impact_score"),
        Index("idx_signal_created", "created_at"),
        Index("idx_signal_geolocation", "geolocation", postgresql_using="gin"),
        Index("idx_signal_entities", "involved_entities", postgresql_using="gin"),
    )


class VehicleModel(Base):
    """静态结构化资产: 车型动态对标库"""
    __tablename__ = "vehicle_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Flexible specs schema to handle rapid industry evolution
    specs: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("idx_vehicle_brand", "brand_name"),
        Index("idx_vehicle_specs", "specs", postgresql_using="gin"),
    )


class MarketTimeSeries(Base):
    """宏观脉搏: 大宗商品、销量等时序数据"""
    __tablename__ = "market_time_series"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. 'lithium_carbonate', 'cpca_weekly_sales'
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # e.g. 'CNY/Ton'
    
    __table_args__ = (
        Index("idx_market_indicator_time", "indicator_name", "timestamp", unique=True),
    )


class StrategicInsight(Base):
    """
    L3 战略洞察合成库 (AI Denoise 产物)
    基于不同角色进行跨面板融合分析的结果，用于地图展示
    """
    __tablename__ = "strategic_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String(50), index=True) # 所属角色 (Macro, SupplyChain 等)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text)
    
    # 核心分析包: 现状、影响、时效、规模
    analysis: Mapped[dict] = mapped_column(JSONB, default=dict)
    strategic_advice: Mapped[str] = mapped_column(Text)
    
    # 地图视觉逻辑
    display_type: Mapped[str] = mapped_column(String(50)) # 'HOTSPOT', 'FLOW', 'ZONE', 'RIPPLE', 'COMPARISON', 'SHIELD_UP', 'MARKER'
    geo_coordinates: Mapped[dict] = mapped_column(JSONB, default=dict) # 坐标、目的地、标签等
    
    priority: Mapped[int] = mapped_column(Integer, default=2) # 0-4
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    affected_panels: Mapped[List[str]] = mapped_column(JSONB, default=list) # 关联的面板 ID 列表
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("idx_insight_role", "role"),
        Index("idx_insight_created", "created_at"),
    )

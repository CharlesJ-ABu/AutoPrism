# Tech Nebula - Pydantic Schemas
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ============== Auth ==============
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    ai_quota_used: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user_id


# ============== DataSource ==============
class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(rss|api|webpage|coze|ota)$")
    url: str = Field(..., min_length=1)
    config: dict = Field(default_factory=dict)
    global_cache_timeout: int = Field(default=3600, ge=60, le=86400)
    tag_ids: Optional[List[UUID]] = []


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    config: Optional[dict] = None
    global_cache_timeout: Optional[int] = Field(None, ge=60, le=86400)
    tag_ids: Optional[List[UUID]] = None


class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    type: str
    url: str
    config: dict
    schema_template: Optional[dict]
    global_cache_timeout: int
    tags: List["TagResponse"] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Subscription ==============
class SubscribeRequest(BaseModel):
    poll_interval: int = Field(default=3600, ge=300, le=86400)


class SubscriptionResponse(BaseModel):
    id: UUID
    user_id: UUID
    data_source_id: UUID
    poll_interval: int
    is_active: bool
    data_source: DataSourceResponse
    panel: Optional["PanelResponse"] = None

    class Config:
        from_attributes = True


# ============== Panel ==============
class PanelCreate(BaseModel):
    data_source_id: Optional[UUID] = None
    tag: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)
    type: str = Field(default="list", pattern="^(list|number|ai_summary)$")
    size: str = Field(default="1x1", pattern="^(1x1|2x1|2x2)$")
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0, "w": 1, "h": 1})


class PanelUpdate(BaseModel):
    tag: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, pattern="^(list|number|ai_summary)$")
    size: Optional[str] = Field(None, pattern="^(1x1|2x1|2x2)$")
    position: Optional[dict] = None
    is_visible: Optional[bool] = None


class PanelResponse(BaseModel):
    id: UUID
    user_id: UUID
    data_source_id: Optional[UUID]
    tag: Optional[str]
    title: Optional[str]
    type: str
    size: str
    position: dict
    is_visible: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Layout ==============
class LayoutSnapshotCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    layout_config: dict
    is_default: bool = False


class LayoutSnapshotResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: Optional[str]
    layout_config: dict
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Feed ==============
class FeedItem(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    tags: List[str] = []
    source_name: str


class FeedResponse(BaseModel):
    items: List[FeedItem]
    data_source_id: UUID
    fetched_at: Optional[datetime] = None


# ============== Tag Management ==============
class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=20)
    hotness: Optional[int] = Field(None, ge=0)


# ============== FeedItem ==============
class FeedItemResponse(BaseModel):
    id: UUID
    data_source_id: UUID
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    tags: List[str] = []
    fetched_at: datetime

    class Config:
        from_attributes = True


# ============== Tag ==============
class TagResponse(BaseModel):
    id: UUID
    name: str
    category: Optional[str]
    color: Optional[str]
    hotness: int
    article_count: int = 0

    class Config:
        from_attributes = True


# ============== AI ==============
class AIInterpretRequest(BaseModel):
    content: str = Field(..., min_length=10)
    context: Optional[str] = None
    prompt_template: Optional[str] = None


class AIInterpretResponse(BaseModel):
    cache_key: str
    interpretation: dict
    cached: bool


# ============== Crawl ==============
class CrawlTriggerResponse(BaseModel):
    task_id: str
    status: str
    message: str


# Forward refs
DataSourceResponse.model_rebuild()
SubscriptionResponse.model_rebuild()

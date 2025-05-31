# src/api/models.py
from pydantic import BaseModel
from typing import Optional

class UpdateCategoryRequest(BaseModel):
    category: str

class CreateCategoryRequest(BaseModel):
    name: str

class UpdateSettingsRequest(BaseModel):
    auto_classify: Optional[bool] = None
    classify_schedule: Optional[str] = None
    classify_time: Optional[str] = None
    retention_days: Optional[int] = None
    enable_sensitive_detection: Optional[bool] = None
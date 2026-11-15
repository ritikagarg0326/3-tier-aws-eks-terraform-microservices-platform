from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Category = Literal["movie", "tv_show", "web_series", "other"]


class ContentIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    genre: str = Field(min_length=1, max_length=50)
    language: str = Field(min_length=1, max_length=50)
    release_year: int = Field(ge=1888, le=2100)
    duration_minutes: int = Field(gt=0, le=6000)
    category: Category
    maturity_rating: str = Field(default="U/A 13+", min_length=1, max_length=10)
    is_featured: bool = False

    @field_validator("title", "description", "genre", "language", "maturity_rating")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class ContentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    genre: str | None = Field(default=None, min_length=1, max_length=50)
    language: str | None = Field(default=None, min_length=1, max_length=50)
    release_year: int | None = Field(default=None, ge=1888, le=2100)
    duration_minutes: int | None = Field(default=None, gt=0, le=6000)
    category: Category | None = None
    maturity_rating: str | None = Field(default=None, min_length=1, max_length=10)
    is_featured: bool | None = None


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    genre: str
    language: str
    release_year: int
    duration_minutes: int
    category: str
    maturity_rating: str
    is_featured: bool
    created_at: datetime
    updated_at: datetime


class Facets(BaseModel):
    genres: list[str]
    languages: list[str]
    categories: list[str]
    years: list[int]


class ContentStats(BaseModel):
    total: int
    featured: int
    added_last_7_days: int
    by_category: dict[str, int]
    by_genre: dict[str, int]
    by_language: dict[str, int]

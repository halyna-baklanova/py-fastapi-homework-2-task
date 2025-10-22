from datetime import date
import datetime
from enum import Enum
from typing import Annotated, List, Optional, Any

from pydantic import BaseModel, Field


class GenreResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class CountryResponseSchema(BaseModel):
    id: int
    code: str
    name: Optional[str]

    model_config = {"from_attributes": True}


class ActorResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class LanguageResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    overview: str | None = None
    date: datetime.date
    score: float | None = None

    model_config = {"from_attributes": True}


class MovieDetailSchema(MovieListItemSchema):
    budget: float | None = None
    revenue: float | None = None
    status: str | None = None
    languages: list[LanguageResponseSchema] = Field(default_factory=list)
    actors: list[ActorResponseSchema] = Field(default_factory=list)
    genres: list[GenreResponseSchema]
    country: Optional[CountryResponseSchema] = None


class MovieListResponseSchema(BaseModel):
    movies: list[MovieListItemSchema]
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    total_pages: int
    total_items: int

    model_config = {"from_attributes": True}


class StatusEnum(str, Enum):
    released = "Released"
    post_production = "Post Production"
    in_product = "In Production"


class CountryEnum(str, Enum):
    USA = "US"
    UKR = "AU"
    POL = "GB"


class MovieCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    date: datetime.date
    score: float = Field(..., ge=0, le=100)
    overview: str = Field(max_length=1000)
    status: StatusEnum | None = None
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: CountryEnum | None = None
    genres: List[str] = Field(default_factory=list)
    actors: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)


class MoviePartialUpdateSchema(BaseModel):
    name: Annotated[str | None, Field(max_length=255, default=None)]
    date: Annotated[date | None, Field(default=None)]
    score: Annotated[float | None, Field(ge=0, le=100, default=None)]
    overview: str | None = None
    status: StatusEnum | None = None
    budget: Annotated[float | None, Field(ge=0, default=None)]
    revenue: Annotated[float | None, Field(ge=0, default=None)]


class MoviePartialUpdateSuccessSchema(BaseModel):
    detail: str

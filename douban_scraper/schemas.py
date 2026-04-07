"""Data schemas for Douban scraper."""

from pydantic import BaseModel, Field


class BookCatalogItem(BaseModel):
    title: str = Field(description="Book title")
    url: str = Field(description="Book Douban subject URL")


class BookCatalogResult(BaseModel):
    kind: str = Field(description="Catalog kind")
    total: int = Field(description="Total books found")
    books: list[BookCatalogItem] = Field(default_factory=list, description="List of books")


class BookDetail(BaseModel):
    title: str = Field(description="Book title")
    url: str = Field(description="Book Douban subject URL")
    rating: float = Field(0.0, description="Book rating out of 10")
    votes: int = Field(0, description="Number of ratings")
    info: str = Field(description="Detailed publishing info string")
    intro: str = Field(description="Book introduction/summary")

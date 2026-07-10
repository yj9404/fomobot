from datetime import date

from pydantic import BaseModel


class NewsArticle(BaseModel):
    title: str
    link: str
    published_at: date


class ComplexNewsResponse(BaseModel):
    complex_key: str
    articles: list[NewsArticle]

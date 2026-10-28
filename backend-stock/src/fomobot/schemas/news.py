from datetime import date

from pydantic import BaseModel


class NewsArticle(BaseModel):
    title: str
    link: str
    published_at: date


class StockNewsResponse(BaseModel):
    ticker: str
    articles: list[NewsArticle]


class TossNewsArticle(BaseModel):
    title: str
    source: str
    url: str
    published_at: date


class TossNewsResponse(BaseModel):
    ticker: str
    articles: list[TossNewsArticle]

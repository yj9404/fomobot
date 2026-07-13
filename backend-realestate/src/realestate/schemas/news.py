from datetime import date
from typing import Literal

from pydantic import BaseModel


class NewsArticle(BaseModel):
    title: str
    link: str
    published_at: date


class ComplexNewsResponse(BaseModel):
    complex_key: str
    # 이 뉴스는 "단지 뉴스"가 아니라 단지가 속한 동/구의 최근 소식이다.
    # region_label/granularity가 None이면 뉴스 없음(articles도 빈 배열).
    region_label: str | None = None
    granularity: Literal["dong", "gu"] | None = None
    articles: list[NewsArticle]

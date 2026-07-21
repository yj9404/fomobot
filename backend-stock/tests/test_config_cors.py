import pytest
from pydantic import ValidationError
from fomobot.config import Settings

def test_cors_production_rejects_localhost():
    with pytest.raises(ValidationError, match="Localhost origins are not allowed in production"):
        Settings(app_env="production", allowed_origins="http://localhost:5173")

def test_cors_production_accepts_valid():
    s = Settings(app_env="production", allowed_origins="https://fomobot.vercel.app")
    assert s.allowed_origins == "https://fomobot.vercel.app"

def test_cors_dev_accepts_localhost():
    s = Settings(app_env="development", allowed_origins="http://localhost:5173")
    assert s.allowed_origins == "http://localhost:5173"

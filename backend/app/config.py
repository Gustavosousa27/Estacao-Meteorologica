from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    db_host: str = 'db'
    db_name: str = 'weather'
    db_user: str = 'weather'
    db_password: str = ''
    database_url: str | None = None
    admin_username: str = 'admin'
    admin_password: str = Field(min_length=16)
    offline_seconds: int = Field(default=90, ge=30)
    interface_timezone: str = 'America/Sao_Paulo'

    @property
    def url(self):
        return self.database_url or URL.create('mysql+pymysql', username=self.db_user,
            password=self.db_password, host=self.db_host, database=self.db_name,
            query={'charset': 'utf8mb4'})

@lru_cache
def settings():
    return Settings()

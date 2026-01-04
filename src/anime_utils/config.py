from email.policy import HTTP
from functools import cache
from typing import Optional

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict, YamlConfigSettingsSource


class RateLimitSettings(BaseSettings):
    max_rate: int
    time_period: int


class RetrySettings(BaseSettings):
    max_attempts: int = 1
    backoff_factor: float = 1
    initial_delay: float = 1


class HTTPClientSettings(BaseSettings):
    cookies_file: Optional[str] = None
    socks_url: Optional[str] = None
    rate_limit: RateLimitSettings = RateLimitSettings(max_rate=3, time_period=10)
    retry_settings: RetrySettings = RetrySettings()

    model_config = SettingsConfigDict(env_nested_delimiter="__", nested_model_default_partial_update=True)


class AniDBScraperSettings(HTTPClientSettings):
    rate_limit: RateLimitSettings = RateLimitSettings(max_rate=3, time_period=10)


class IDsMoeClientSettings(HTTPClientSettings):
    api_key: str
    cache_db_name: str = "idsmoe.db"
    cache_ttl: float = 60 * 60 * 24

    model_config = SettingsConfigDict(env_nested_delimiter="__", nested_model_default_partial_update=True)


class ShikimoriClientSettings(HTTPClientSettings):
    cache_db_name: str = "shikimori.db"
    cache_ttl: float = 60 * 60 * 24

    model_config = SettingsConfigDict(env_nested_delimiter="__", nested_model_default_partial_update=True)


class LocalSettings(BaseSettings):
    xml_path: Optional[str] = None
    pickle_path: Optional[str] = None


class Settings(BaseSettings):
    cache_dir: str = "~/.cache/anime-utils"
    anidb_scraper_settings: AniDBScraperSettings = AniDBScraperSettings()
    idsmoe_client_settings: IDsMoeClientSettings
    shikimori_client_settings: ShikimoriClientSettings = ShikimoriClientSettings()
    mal_client_settings: HTTPClientSettings = HTTPClientSettings()
    local_settings: LocalSettings = LocalSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            YamlConfigSettingsSource(settings_cls=settings_cls, yaml_file="anime-utils-config.yaml"),
            env_settings,
            file_secret_settings,
        )


@cache
def get_settings() -> Settings:
    return Settings()  # type: ignore

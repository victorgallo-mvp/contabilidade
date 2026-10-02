from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost/contabilidade_pedro"
    secret_key: str = "troque-em-producao"
    access_token_expire_minutes: int = 525600  # 1 ano, sem relogin
    cors_origins: str = "http://localhost:5173"

    # superadmin inicial (criado no primeiro boot se não existir)
    admin_username: str = "pedro"
    admin_password: str = "pedro123"
    admin_nome: str = "Pedro"

    # regras de negócio
    dia_corte_padrao: int = 10  # dia do mês seguinte à competência

    # armazenamento: local | drive
    storage_backend: str = "local"
    local_storage_dir: str = "./storage"
    drive_root_folder_id: str = ""
    google_service_account_json: str = ""  # conteúdo JSON da service account

    # IA (opcional; se vazio, a leitura do PDF é pulada)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"

    # URL pública do frontend (usada nos links do portal enviados por WhatsApp)
    frontend_url: str = "http://localhost:5173"

    @property
    def sqlalchemy_url(self) -> str:
        # Railway entrega postgresql://...; o driver psycopg3 precisa do prefixo explícito
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic va chercher automatiquement la variable OLLAMA_HOST
    # Si elle n'est pas dans le .env ou l'environnement, une erreur sera levée au démarrage.
    OLLAMA_HOST: str
    LLM_MODEL: str
    VLM_MODEL: str

    # Configuration du chargement du fichier .env (Nouvelle syntaxe Pydantic v2)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instanciation : tout est chargé et validé magiquement !
settings = Settings()

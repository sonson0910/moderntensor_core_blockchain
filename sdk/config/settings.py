# sdk/config/settings.py

import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pycardano import Network

class Settings(BaseSettings):
    """
    Centralized project settings using pydantic-settings (Pydantic >= 2.0).

    This class:
      - Maps environment variables via `alias=...` (instead of the deprecated `env=...`).
      - Uses `field_validator(..., mode="before")` instead of `@validator(pre=True)`.
      - Automatically loads from a .env file if you choose to enable it in `model_config`.

    Usage:
      - Instantiate `settings = Settings()` once.
      - Import `settings` throughout the project to access configuration (e.g. `settings.BLOCKFROST_PROJECT_ID`).
    """

    # This model_config specifies how pydantic-settings should handle extra environment variables,
    # and whether to automatically load a .env file, etc.
    model_config = SettingsConfigDict(
        extra="ignore",   # Ignore any unused environment variables
        env_file=".env",  # Loads environment variables from .env if needed
        env_file_encoding="utf-8",
    )

    # Environment-based or default values. 
    # Using alias="..." maps each class field to an environment variable.
    BLOCKFROST_PROJECT_ID: str = Field(
        default="preprod06dzhzKlynuTInzvxHDH5cXbdHo524DE",
        alias="BLOCKFROST_PROJECT_ID"
    )
    HOTKEY_BASE_DIR: str = Field(default="moderntensor", alias="HOTKEY_BASE_DIR")
    COLDKEY_NAME: str = Field(default="kickoff", alias="COLDKEY_NAME")
    HOTKEY_NAME: str = Field(default="hk1", alias="HOTKEY_NAME")
    HOTKEY_PASSWORD: str = Field(default="sonlearn2003", alias="HOTKEY_PASSWORD")

    TEST_RECEIVER_ADDRESS: str = Field(
        default="addr_test1qpkxr3kpzex93m646qr7w82d56md2kchtsv9jy39dykn4cmcxuuneyeqhdc4wy7de9mk54fndmckahxwqtwy3qg8pums5vlxhz",
        alias="TEST_RECEIVER_ADDRESS"
    )
    TEST_POLICY_ID_HEX: str = Field(
        default="b9107b627e28700da1c5c2077c40b1c7d1fe2e9b23ff20e0e6b8fec1",
        alias="TEST_POLICY_ID_HEX"
    )

    CARDANO_NETWORK: str = Field(default="TESTNET", alias="CARDANO_NETWORK")
    """
    Accepts "MAINNET" or "TESTNET" as strings. We use a validator to convert it
    into pycardano.Network when the settings are instantiated.
    """

    @field_validator("CARDANO_NETWORK", mode="before")
    def validate_network(cls, value: str):
        """
        Convert the 'CARDANO_NETWORK' field from a string into pycardano.Network.
        If the string is "MAINNET", we set it to Network.MAINNET; otherwise, we
        default to Network.TESTNET.
        """
        normalized = str(value).upper().strip()
        if normalized == "MAINNET":
            return Network.MAINNET
        return Network.TESTNET


# Create a single instance of Settings to import elsewhere in the project
settings = Settings()

# ----------------------------------------------------------------------------
# LOGGING CONFIGURATION - Customize as needed for your entire project
# ----------------------------------------------------------------------------
LOG_LEVEL = logging.INFO

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        # Uncomment below if you want to log to a file as well:
        # logging.FileHandler("project.log", mode="a"),
    ]
)
logger = logging.getLogger(__name__)
logger.info("Settings loaded via pydantic-settings for Pydantic 2.x.")

import os
from pathlib import Path
from typing import Any

import rootutils
from dotenv import load_dotenv
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

# Setup root directory
ROOT_DIR = rootutils.setup_root(search_from=os.getcwd(), indicator=['.project-root'], pythonpath=True)

# Load .env only in local development (not in Kubernetes)
# In Kubernetes, environment variables are injected via ConfigMap and Secret
if not os.getenv('IS_IN_KUBERNETES'):
    env_file = ROOT_DIR / '.env'
    if env_file.exists():
        load_dotenv(env_file)

# Load main config YAML once
CONFIG_PATH = ROOT_DIR / "configs" / "main_config.yaml"
YAML_CONFIG = {}
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        YAML_CONFIG = yaml.safe_load(f) or {}

# Load BioNexus config YAML once
BIONEXUS_CONFIG_PATH = ROOT_DIR / "configs" / "bio_nexus.yaml"
BIONEXUS_CONFIG = {}
if BIONEXUS_CONFIG_PATH.exists():
    with open(BIONEXUS_CONFIG_PATH, 'r', encoding='utf-8') as f:
        BIONEXUS_CONFIG = yaml.safe_load(f) or {}

# Load Kafka config YAML once
KAFKA_CONFIG_PATH = ROOT_DIR / "configs" / "kafka.yaml"
KAFKA_CONFIG = {}
if KAFKA_CONFIG_PATH.exists():
    with open(KAFKA_CONFIG_PATH, 'r', encoding='utf-8') as f:
        KAFKA_CONFIG = yaml.safe_load(f) or {}

# Load base configs from configs/base/ directory
BASE_CONFIG_DIR = ROOT_DIR / "configs" / "base"
APP_BASE_CONFIG = {}
LLM_BASE_CONFIG = {}
DATABASE_BASE_CONFIG = {}
SOA_BASE_CONFIG = {}
OSS_BASE_CONFIG = {}

if BASE_CONFIG_DIR.exists():
    app_config_path = BASE_CONFIG_DIR / "app.yaml"
    if app_config_path.exists():
        with open(app_config_path, 'r', encoding='utf-8') as f:
            APP_BASE_CONFIG = yaml.safe_load(f) or {}

    llm_config_path = BASE_CONFIG_DIR / "llm.yaml"
    if llm_config_path.exists():
        with open(llm_config_path, 'r', encoding='utf-8') as f:
            LLM_BASE_CONFIG = yaml.safe_load(f) or {}

    database_config_path = BASE_CONFIG_DIR / "database.yaml"
    if database_config_path.exists():
        with open(database_config_path, 'r', encoding='utf-8') as f:
            DATABASE_BASE_CONFIG = yaml.safe_load(f) or {}

    soa_config_path = BASE_CONFIG_DIR / "soa.yaml"
    if soa_config_path.exists():
        with open(soa_config_path, 'r', encoding='utf-8') as f:
            SOA_BASE_CONFIG = yaml.safe_load(f) or {}

    oss_config_path = BASE_CONFIG_DIR / "oss.yaml"
    if oss_config_path.exists():
        with open(oss_config_path, 'r', encoding='utf-8') as f:
            OSS_BASE_CONFIG = yaml.safe_load(f) or {}

# Load SOA Builder env for source database config
SOA_BUILDER_ENV = {}
SOA_BUILDER_ENV_PATH = ROOT_DIR / '.soa_builder_env'
if SOA_BUILDER_ENV_PATH.exists():
    with open(SOA_BUILDER_ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                SOA_BUILDER_ENV[key.strip()] = value.strip()

def load_config(file_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

class Settings(BaseSettings):
    """Simple settings - just merge .env and YAML"""
    IS_IN_KUBERNETES: bool = False  # If running in Kubernetes

    # Target Database - PostgreSQL (from .env)
    DATABASE_URL: str | None = None

    # PostgreSQL specific settings (target database)
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_SSL: bool = False  # SSL mode for PostgreSQL connection

    # Source Database - SOA Builder (from .soa_builder_env)
    SOURCE_HOST: str | None = None
    SOURCE_PORT: int = 5432
    SOURCE_DB: str | None = None
    SOURCE_USER: str | None = None
    SOURCE_PASSWORD: str | None = None
    SOURCE_SEARCH_PATH: str | None = None
    SOURCE_POOLING: bool = True
    SOURCE_MIN_POOL_SIZE: int = 1
    SOURCE_MAX_POOL_SIZE: int = 20
    SOURCE_COMMAND_TIMEOUT: int = 15
    SOURCE_TIMEOUT: int = 15
    
    # LLM Providers
    AZURE_ENABLED: bool = True
    DATABRICKS_ENABLED: bool = True
    DEEPSEEK_ENABLED: bool = True

    # Azure GPT-4.1
    GPT_4_1_LLM_MODEL_NAME: str | None = None
    GPT_4_1_LLM_DEPLOYMENT_NAME: str | None = None
    GPT_4_1_LLM_AZURE_ENDPOINT: str | None = None
    GPT_4_1_LLM_OPENAI_API_VERSION: str | None = None
    GPT_4_1_OPENAI_API_KEY: str | None = None

    # Databricks
    DATABRICKS_TOKEN: str | None = None
    DATABRICKS_BASE_URL: str | None = None
    DATABRICKS_LLM_MODEL_NAME: str | None = None

    # DeepSeek
    DEEPSEEK_MODEL_NAME: str | None = None
    DEEPSEEK_BASE_URL: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    
    # Embedding
    EMBEDDING_KEY: str | None = None
    EMBEDDING_MODEL_NAME: str | None = None
    EMBEDDING_AZURE_ENDPOINT: str | None = None
    EMBEDDING_DEPLOYMENT: str | None = None
    EMBEDDING_OPENAI_API_VERSION: str | None = None
    
    # SOA Builder API
    SOA_API_TOKEN: str | None = None
    ESOA_TABLE_API: str | None = None  # Dev environment URL
    KUBERNETE_ESOA_TABLE_URL: str | None = None  # K8s environment URL (internal service)
    SOA_API_BASE_URL: str | None = None

    # BioNexus API
    BIONEXUS_ACCESS_TOKEN: str | None = None
    BIONEXUS_ACCESS_TOKEN_CRF_GENERATION: str | None = None

    # Kafka Settings (defaults from kafka.yaml, can be overridden by env vars)
    KAFKA_BOOTSTRAP_SERVERS: str = "service-beone-kafka:9092"
    KAFKA_INPUT_TOPIC: str = "protocolbuilder.study-protocol-uploaded"
    KAFKA_OUTPUT_TOPIC: str = "protocolbuilder.protocol-processing-status"
    KAFKA_GROUP_ID: str = "crf-generation-service"
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"
    KAFKA_ENABLE_AUTO_COMMIT: bool = False
    KAFKA_MAX_POLL_RECORDS: int = 1
    KAFKA_SESSION_TIMEOUT_MS: int = 30000
    KAFKA_HEARTBEAT_INTERVAL_MS: int = 10000
    KAFKA_POLL_TIMEOUT_MS: int = 1000
    KAFKA_MAX_RETRIES: int = 3

    # Kafka Security (optional)
    KAFKA_SECURITY_PROTOCOL: str | None = None
    KAFKA_SASL_MECHANISM: str | None = None
    KAFKA_SASL_USERNAME: str | None = 'user1'
    KAFKA_SASL_PASSWORD: str | None = 'WZY2ihF8ik'

    # OSS Settings
    OSS_PROVIDER: str = "aws"
    OSS_ENDPOINT: str = "http://service-beone-file-service:80"
    OSS_BUCKET: str = "protocol-files"
    OSS_ACCESS_KEY_ID: str | None = None
    OSS_ACCESS_KEY_SECRET: str | None = None
    OSS_DOWNLOAD_DIR: str = "data/downloads"
    OSS_UPLOAD_DIR: str = "data/output"
    OSS_TIMEOUT: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

    def _prepare_yaml_defaults(self) -> dict[str, Any]:
        """
        Prepare default values from YAML configs.
        Only for NON-SENSITIVE values (sensitive values MUST come from .env).
        Priority: .env > configs/base/*.yaml > defaults
        """
        defaults = {}

        # App settings
        app = APP_BASE_CONFIG.get('app', {})
        defaults['APP_NAME'] = app.get('name', 'CRFGeneration')
        defaults['APP_VERSION'] = app.get('version', '1.0.0')
        defaults['DEBUG'] = app.get('debug', False)

        server = app.get('server', {})
        defaults['HOST'] = server.get('host', '0.0.0.0')
        defaults['PORT'] = server.get('port', 18000)

        # Feature flags
        features = app.get('features', {})
        defaults['USE_SQLITE_DB'] = features.get('use_sqlite_db', False)
        defaults['OLLAMA_ENABLED'] = features.get('ollama_enabled', False)
        defaults['OLLAMA_MODEL_NAME'] = features.get('ollama_model_name', 'gpt-oss:latest')

        # Database settings (NON-SENSITIVE)
        # Note: POSTGRES_SSL is environment-specific, loaded from .env only
        db = DATABASE_BASE_CONFIG.get('database', {})
        postgres = db.get('postgres', {})
        defaults['POSTGRES_HOST'] = postgres.get('host')
        defaults['POSTGRES_PORT'] = postgres.get('port', 5432)
        defaults['POSTGRES_DB'] = postgres.get('database')
        defaults['POSTGRES_USER'] = postgres.get('user')

        # LLM settings (NON-SENSITIVE: endpoints, model names, versions)
        llm = LLM_BASE_CONFIG.get('llm', {})

        # OpenAI API type
        defaults['OPENAI_API_TYPE'] = llm.get('openai_api_type', 'azure')

        # Databricks (no token)
        databricks = llm.get('databricks', {})
        defaults['DATABRICKS_BASE_URL'] = databricks.get('base_url')
        defaults['DATABRICKS_HOST'] = databricks.get('host')
        defaults['DATABRICKS_LLM_MODEL_NAME'] = databricks.get('model_name')

        # GPT-4.1 (no key)
        gpt_4_1 = llm.get('gpt_4_1', {})
        defaults['GPT_4_1_LLM_MODEL_NAME'] = gpt_4_1.get('model_name')
        defaults['GPT_4_1_LLM_DEPLOYMENT_NAME'] = gpt_4_1.get('deployment_name')
        defaults['GPT_4_1_LLM_AZURE_ENDPOINT'] = gpt_4_1.get('azure_endpoint')
        defaults['GPT_4_1_LLM_OPENAI_API_VERSION'] = gpt_4_1.get('api_version')

        # O4-Mini (no key)
        o4_mini = llm.get('o4_mini', {})
        defaults['O4_MINI_LLM_MODEL_NAME'] = o4_mini.get('model_name')
        defaults['O4_MINI_LLM_DEPLOYMENT_NAME'] = o4_mini.get('deployment_name')
        defaults['O4_MINI_LLM_AZURE_ENDPOINT'] = o4_mini.get('azure_endpoint')
        defaults['O4_MINI_LLM_OPENAI_API_VERSION'] = o4_mini.get('api_version')

        # GPT-4o (no key)
        gpt_4o = llm.get('gpt_4o', {})
        defaults['GPT_4O_LLM_MODEL_NAME'] = gpt_4o.get('model_name')
        defaults['GPT_4O_LLM_DEPLOYMENT_NAME'] = gpt_4o.get('deployment_name')
        defaults['GPT_4O_LLM_AZURE_ENDPOINT'] = gpt_4o.get('azure_endpoint')
        defaults['GPT_4O_LLM_OPENAI_API_VERSION'] = gpt_4o.get('api_version')

        # DeepSeek (no key)
        deepseek = llm.get('deepseek', {})
        defaults['DEEPSEEK_MODEL_NAME'] = deepseek.get('model_name')
        defaults['DEEPSEEK_BASE_URL'] = deepseek.get('base_url')

        # Embedding (no key)
        embedding = llm.get('embedding', {})
        defaults['EMBEDDING_MODEL_NAME'] = embedding.get('model_name')
        defaults['EMBEDDING_AZURE_ENDPOINT'] = embedding.get('azure_endpoint')
        defaults['EMBEDDING_DEPLOYMENT'] = embedding.get('deployment')
        defaults['EMBEDDING_OPENAI_API_VERSION'] = embedding.get('api_version')

        # SOA settings (NON-SENSITIVE: endpoints)
        soa = SOA_BASE_CONFIG.get('soa', {})
        api = soa.get('api', {})
        defaults['ESOA_TABLE_API'] = api.get('table_api')
        defaults['SOA_API_BASE_URL'] = api.get('base_url')

        # OSS settings (NON-SENSITIVE)
        oss = OSS_BASE_CONFIG.get('oss', {})
        defaults['OSS_PROVIDER'] = oss.get('provider', 'aws')
        defaults['OSS_ENDPOINT'] = oss.get('endpoint', 'http://service-beone-file-service:80')
        defaults['OSS_BUCKET'] = oss.get('bucket', 'protocol-files')

        directories = oss.get('directories', {})
        defaults['OSS_DOWNLOAD_DIR'] = directories.get('download', 'data/downloads')
        defaults['OSS_UPLOAD_DIR'] = directories.get('upload', 'data/output')
        defaults['OSS_TIMEOUT'] = oss.get('timeout', 300)

        return defaults

    def __init__(self, **kwargs):
        # ====================================================================
        # Step 1: Initialize Pydantic FIRST (loads .env and env vars)
        # Priority: env vars > .env > kwargs > defaults
        # ====================================================================
        super().__init__(**kwargs)

        # ====================================================================
        # Step 2: Fill in missing values from YAML (only if not already set)
        # ====================================================================
        yaml_defaults = self._prepare_yaml_defaults()
        for key, value in yaml_defaults.items():
            # Only use YAML value if attribute is None or not set
            if not hasattr(self, key) or getattr(self, key) is None:
                setattr(self, key, value)

        # ====================================================================
        # Step 3: Post-processing (existing logic)
        # ====================================================================
        # Set all path attributes directly
        self.root_dir = str(ROOT_DIR)
        self.soa_bible_path = self._get_path_str('data.soa_bible.current', 'data/bible.xlsx')
        self.field_bible_path = self._get_path_str('data.field_bible.current', 'data/ecrf.xlsx')
        self.protocol_folder = self._get_path_str('data.directories.protocols', 'data/protocols')
        self.protocol_pkl_folder = self._get_path_str('data.directories.protocol_pkl', 'data/protocol_pkl')
        self.output_folder = self._get_path_str('data.directories.output', 'data/total_result')
        self.chemistry_output_folder = self._get_path_str('data.directories.chemistry_output', 'data/total_chemistry_result')
        self.merged_output_folder = self._get_path_str('data.directories.merged_output', 'data/total_merged_result')
        # Removed sqlite_path - using PostgreSQL only

        # Load source database config from .soa_builder_env
        self._load_source_db_config()

        # Load BioNexus configuration
        self._load_bionexus_config()

        # Load Kafka and OSS configuration
        self._load_kafka_oss_config()

        # Set LLM config directly
        self.LLM_TEMPERATURE = self.get_config('llm.default_temperature', 0.1)
        self.MAX_TOKENS = self.get_config('llm.default_max_tokens', 4000)
        self.LOG_LEVEL = self.get_config('logging.log_level', 'INFO')
        self.LOG_FILE = self.get_config('logging.log_file', 'logs/app.log')
        
        # Set processing config
        self.top_k_candidates = self.get_config('processing.search.top_k_candidates', 20)
        self.batch_size = self.get_config('processing.search.batch_size', 8)
        self.confidence_threshold = self.get_config('processing.confidence_threshold', 'medium')

        # Set Bible database config
        self.bible_use_database = self.get_config('data.bible.use_database', False)
        self.bible_database_version = self.get_config('data.bible.database_version', 'V7.0')
        
        # Set database URL - PostgreSQL (optional for LLM-only usage)
        if self.DATABASE_URL and not self.DATABASE_URL.startswith('sqlite'):
            # Use DATABASE_URL if it's PostgreSQL
            self.database_url_computed = self.DATABASE_URL
        elif all([self.POSTGRES_HOST, self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_DB]):
            # Build PostgreSQL URL from individual components
            base_url = (
                f'postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}'
                f'@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
            )
            # Add SSL parameter if enabled
            if self.POSTGRES_SSL:
                self.database_url_computed = f'{base_url}?sslmode=require'
            else:
                self.database_url_computed = base_url
        else:
            # Database configuration is optional - set to None for LLM-only usage
            self.database_url_computed = None
        
        # Store yaml config for reference
        self.yaml_config = YAML_CONFIG
    
    def _load_source_db_config(self):
        """Load source database config from .soa_builder_env"""
        # If .soa_builder_env is empty or doesn't exist, set all to None
        if not SOA_BUILDER_ENV:
            self.SOURCE_HOST = None
            self.SOURCE_PORT = 5432
            self.SOURCE_USER = None
            self.SOURCE_PASSWORD = None
            self.SOURCE_DB = None
            self.SOURCE_SEARCH_PATH = None
            self.SOURCE_POOLING = True
            self.SOURCE_MIN_POOL_SIZE = 1
            self.SOURCE_MAX_POOL_SIZE = 20
            self.SOURCE_COMMAND_TIMEOUT = 15
            self.SOURCE_TIMEOUT = 15
            self.source_database_url = None
            return

        # Map .soa_builder_env keys to Settings attributes
        self.SOURCE_HOST = SOA_BUILDER_ENV.get('HOST')
        self.SOURCE_PORT = int(SOA_BUILDER_ENV.get('PORT', 5432))
        self.SOURCE_USER = SOA_BUILDER_ENV.get('USERNAME')
        self.SOURCE_PASSWORD = SOA_BUILDER_ENV.get('PASSWORD')
        self.SOURCE_DB = SOA_BUILDER_ENV.get('DATABASE')
        self.SOURCE_SEARCH_PATH = SOA_BUILDER_ENV.get('SEARCHPATH')
        self.SOURCE_POOLING = SOA_BUILDER_ENV.get('POOLING', 'true').lower() == 'true'
        self.SOURCE_MIN_POOL_SIZE = int(SOA_BUILDER_ENV.get('MINPOOLSIZE', 1))
        self.SOURCE_MAX_POOL_SIZE = int(SOA_BUILDER_ENV.get('MAXPOOLSIZE', 20))
        self.SOURCE_COMMAND_TIMEOUT = int(SOA_BUILDER_ENV.get('COMMANDTIMEOUT', 15))
        self.SOURCE_TIMEOUT = int(SOA_BUILDER_ENV.get('TIMEOUT', 15))

        # Build source database URL if all required fields are present
        if all([self.SOURCE_HOST, self.SOURCE_USER, self.SOURCE_PASSWORD, self.SOURCE_DB]):
            self.source_database_url = (
                f'postgresql://{self.SOURCE_USER}:{self.SOURCE_PASSWORD}'
                f'@{self.SOURCE_HOST}:{self.SOURCE_PORT}/{self.SOURCE_DB}'
            )
            if self.SOURCE_SEARCH_PATH:
                self.source_database_url += f'?options=-c%20search_path={self.SOURCE_SEARCH_PATH}'
        else:
            self.source_database_url = None

    def _load_bionexus_config(self):
        """Load BioNexus configuration from YAML"""
        if not BIONEXUS_CONFIG:
            # Set defaults if config file doesn't exist
            self.bionexus_host = None
            self.bionexus_api_paths = {}
            self.bionexus_user_id = None
            self.bionexus_display_name = None
            self.bionexus_mail = None
            return

        # Load BioNexus settings
        self.bionexus_host = BIONEXUS_CONFIG.get('host')
        self.bionexus_api_paths = BIONEXUS_CONFIG.get('api_path', {})
        self.bionexus_user_id = BIONEXUS_CONFIG.get('bio_nexus_user_id')
        self.bionexus_display_name = BIONEXUS_CONFIG.get('display_name')
        self.bionexus_mail = BIONEXUS_CONFIG.get('mail')

        # Store full config for reference
        self.bionexus_config = BIONEXUS_CONFIG

    def _load_kafka_oss_config(self):
        """Load Kafka and OSS configuration from YAML"""
        if not KAFKA_CONFIG:
            # Use environment variables as defaults
            self.kafka_config = None
            self.oss_config = None
            return

        # Override with YAML values if environment variables not set
        kafka_yaml = KAFKA_CONFIG.get('kafka', {})
        oss_yaml = KAFKA_CONFIG.get('oss', {})
        service_yaml = KAFKA_CONFIG.get('service', {})

        # Kafka settings - environment variables take precedence
        if not os.getenv('KAFKA_BOOTSTRAP_SERVERS'):
            self.KAFKA_BOOTSTRAP_SERVERS = kafka_yaml.get('bootstrap_servers', self.KAFKA_BOOTSTRAP_SERVERS)

        consumer_yaml = kafka_yaml.get('consumer', {})
        if not os.getenv('KAFKA_INPUT_TOPIC'):
            self.KAFKA_INPUT_TOPIC = consumer_yaml.get('topic', self.KAFKA_INPUT_TOPIC)
        if not os.getenv('KAFKA_GROUP_ID'):
            self.KAFKA_GROUP_ID = consumer_yaml.get('group_id', self.KAFKA_GROUP_ID)
        if not os.getenv('KAFKA_AUTO_OFFSET_RESET'):
            self.KAFKA_AUTO_OFFSET_RESET = consumer_yaml.get('auto_offset_reset', self.KAFKA_AUTO_OFFSET_RESET)
        if not os.getenv('KAFKA_ENABLE_AUTO_COMMIT'):
            self.KAFKA_ENABLE_AUTO_COMMIT = consumer_yaml.get('enable_auto_commit', self.KAFKA_ENABLE_AUTO_COMMIT)
        if not os.getenv('KAFKA_MAX_POLL_RECORDS'):
            self.KAFKA_MAX_POLL_RECORDS = consumer_yaml.get('max_poll_records', self.KAFKA_MAX_POLL_RECORDS)
        if not os.getenv('KAFKA_SESSION_TIMEOUT_MS'):
            self.KAFKA_SESSION_TIMEOUT_MS = consumer_yaml.get('session_timeout_ms', self.KAFKA_SESSION_TIMEOUT_MS)
        if not os.getenv('KAFKA_HEARTBEAT_INTERVAL_MS'):
            self.KAFKA_HEARTBEAT_INTERVAL_MS = consumer_yaml.get('heartbeat_interval_ms', self.KAFKA_HEARTBEAT_INTERVAL_MS)

        producer_yaml = kafka_yaml.get('producer', {})
        if not os.getenv('KAFKA_OUTPUT_TOPIC'):
            self.KAFKA_OUTPUT_TOPIC = producer_yaml.get('topic', self.KAFKA_OUTPUT_TOPIC)

        security_yaml = kafka_yaml.get('security', {})
        if not os.getenv('KAFKA_SECURITY_PROTOCOL'):
            self.KAFKA_SECURITY_PROTOCOL = security_yaml.get('protocol')
        if not os.getenv('KAFKA_SASL_MECHANISM'):
            self.KAFKA_SASL_MECHANISM = security_yaml.get('sasl_mechanism')

        # OSS settings - environment variables take precedence
        if not os.getenv('OSS_PROVIDER'):
            self.OSS_PROVIDER = oss_yaml.get('provider', self.OSS_PROVIDER)
        if not os.getenv('OSS_ENDPOINT'):
            self.OSS_ENDPOINT = oss_yaml.get('endpoint', self.OSS_ENDPOINT)
        if not os.getenv('OSS_BUCKET'):
            self.OSS_BUCKET = oss_yaml.get('bucket', self.OSS_BUCKET)
        if not os.getenv('OSS_DOWNLOAD_DIR'):
            self.OSS_DOWNLOAD_DIR = oss_yaml.get('download_dir', self.OSS_DOWNLOAD_DIR)
        if not os.getenv('OSS_UPLOAD_DIR'):
            self.OSS_UPLOAD_DIR = oss_yaml.get('upload_dir', self.OSS_UPLOAD_DIR)
        if not os.getenv('OSS_TIMEOUT'):
            self.OSS_TIMEOUT = oss_yaml.get('timeout', self.OSS_TIMEOUT)

        # Service settings
        if not os.getenv('KAFKA_POLL_TIMEOUT_MS'):
            self.KAFKA_POLL_TIMEOUT_MS = service_yaml.get('poll_timeout_ms', self.KAFKA_POLL_TIMEOUT_MS)
        if not os.getenv('KAFKA_MAX_RETRIES'):
            self.KAFKA_MAX_RETRIES = service_yaml.get('max_retries', self.KAFKA_MAX_RETRIES)

        # Store full configs for reference
        self.kafka_config = KAFKA_CONFIG.get('kafka', {})
        self.oss_config = KAFKA_CONFIG.get('oss', {})
        self.service_config = KAFKA_CONFIG.get('service', {})

    def _get_path_str(self, yaml_key: str, default: str) -> str:
        """Get path string from YAML config"""
        try:
            value = YAML_CONFIG
            for part in yaml_key.split('.'):
                value = value[part]
            return str(ROOT_DIR / Path(value))
        except (KeyError, TypeError):
            return str(ROOT_DIR / Path(default))
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get any config value from YAML"""
        try:
            value = YAML_CONFIG
            for part in key.split('.'):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_path(self, name: str) -> Path:
        """Get Path object for given name"""
        path_map = {
            'bible': self.soa_bible_path,
            'ecrf': self.field_bible_path,
            'protocols': self.protocol_folder,
            'protocol_pkl': self.protocol_pkl_folder,
            'output': self.output_folder,
            'chemistry_output': self.chemistry_output_folder,
            'merged_output': self.merged_output_folder
        }
        return Path(path_map.get(name, self.root_dir))
    
    def get_path_obj(self, name: str) -> Path:
        """Alias for get_path (backward compatibility)"""
        return self.get_path(name)
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if service is enabled"""
        if not service_name.startswith('enable_'):
            service_name = f'enable_{service_name}'
        return self.get_config(f'services.{service_name}', False)
    
    def get_services_config(self) -> dict[str, bool]:
        """Get all services config"""
        return self.get_config('services', {})
    
    def get_processing_config(self) -> dict[str, Any]:
        """Get processing config"""
        return self.get_config('processing', {})
    
    def get_workflow_config(self) -> dict[str, Any]:
        """Get workflow config"""
        return self.get_config('workflow', {})

    def refresh_soa_token(self, username: str | None = None, password: str | None = None) -> bool:
        """
        刷新SOA Token

        Args:
            username: 用户名（可选，不提供则使用环境变量）
            password: 密码（可选，不提供则使用环境变量）

        Returns:
            是否刷新成功
        """
        token_manager = self.get_token_manager()
        new_token = token_manager.refresh_token(username, password)

        if new_token:
            self.SOA_API_TOKEN = new_token
            return True

        return False

    def get_token_info(self) -> dict[str, Any]:
        """
        获取Token信息

        Returns:
            包含token状态信息的字典
        """
        token_manager = self.get_token_manager()
        return token_manager.get_token_info()

    def get_source_db_url(self) -> str | None:
        """
        获取源数据库连接URL（从.soa_builder_env）

        Returns:
            源数据库连接URL，如果配置不完整则返回None
        """
        return getattr(self, 'source_database_url', None)

    def get_target_db_url(self) -> str:
        """
        获取目标数据库连接URL（从.env）

        Returns:
            目标数据库连接URL
        """
        return self.database_url_computed

    def get_source_db_config(self) -> dict[str, Any]:
        """
        获取源数据库配置信息（从.soa_builder_env）

        Returns:
            包含源数据库配置的字典
        """
        return {
            'host': self.SOURCE_HOST,
            'port': self.SOURCE_PORT,
            'database': self.SOURCE_DB,
            'username': self.SOURCE_USER,
            'password': self.SOURCE_PASSWORD,
            'search_path': self.SOURCE_SEARCH_PATH,
            'pooling': self.SOURCE_POOLING,
            'min_pool_size': self.SOURCE_MIN_POOL_SIZE,
            'max_pool_size': self.SOURCE_MAX_POOL_SIZE,
            'command_timeout': self.SOURCE_COMMAND_TIMEOUT,
            'timeout': self.SOURCE_TIMEOUT,
            'connection_url': self.get_source_db_url()
        }

    def get_target_db_config(self) -> dict[str, Any]:
        """
        获取目标数据库配置信息（从.env）

        Returns:
            包含目标数据库配置的字典
        """
        return {
            'host': self.POSTGRES_HOST,
            'port': self.POSTGRES_PORT,
            'database': self.POSTGRES_DB,
            'username': self.POSTGRES_USER,
            'password': self.POSTGRES_PASSWORD,
            'connection_url': self.get_target_db_url()
        }

    def get_bionexus_config(self) -> dict[str, Any]:
        """
        获取BioNexus配置信息（从configs/bio_nexus.yaml）

        Returns:
            包含BioNexus配置的字典
        """
        return {
            'host': getattr(self, 'bionexus_host', None),
            'api_paths': getattr(self, 'bionexus_api_paths', {}),
            'user_id': getattr(self, 'bionexus_user_id', None),
            'display_name': getattr(self, 'bionexus_display_name', None),
            'mail': getattr(self, 'bionexus_mail', None),
            'access_token': self.BIONEXUS_ACCESS_TOKEN,
        }

    def get_kafka_config(self) -> dict[str, Any]:
        """
        获取Kafka配置信息（环境变量优先，然后是configs/kafka_service.yaml）

        Returns:
            包含Kafka配置的字典
        """
        return {
            'bootstrap_servers': self.KAFKA_BOOTSTRAP_SERVERS,
            'consumer': {
                'topic': self.KAFKA_INPUT_TOPIC,
                'group_id': self.KAFKA_GROUP_ID,
                'auto_offset_reset': self.KAFKA_AUTO_OFFSET_RESET,
                'enable_auto_commit': self.KAFKA_ENABLE_AUTO_COMMIT,
                'max_poll_records': self.KAFKA_MAX_POLL_RECORDS,
                'session_timeout_ms': self.KAFKA_SESSION_TIMEOUT_MS,
                'heartbeat_interval_ms': self.KAFKA_HEARTBEAT_INTERVAL_MS,
            },
            'producer': {
                'topic': self.KAFKA_OUTPUT_TOPIC,
                'acks': 'all',
                'retries': 3,
                'retry_backoff_ms': 1000,
            },
            'security': {
                'protocol': self.KAFKA_SECURITY_PROTOCOL,
                'sasl_mechanism': self.KAFKA_SASL_MECHANISM,
                'sasl_username': self.KAFKA_SASL_USERNAME,
                'sasl_password': self.KAFKA_SASL_PASSWORD,
            },
            'poll_timeout_ms': self.KAFKA_POLL_TIMEOUT_MS,
            'max_retries': self.KAFKA_MAX_RETRIES,
        }

    def get_oss_config(self) -> dict[str, Any]:
        """
        获取OSS配置信息（环境变量优先，然后是configs/kafka_service.yaml）

        Returns:
            包含OSS配置的字典
        """
        return {
            'provider': self.OSS_PROVIDER,
            'endpoint': self.OSS_ENDPOINT,
            'bucket': self.OSS_BUCKET,
            'access_key_id': self.OSS_ACCESS_KEY_ID,
            'access_key_secret': self.OSS_ACCESS_KEY_SECRET,
            'download_dir': self.OSS_DOWNLOAD_DIR,
            'upload_dir': self.OSS_UPLOAD_DIR,
            'timeout': self.OSS_TIMEOUT,
        }

# Global settings instance
settings = Settings()

# Helper functions for backward compatibility
def get_settings() -> Settings:
    return settings

def load_yaml_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML config file"""
    if config_path is None:
        return YAML_CONFIG
    
    config_path = Path(config_path) if not isinstance(config_path, Path) else config_path
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def get_config_value(key_path: str, config_data: dict[str, Any] | None = None) -> Any:
    """Get config value by dot notation"""
    if config_data is None:
        config_data = YAML_CONFIG
    
    try:
        value = config_data
        for key in key_path.split('.'):
            value = value[key]
        return value
    except (KeyError, TypeError):
        raise KeyError(f"Config path '{key_path}' not found")

if __name__ == '__main__':
    # Keep print here to avoid circular import with logger
    print(settings)
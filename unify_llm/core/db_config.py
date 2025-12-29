"""
Database configuration loader.
Provides centralized access to database settings and table names.
"""

from pathlib import Path
from typing import Any

from unify_llm.core.logger import logger

def load_db_config() -> dict[str, Any]:
    """Load database configuration from unified settings.
    
    Args:

    Returns:
        dictionary with database configuration
    """
    from unify_llm.core.config import settings, load_yaml_config
    
    # Use the raw YAML config for database-specific settings
    if hasattr(settings, 'raw_yaml_config'):
        db_config = settings.raw_yaml_config.get('database', {})
    else:
        # Fallback to loading YAML if needed
        yaml_config = load_yaml_config()
        db_config = yaml_config.get('database', {})
    
    # Add connection settings from unified config
    db_config.update({
        'url': settings.database_url,
        'host': settings.database_host,
        'port': settings.database_port,
        'user': settings.database_user,
        'password': settings.database_password,
        'name': settings.database_name,
        'use_sqlite': settings.use_sqlite_db,
        'sqlite_path': str(settings.sqlite_path) if settings.sqlite_path else None
    })
    
    return db_config

def get_table_name(table_key: str, default: str | None = None) -> str:
    """Get table name from configuration.

    Args:
        table_key: Key for the table (e.g., 'soa_bible', 'field_fields')
        default: Default table name if not found in config
    
    Returns:
        Table name from config or default
    """
    config = load_db_config()
    tables = config.get('tables', {})
    
    if table_key in tables:
        return tables[table_key]
    
    if default:
        return default
    
    # If no default provided, return the key itself as table name
    return table_key
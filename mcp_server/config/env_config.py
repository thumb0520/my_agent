import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

class EnvConfig:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnvConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._load_env_files()

    def _load_env_files(self):
        """Load environment variables from multiple .env files"""
        # Get the project root directory (autogen_version)
        project_root = Path(__file__).parent.parent
        
        # Load root .env file
        root_env = project_root.parent / '.env'
        if root_env.exists():
            load_dotenv(root_env)
            
        # Load project .env file
        project_env = project_root / '.env'
        if project_env.exists():
            load_dotenv(project_env)

    @property
    def pythonpath(self) -> str:
        """Get the current PYTHONPATH"""
        return os.getenv('PYTHONPATH', '')

    @pythonpath.setter
    def pythonpath(self, value: str):
        """Set PYTHONPATH"""
        os.environ['PYTHONPATH'] = value

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable"""
        return os.getenv(key, default)

    def set(self, key: str, value: str):
        """Set an environment variable"""
        os.environ[key] = value

# Create a singleton instance
env_config = EnvConfig() 
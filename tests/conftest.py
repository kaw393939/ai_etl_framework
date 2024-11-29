import os
import sys
import pytest
from pathlib import Path
from typing import Generator

# Add the src directory to the Python path
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

@pytest.fixture
def test_env() -> Generator[None, None, None]:
    """Setup test environment variables"""
    original_env = dict(os.environ)
    os.environ.update({
        'ENVIRONMENT': 'test',
        'DEBUG': 'false'
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def test_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for test configurations"""
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    return config_dir

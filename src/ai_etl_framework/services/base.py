from abc import ABC, abstractmethod
from typing import Any

class BaseService(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the service"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if service is healthy"""
        pass

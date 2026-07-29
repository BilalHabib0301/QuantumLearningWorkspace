from abc import ABC, abstractmethod
from typing import List, Dict

class BaseGenerator(ABC):
    """
    Base class for all quiz generators.

    Every quiz generator (MCQ, True/False, Fill in the Blank,
    Short Answer) will inherit from this class.
    """

    @abstractmethod
    def generate(self, text: str) -> List[Dict]:
        """Returns a list of dictionaries (JSON format)."""
        pass
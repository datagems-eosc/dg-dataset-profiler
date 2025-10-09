from abc import ABC, abstractmethod
from typing import Dict, List


class RecordSet(ABC):
    def __init__(self):
        self.inject_distribution = None

    @abstractmethod
    def extract_fields(self) -> List:
        pass

    @abstractmethod
    def to_dict(self) -> Dict:
        pass


class ColumnField(ABC):
    @abstractmethod
    def to_dict(self) -> Dict:
        pass


class TextChunk(ABC):
    @abstractmethod
    def to_dict(self) -> Dict:
        pass

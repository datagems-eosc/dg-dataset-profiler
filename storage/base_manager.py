from abc import ABC, abstractmethod
from typing import List, Optional
import logging


class AbstractFileManager(ABC):
    """Abstract base class for file management operations."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._create_default_logger()

    @classmethod
    def _create_default_logger(cls) -> logging.Logger:
        # get class name for logger
        cls_name = cls.__name__
        logger = logging.getLogger(cls_name)
        if not logger.hasHandlers():
            # Configure logging to output to console
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    @abstractmethod
    def create_directory(self, path: str):
        raise NotImplementedError(
            "create_directory method not implemented in the abstract object."
        )

    @abstractmethod
    def delete_directory(self, path: str):
        raise NotImplementedError(
            "delete_directory method not implemented in the abstract object."
        )

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str):
        raise NotImplementedError(
            "upload_file method not implemented in the abstract object."
        )

    @abstractmethod
    def delete_file(self, remote_path: str):
        raise NotImplementedError(
            "delete_file method not implemented in the abstract object."
        )

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str):
        raise NotImplementedError(
            "download_file method not implemented in the abstract object."
        )

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        raise NotImplementedError(
            "list_files method not implemented in the abstract object."
        )

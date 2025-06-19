from cryptography.fernet import Fernet
from pathlib import Path


class TextEncryptor:
    def __init__(self, key : bytes):
        self._fernet = Fernet(key)

    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()

    @staticmethod
    def load_key(keypath : Path) -> bytes:
        abspath = keypath.resolve()
        if not abspath.is_file():
            raise ValueError(f"Not a regular file: {abspath}")
        if not abspath.exists():
            raise FileNotFoundError(f"File not found: {abspath}")
        
        with abspath.open(mode = "rb") as file:
            key = file.read()
            return key

    @staticmethod
    def save_key(key : bytes, keypath : Path):
        abspath = keypath.resolve()
        if not abspath.is_file():
            raise ValueError(f"Not a regular file: {abspath}")

        with abspath.open(mode = "wb") as file:
            file.write(key)

    def encrypt(self, text : str) -> bytes:
        return self._fernet.encrypt(data = text.encode())
    
    def decrypt(self, data : bytes) -> str:
        return self._fernet.decrypt(token = data).decode()

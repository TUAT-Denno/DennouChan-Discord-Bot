from cryptography.fernet import Fernet
from pathlib import Path


class TextEncryptor:
    """A utility class for symmetric text encryption and decryption using Fernet.

    This class supports key generation, loading, saving, and text encryption/decryption
    using the Fernet symmetric encryption algorithm.
    """

    def __init__(self, key : bytes):
        """Initializes the encryptor with a given Fernet key.

        Args:
            key (bytes): A valid Fernet key for encryption and decryption.
        """
        self._fernet = Fernet(key)

    @staticmethod
    def generate_key() -> bytes:
        """Generates a new Fernet key.

        Returns:
            bytes: A newly generated Fernet-compatible key.
        """
        return Fernet.generate_key()

    @staticmethod
    def load_key(keypath : Path) -> bytes:
        """Loads a Fernet key from a file.

        Args:
            keypath (Path): Path to the file containing the key.

        Returns:
            bytes: The key read from the file.

        Raises:
            ValueError: If the path is not a regular file.
            FileNotFoundError: If the file does not exist.
        """
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
        """Saves a Fernet key to a file.

        Args:
            key (bytes): The Fernet key to be saved.
            keypath (Path): Path to the destination file.

        Raises:
            ValueError: If the path is not a regular file.
        """
        abspath = keypath.resolve()
        if not abspath.is_file():
            raise ValueError(f"Not a regular file: {abspath}")

        with abspath.open(mode = "wb") as file:
            file.write(key)

    def encrypt(self, text : str) -> bytes:
        """Encrypts a text string.

        Args:
            text (str): The plain text to encrypt.

        Returns:
            bytes: The encrypted data as a byte string.
        """
        return self._fernet.encrypt(data = text.encode())
    
    def decrypt(self, data : bytes) -> str:
        """Decrypts a byte string back into plain text.

        Args:
            data (bytes): The encrypted byte string.

        Returns:
            str: The decrypted plain text.
        """
        return self._fernet.decrypt(token = data).decode()

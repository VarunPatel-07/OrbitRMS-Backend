import base64
import json
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status


def get_encryption_key() -> bytes:
    key = os.getenv("BACKEND_APP_ENCRYPTION_KEY")

    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "BACKEND_APP_ENCRYPTION_KEY is missing", "success": False},
        )

    try:
        decode_key = base64.b64decode(key)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "BACKEND_APP_ENCRYPTION_KEY must be a valid base64 value",
                "success": False,
            },
        )

    if len(decode_key) != 32:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "BACKEND_APP_ENCRYPTION_KEY must be 32 bytes", "success": False},
        )

    return decode_key


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encrypt_data_service(data: dict | str) -> str:
    encryption_key = get_encryption_key()

    iv = os.urandom(12)

    plain_text = data if isinstance(data, str) else json.dumps(data)

    encryptor = Cipher(algorithm=algorithms.AES(encryption_key), mode=modes.GCM(iv)).encryptor()

    encrypt_data = encryptor.update(plain_text.encode("utf-8")) + encryptor.finalize()
    auth_tag = encryptor.tag

    return base64url_encode(iv + auth_tag + encrypt_data)


def decrypt_data_service(encrypted_text: str) -> dict | str:
    try:
        decryption_key = get_encryption_key()

        encrypted_buffer = base64url_decode(encrypted_text)

        iv = encrypted_buffer[:12]
        auth_tag = encrypted_buffer[12:28]
        encrypted_data = encrypted_buffer[28:]

        decryptor = Cipher(algorithm=algorithms.AES(decryption_key), mode=modes.GCM(iv, auth_tag)).decryptor()

        encrypt_data = decryptor.update(encrypted_data) + decryptor.finalize()

        try:
            return json.loads(encrypt_data)
        except json.JSONDecodeError:
            return encrypt_data

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid or corrupted encrypted data",
                "success": False,
            },
        )


def urlsafe_data_encoding_service(data: dict | str) -> str:
    if not data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "The Data is required", "success": False},
        )

    try:
        plain_text = data if isinstance(data, str) else json.dumps(data)
        key = get_encryption_key()
        aesgcm = AESGCM(key)

        nonce = os.urandom(12)

        encrypted_data = aesgcm.encrypt(
            nonce,
            plain_text.encode("utf-8"),
            None,
        )

        # AESGCM returns: ciphertext + auth_tag
        # Final format: nonce + ciphertext + auth_tag
        return base64url_encode(nonce + encrypted_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unexpected error during encryption",
                "success": False,
                "error": str(e),
            },
        )


def urlsafe_data_decoding_service(encrypted_data: str) -> dict | str:
    if not encrypted_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "The Data is required", "success": False},
        )

    try:
        key = get_encryption_key()
        aesgcm = AESGCM(key)

        raw_data = base64url_decode(encrypted_data)

        nonce = raw_data[:12]
        ciphertext_with_tag = raw_data[12:]

        decrypted_data = aesgcm.decrypt(
            nonce,
            ciphertext_with_tag,
            None,
        )

        decoded_data = decrypted_data.decode("utf-8")

        try:
            return json.loads(decoded_data)
        except json.JSONDecodeError:
            return decoded_data

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Decryption failed: Data may have been altered or corrupted!",
                "success": False,
                "error": str(e),
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Unexpected error during decryption: {str(e)}",
                "success": False,
                "error": str(e),
            },
        )

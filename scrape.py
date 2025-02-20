import os
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def decrypt_password(encrypted_password: str) -> str:
    secret_key = os.environ.get("ENCRYPTION_KEY")
    iv = os.environ.get("ENCRYPTION_IV")
    print("SECRET KEY", secret_key)
    print("IV", iv)
    if not secret_key or not iv:
        raise ValueError("ENCRYPTION_KEY or ENCRYPTION_IV environment variable is not set")
    
    
    ciphertext = b64decode(encrypted_password)
    derived_key = b64decode(secret_key)
    cipher = AES.new(derived_key, AES.MODE_CBC, iv.encode('utf-8'))
    decrypted_data = cipher.decrypt(ciphertext)
    return unpad(decrypted_data, 16).decode("utf-8")

# Example usage
encrypted_password = "XMupu5u4sNSL3+UyfXPb4Q=="
decrypted_password = decrypt_password(encrypted_password)
print(decrypted_password)
# crypto_core.py —— PeriKey 参考原型之密码学核心（演示用）
#
# ⚠️ 注意：本文件使用的“SHA-256 密钥流”仅为演示协议流程，
#    生产环境 MUST 使用 HKDF-SHA256 + AES-256-GCM（见 docs/protocol.md §9）。
#    切勿将本文件直接用于真实网络。

import secrets
import hashlib
import string

_CHARSET = string.ascii_letters + string.digits + "!@#$%^&*"


def gen_dsecret() -> bytes:
    """生成设备小秘密 DSecret_i（32 字节随机）。"""
    return secrets.token_bytes(32)


def derive_key(dsecret: bytes) -> bytes:
    """由 DSecret 派生加密密钥（生产中应为 HKDF-SHA256）。"""
    return hashlib.sha256(dsecret).digest()


def _keystream(key: bytes, nonce: bytes):
    """演示用密钥流生成器：keystream = SHA256(key || nonce || counter)。"""
    i = 0
    while True:
        yield from hashlib.sha256(key + nonce + i.to_bytes(4, "big")).digest()
        i += 1


def encrypt(key: bytes, data: bytes) -> bytes:
    """演示用流式加密（非生产级）。返回 nonce(16) || 密文。"""
    nonce = secrets.token_bytes(16)
    out = bytearray()
    gen = _keystream(key, nonce)
    for b in data:
        out.append(b ^ next(gen))
    return nonce + bytes(out)


def decrypt(key: bytes, blob: bytes) -> bytes:
    """演示用流式解密。"""
    nonce, body = blob[:16], blob[16:]
    out = bytearray()
    gen = _keystream(key, nonce)
    for b in body:
        out.append(b ^ next(gen))
    return bytes(out)


def gen_password(length: int = 16) -> str:
    """生成一个随机密码（length 个字符）。老设备用很长的值抬高破解成本。"""
    return "".join(secrets.choice(_CHARSET) for _ in range(length))

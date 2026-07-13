#!/usr/bin/env python3
"""
Secure File Encryptor (AES)
A lightweight, single-file tool to encrypt/decrypt files with a password,
using AES-256-GCM (authenticated encryption) and PBKDF2-HMAC-SHA256 for
key derivation.

Requires: pip install cryptography

Usage:
    python file_encryptor.py encrypt secret.docx
    python file_encryptor.py decrypt secret.docx.enc
    python file_encryptor.py encrypt secret.docx -o out.enc
"""

import argparse
import getpass
import os
import struct
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

MAGIC = b"AESF"          # file format marker
VERSION = 1
SALT_LEN = 16
NONCE_LEN = 12
KDF_ITERATIONS = 480_000
KEY_LEN = 32              # AES-256
CHUNK_SIZE = 64 * 1024 * 1024  # read whole file at once up to this; fine for most files


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_file(in_path: str, out_path: str, password: str) -> None:
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = derive_key(password, salt)
    aesgcm = AESGCM(key)

    with open(in_path, "rb") as f:
        plaintext = f.read()

    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    with open(out_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">B", VERSION))
        f.write(struct.pack(">I", KDF_ITERATIONS))
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)  # ciphertext already includes the 16-byte GCM tag at the end

    print(f"Encrypted -> {out_path} ({len(ciphertext):,} bytes)")


def decrypt_file(in_path: str, out_path: str, password: str) -> None:
    with open(in_path, "rb") as f:
        data = f.read()

    if data[:4] != MAGIC:
        print("Error: not a recognized encrypted file (bad magic header).")
        sys.exit(1)

    offset = 4
    version = struct.unpack(">B", data[offset:offset + 1])[0]
    offset += 1
    if version != VERSION:
        print(f"Error: unsupported file format version {version}.")
        sys.exit(1)

    iterations = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    salt = data[offset:offset + SALT_LEN]
    offset += SALT_LEN
    nonce = data[offset:offset + NONCE_LEN]
    offset += NONCE_LEN
    ciphertext = data[offset:]

    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_LEN, salt=salt, iterations=iterations)
    key = kdf.derive(password.encode("utf-8"))
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    except Exception:
        print("Error: decryption failed. Wrong password, or the file is corrupted/tampered with.")
        sys.exit(1)

    with open(out_path, "wb") as f:
        f.write(plaintext)

    print(f"Decrypted -> {out_path} ({len(plaintext):,} bytes)")


def get_password(confirm: bool) -> str:
    pw = getpass.getpass("Password: ")
    if not pw:
        print("Error: password cannot be empty.")
        sys.exit(1)
    if confirm:
        pw2 = getpass.getpass("Confirm password: ")
        if pw != pw2:
            print("Error: passwords do not match.")
            sys.exit(1)
    return pw


def main():
    parser = argparse.ArgumentParser(description="Encrypt or decrypt a file with AES-256-GCM.")
    parser.add_argument("action", choices=["encrypt", "decrypt"])
    parser.add_argument("file", help="Path to the input file")
    parser.add_argument("-o", "--output", help="Output file path (optional)")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: '{args.file}' not found.")
        sys.exit(1)

    if args.action == "encrypt":
        out_path = args.output or (args.file + ".enc")
        password = get_password(confirm=True)
        encrypt_file(args.file, out_path, password)
    else:
        if args.output:
            out_path = args.output
        elif args.file.endswith(".enc"):
            out_path = args.file[:-4]
        else:
            out_path = args.file + ".dec"
        password = get_password(confirm=False)
        decrypt_file(args.file, out_path, password)


if __name__ == "__main__":
    main()

"""
This module provides a unified way to generate IDs across the entire application.
"""

import string

from nanoid import generate

alphanumeric_chars = string.ascii_letters + string.digits


def generate_chat_id() -> str:
    return generate(alphabet=alphanumeric_chars, size=8)


def generate_message_id() -> str:
    return generate(alphabet=alphanumeric_chars, size=8)

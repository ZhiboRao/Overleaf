"""Secure credential storage backed by the system keychain.

基于系统密钥链的安全凭据存储。

We deliberately avoid storing passwords in plaintext on disk. On macOS the
``keyring`` library talks to the Keychain via the Security framework;
failure to access the keychain is treated as "no saved credential" rather
than raising, so the UI flow can proceed without secrets.

我们不会将密码以明文落盘。macOS 上 ``keyring`` 通过 Security 框架访问
钥匙串；当钥匙串不可用时，视为「无保存凭据」，而不是抛出异常，确保
UI 流程始终可用。
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass

import keyring
from keyring.errors import KeyringError

_LOGGER = logging.getLogger(__name__)

_SERVICE_NAME = "com.zhiborao.overleafclient"
_USERNAME_ANCHOR_KEY = "__last_username__"


@dataclass(frozen=True)
class Credential:
    """A (username, password) pair / 账号密码组合."""

    username: str
    password: str


class CredentialStore:
    """Thin facade over :mod:`keyring` scoped to this application.

    基于 :mod:`keyring` 的轻封装，所有键都限定在本应用命名空间。
    """

    def __init__(self, service_name: str = _SERVICE_NAME) -> None:
        """Initialize the store.

        Args:
            service_name: Keychain service identifier; override for tests.
        """
        self._service = service_name

    def save(self, credential: Credential) -> bool:
        """Persist credentials in the keychain.

        将凭据写入钥匙串。

        Args:
            credential: The credential to store.

        Returns:
            True if the write succeeded; False otherwise.
        """
        try:
            keyring.set_password(
                self._service, credential.username, credential.password,
            )
            # Remember the last username so we can auto-fill without asking.
            # 记录最近用户名，便于下次直接带入。
            keyring.set_password(
                self._service, _USERNAME_ANCHOR_KEY, credential.username,
            )
        except KeyringError as exc:
            _LOGGER.warning("Unable to write to keychain: %s", exc)
            return False
        return True

    def load(self, username: str | None = None) -> Credential | None:
        """Load credentials.

        读取凭据。

        Args:
            username: Explicit username; if None, the last saved username
                is used.

        Returns:
            The stored credential, or None if nothing is available.
        """
        try:
            user = username or keyring.get_password(
                self._service, _USERNAME_ANCHOR_KEY,
            )
            if not user:
                return None
            password = keyring.get_password(self._service, user)
            if password is None:
                return None
            return Credential(username=user, password=password)
        except KeyringError as exc:
            _LOGGER.warning("Unable to read from keychain: %s", exc)
            return None

    def delete(self, username: str | None = None) -> bool:
        """Delete credentials.

        删除凭据。

        Args:
            username: Username to delete; if None, the last saved username
                is cleared along with its password.

        Returns:
            True if deletion succeeded or nothing was stored.
        """
        try:
            user = username or keyring.get_password(
                self._service, _USERNAME_ANCHOR_KEY,
            )
            if user:
                with contextlib.suppress(KeyringError):
                    keyring.delete_password(self._service, user)
            with contextlib.suppress(KeyringError):
                keyring.delete_password(self._service, _USERNAME_ANCHOR_KEY)
        except KeyringError as exc:
            _LOGGER.warning("Unable to delete from keychain: %s", exc)
            return False
        return True

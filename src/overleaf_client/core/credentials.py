"""Secure credential storage backed by the macOS Keychain.

基于 macOS 钥匙串的安全凭据存储。

We shell out to ``/usr/bin/security`` instead of using the ``keyring``
Python package. ``keyring`` on macOS relies on PyObjC bindings that
routinely fail inside unsigned py2app bundles — the Security framework
rejects keychain calls whose caller's code signature does not match the
keychain's ACL. The ``security`` CLI bypasses this: it always works as
long as the user's login keychain is unlocked.

我们通过 ``/usr/bin/security`` 命令行工具访问钥匙串，而不是 ``keyring``
包。``keyring`` 在 macOS 上依赖 PyObjC；在未签名的 py2app 应用包中，
Security 框架会因调用方签名与钥匙串 ACL 不匹配而拒绝访问，导致保存
失败。``security`` 命令则只要用户登录钥匙串解锁就可以正常工作。
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

_SERVICE_NAME = "com.zhiborao.overleafclient"
_USERNAME_ANCHOR_KEY = "__last_username__"
_SECURITY_CMD = "/usr/bin/security"


@dataclass(frozen=True)
class Credential:
    """A (username, password) pair / 账号密码组合."""

    username: str
    password: str


def _run_security(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke ``/usr/bin/security`` with ``args``.

    调用 ``/usr/bin/security`` 并返回结果对象。
    """
    return subprocess.run(  # noqa: S603 - fixed absolute path, fixed argv
        [_SECURITY_CMD, *args],
        check=False,
        capture_output=True,
        text=True,
    )


class CredentialStore:
    """Keychain-backed credential store scoped to this application.

    限定在本应用命名空间内的钥匙串凭据存储。
    """

    def __init__(self, service_name: str = _SERVICE_NAME) -> None:
        """Initialize the store.

        Args:
            service_name: Keychain service identifier; override for tests.
        """
        self._service = service_name

    def _set(self, account: str, password: str) -> bool:
        try:
            result = _run_security(
                "add-generic-password",
                "-U",  # update in place if it already exists
                "-a", account,
                "-s", self._service,
                "-w", password,
            )
        except FileNotFoundError:
            _LOGGER.warning("%s not found on PATH.", _SECURITY_CMD)
            return False
        if result.returncode != 0:
            _LOGGER.warning(
                "security add-generic-password failed (rc=%s): %s",
                result.returncode, result.stderr.strip(),
            )
            return False
        return True

    def _get(self, account: str) -> str | None:
        try:
            result = _run_security(
                "find-generic-password",
                "-a", account,
                "-s", self._service,
                "-w",  # print the password only
            )
        except FileNotFoundError:
            _LOGGER.warning("%s not found on PATH.", _SECURITY_CMD)
            return None
        if result.returncode != 0:
            return None
        return result.stdout.rstrip("\n") or None

    def _delete(self, account: str) -> None:
        try:
            _run_security(
                "delete-generic-password",
                "-a", account,
                "-s", self._service,
            )
        except FileNotFoundError:
            _LOGGER.warning("%s not found on PATH.", _SECURITY_CMD)

    def save(self, credential: Credential) -> bool:
        """Persist credentials in the keychain.

        将凭据写入钥匙串。

        Args:
            credential: The credential to store.

        Returns:
            True if the write succeeded; False otherwise.
        """
        if not self._set(credential.username, credential.password):
            return False
        # Best-effort anchor write; failure here does not invalidate the save.
        # 同步记录最近用户名，失败不影响主凭据保存。
        self._set(_USERNAME_ANCHOR_KEY, credential.username)
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
        user = username or self._get(_USERNAME_ANCHOR_KEY)
        if not user:
            return None
        password = self._get(user)
        if password is None:
            return None
        return Credential(username=user, password=password)

    def delete(self, username: str | None = None) -> bool:
        """Delete credentials.

        删除凭据。

        Args:
            username: Username to delete; if None, the last saved username
                is cleared along with its password.

        Returns:
            True once deletion has been attempted.
        """
        user = username or self._get(_USERNAME_ANCHOR_KEY)
        if user:
            self._delete(user)
        self._delete(_USERNAME_ANCHOR_KEY)
        return True

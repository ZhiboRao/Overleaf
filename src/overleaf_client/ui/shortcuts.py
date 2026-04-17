"""JavaScript snippets injected to drive the Overleaf UI.

注入到 Overleaf 页面以触发其 UI 操作的 JavaScript 片段。

Rather than reinventing Overleaf's editor, we invoke the existing DOM
controls. Selectors are documented below; if Overleaf's markup changes
only this file needs updating.

我们并不重实现 Overleaf 编辑器，而是复用其现有 DOM 元素。选择器集中
在此；Overleaf 前端升级时只需修改本文件。
"""

from __future__ import annotations

import json

# Auto-fill the login form. The two input ids are stable on Overleaf's
# Passport-based login page ("email" and "password").
# 自动填充登录表单。Overleaf 基于 Passport 的登录页中两个字段
# id 稳定为 "email" 与 "password"。
LOGIN_AUTOFILL_JS_TEMPLATE = r"""
(function () {
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    if (!email || !password) { return false; }
    // Only fill if empty so we never clobber the user's own typing.
    // 仅在空字段上填充，避免覆盖用户输入。
    if (!email.value) { email.value = %(email)s; email.dispatchEvent(
        new Event('input', { bubbles: true })); }
    if (!password.value) {
        password.value = %(password)s;
        password.dispatchEvent(new Event('input', { bubbles: true }));
    }
    return true;
})();
"""


def login_autofill_js(email: str, password: str) -> str:
    """Render :data:`LOGIN_AUTOFILL_JS_TEMPLATE` with safe JSON literals.

    使用安全 JSON 字面量渲染自动填充脚本。

    Args:
        email: Username / email address to inject.
        password: Password to inject.

    Returns:
        JavaScript source ready to be evaluated in the page.
    """
    return LOGIN_AUTOFILL_JS_TEMPLATE % {
        "email": json.dumps(email),
        "password": json.dumps(password),
    }

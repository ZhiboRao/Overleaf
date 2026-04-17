"""JavaScript snippets injected to drive the Overleaf UI.

注入到 Overleaf 页面以触发其 UI 操作的 JavaScript 片段。

Rather than reinventing Overleaf's editor, we invoke the existing DOM
controls. Selectors are documented below; if Overleaf's markup changes
only this file needs updating.

我们并不重实现 Overleaf 编辑器，而是复用其现有 DOM 元素。选择器集中
在此；Overleaf 前端升级时只需修改本文件。
"""

from __future__ import annotations

# Trigger "Recompile". Overleaf binds Cmd+Enter natively, but this button
# selector is the stable way to work when the editor is not focused.
# 触发「Recompile」。Overleaf 原生绑定 Cmd+Enter，但当编辑器失焦时
# 通过点击按钮是更可靠的做法。
RECOMPILE_JS = r"""
(function () {
    const selectors = [
        'button.btn-recompile',
        'button[aria-label="Recompile"]',
        '[data-testid="recompile-button"]',
    ];
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el) { el.click(); return true; }
    }
    return false;
})();
"""

# Download the compiled PDF via Overleaf's own "Download PDF" action.
# 通过 Overleaf 自身的「Download PDF」按钮下载已编译的 PDF。
DOWNLOAD_PDF_JS = r"""
(function () {
    const selectors = [
        'a.btn-download-pdf',
        'a[aria-label="Download PDF"]',
        '[data-testid="download-pdf"]',
    ];
    for (const sel of selectors) {
        const el = document.querySelector(sel);
        if (el) { el.click(); return true; }
    }
    // Fallback: click the PDF icon in the toolbar.
    const iconLink = document.querySelector(
        'a[href*="output.pdf"], a[href*="/download/project/"]',
    );
    if (iconLink) { iconLink.click(); return true; }
    return false;
})();
"""

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
    import json
    return LOGIN_AUTOFILL_JS_TEMPLATE % {
        "email": json.dumps(email),
        "password": json.dumps(password),
    }

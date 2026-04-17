"""Run as ``python -m overleaf_client``.

允许通过 ``python -m overleaf_client`` 启动。
"""

from overleaf_client.app import main

if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Write the user's local, Git-ignored Feishu target configuration."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


CONFIG = Path(__file__).resolve().parents[1] / "config.local.json"


def valid_url(value, *, base=False):
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("链接必须是完整的 HTTPS URL")
    if base and ("/base/" not in parsed.path or not parse_qs(parsed.query).get("table")):
        raise ValueError("目标链接需要包含 /base/ 路径和 table 参数")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="目标飞书多维表格链接")
    parser.add_argument("--priority-policy-url", default="", help="适用的优先级规则文档链接")
    parser.add_argument("--temporary-default", choices=["是", "否"], default="否")
    parser.add_argument("--force", action="store_true", help="覆盖已有的本地配置")
    args = parser.parse_args()
    try:
        if CONFIG.exists() and not args.force:
            raise ValueError("本地配置已存在；需要覆盖时加 --force")
        data = {
            "base_url": valid_url(args.base_url, base=True),
            "priority_policy_url": valid_url(args.priority_policy_url) if args.priority_policy_url else "",
            "temporary_requirement_default": args.temporary_default,
        }
        CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(CONFIG, 0o600)
    except (OSError, ValueError) as exc:
        print(f"配置失败：{exc}", file=sys.stderr)
        return 2
    print("本地配置已保存；未写入公开仓库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

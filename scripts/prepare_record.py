#!/usr/bin/env python3
"""Build a Base create_records payload from a reviewed draft and live field schema.

This only validates and writes local JSON. It never sends a request to Feishu.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


MANDATORY = ["子中心", "功能名称", "功能描述", "进展", "优先级", "需求背景", "需求来源"]
OWNERS = ["产品负责人", "研发负责人", "测试负责人"]
READ_ONLY = {"formula", "lookup", "auto_number", "created_at", "updated_at", "created_by", "updated_by"}


def build(draft, schema, requirement_id):
    if schema.get("ok") is not True or schema.get("identity") != "user":
        raise ValueError("字段 schema 必须来自成功的 user 身份读取")
    fields = schema.get("data", {}).get("fields")
    if not isinstance(fields, list) or not fields:
        raise ValueError("字段 schema 缺少 fields")
    by_name = {field["name"]: field for field in fields}
    matches = [item for item in draft.get("requirements", []) if item.get("id") == requirement_id]
    if len(matches) != 1:
        raise ValueError(f"找不到唯一的需求 {requirement_id}")
    proposed = matches[0].get("fields", {})
    missing = [name for name in MANDATORY if not proposed.get(name)]
    if missing:
        raise ValueError("SOP 必填字段为空：" + "、".join(missing))
    if not any(proposed.get(name) for name in OWNERS):
        raise ValueError("至少填写一位适用负责人")
    background = proposed["需求背景"]
    if not isinstance(background, str) or not background.startswith("提出人：") or not background.removeprefix("提出人：").strip():
        raise ValueError("需求背景须使用‘提出人：姓名’格式")
    unknown = sorted(set(proposed) - set(by_name))
    if unknown:
        raise ValueError("实时表格不存在这些字段：" + "、".join(unknown))

    record = {}
    notices = []
    for name, value in proposed.items():
        if value is None or value == "" or value == []:
            continue
        field = by_name[name]
        kind = field.get("type")
        if kind in READ_ONLY or kind == "attachment":
            raise ValueError(f"{name} 为只读或附件字段，不能作为普通单元格提交")
        if kind == "text":
            if not isinstance(value, str):
                raise ValueError(f"{name} 必须是文本")
            record[name] = value
        elif kind == "select":
            selected = [value] if isinstance(value, str) else value
            if not isinstance(selected, list) or not all(isinstance(x, str) for x in selected):
                raise ValueError(f"{name} 必须是选项名称或名称数组")
            if field.get("multiple") is False and len(selected) != 1:
                raise ValueError(f"{name} 是单选，只能填一个选项")
            options = Counter(x.get("name") for x in field.get("options", []))
            invalid = [x for x in selected if not options[x]]
            if invalid:
                raise ValueError(f"{name} 不存在选项：{'、'.join(invalid)}")
            duplicate_names = [x for x in selected if options[x] > 1]
            if duplicate_names:
                notices.append(f"{name} 存在同名选项：{'、'.join(duplicate_names)}；提交后须核对结果")
            record[name] = selected
        elif kind == "datetime":
            if not isinstance(value, (str, int)):
                raise ValueError(f"{name} 必须是日期字符串或毫秒时间戳")
            record[name] = value
        elif kind in {"link", "user", "group_chat"}:
            if not isinstance(value, list) or not all(isinstance(x, dict) and x.get("id") for x in value):
                raise ValueError(f"{name} 必须是带 id 的对象数组")
            if field.get("multiple") is False and len(value) != 1:
                raise ValueError(f"{name} 是单值字段，只能填写一个 ID")
            record[name] = value
        else:
            raise ValueError(f"{name} 的字段类型 {kind!r} 尚未支持，需人工核对")
    return {"create_records": [record]}, notices


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("schema", type=Path)
    parser.add_argument("--requirement-id", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
        payload, notices = build(draft, schema, args.requirement_id)
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        for notice in notices:
            print("提示：" + notice, file=sys.stderr)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("无法生成提交数据：" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate candidate coverage and render a reviewable multi-requirement draft.

Input JSON shape:
{
  "source": "recording.m4a",
  "candidates": [
    {"id":"C1","evidence":"02:14 原话…","summary":"协作编辑",
     "decision":"register","requirement_id":"R1"},
    {"id":"C2","evidence":"03:02 原话…","summary":"重复表述",
     "decision":"merge","requirement_id":"R1"},
    {"id":"C3","evidence":"04:11 原话…","summary":"背景",
     "decision":"exclude","reason":"不是新诉求"}
  ],
  "requirements": [
    {"id":"R1","fields":{"功能名称":"…","子中心":"…"},
     "priority_reason":"…","questions":["…"]}
  ]
}
"""

import argparse
import json
import sys
from pathlib import Path


OWNERS = ["产品负责人", "研发负责人", "测试负责人"]
DEFAULT_FORM_FIELDS = [
    "子中心", "功能名称", "功能描述", "进展", "优先级",
    "产品负责人", "研发负责人", "测试负责人",
    "计划提测时间", "计划上线时间", "实际提测时间", "实际上线时间", "上线版本",
    "测试环境走查", "生产环境走查", "详情备注", "需求背景", "需求来源",
    "临时需求", "附件", "需求ID", "父记录", "本次是否走查", "情况说明",
]
REQUIRED = ["子中心", "功能名称", "功能描述", "进展", "优先级", "需求背景", "需求来源"]
DECISIONS = {"register", "merge", "exclude", "unclear"}


def value(v):
    if v is None or v == "" or v == []:
        return "内容为空"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).replace("\n", "<br>").replace("|", "\\|")


def fail(message):
    raise ValueError(message)


def validate(draft, form_fields):
    if not isinstance(draft, dict):
        fail("草稿必须是 JSON 对象")
    candidates = draft.get("candidates")
    requirements = draft.get("requirements")
    if not isinstance(candidates, list) or not candidates:
        fail("candidates 必须是非空数组")
    if not isinstance(requirements, list) or not requirements:
        fail("requirements 必须是非空数组")

    ids = [item.get("id") for item in candidates]
    req_ids = [item.get("id") for item in requirements]
    if any(not item for item in ids + req_ids):
        fail("每个候选事项和需求都必须有 id")
    if len(ids) != len(set(ids)) or len(req_ids) != len(set(req_ids)):
        fail("候选事项或需求 id 重复")

    mapped = {rid: [] for rid in req_ids}
    for item in candidates:
        cid = item["id"]
        decision = item.get("decision")
        if not item.get("summary") or not item.get("evidence"):
            fail(f"{cid} 缺少 summary 或 evidence")
        if decision not in DECISIONS:
            fail(f"{cid} decision 必须是 {', '.join(sorted(DECISIONS))} 之一")
        if decision in {"register", "merge"}:
            rid = item.get("requirement_id")
            if rid not in mapped:
                fail(f"{cid} 指向不存在的需求 {rid!r}")
            mapped[rid].append(cid)
        elif not item.get("reason"):
            fail(f"{cid} 为 {decision} 时必须给出 reason")

    warnings = []
    for item in requirements:
        rid = item["id"]
        fields = item.get("fields")
        if not isinstance(fields, dict):
            fail(f"{rid} fields 必须是对象")
        if not mapped[rid]:
            fail(f"{rid} 没有关联候选事项")
        if "主标题" in fields:
            fail(f"{rid} 截图中没有独立的主标题字段")
        if "需求 ID" in fields or "需求ID" in fields:
            fail(f"{rid} 不得填写系统生成的需求 ID")
        unknown = sorted(set(fields) - set(form_fields))
        if unknown:
            fail(f"{rid} 有不存在于表格的字段：{'、'.join(unknown)}")
        missing = [name for name in REQUIRED if not fields.get(name)]
        if missing:
            warnings.append(f"{rid} 关键字段待补：{'、'.join(missing)}")
        if not any(fields.get(name) for name in OWNERS):
            warnings.append(f"{rid} 负责人待接入飞书时确定；写入前需补齐适用负责人")
        if not item.get("priority_reason"):
            warnings.append(f"{rid} 缺少优先级判断依据")
        if "临时需求" not in fields:
            warnings.append(f"{rid} 未展示临时需求字段；按截图预览默认应为“否”")
        if fields.get("临时需求") == "是" and not item.get("temporary_reason"):
            warnings.append(f"{rid} 临时需求选“是”，但缺少依据")
    return mapped, warnings


def render(draft, mapped, warnings, form_fields, system_fields):
    lines = ["# 需求登记预览", "", f"来源：{value(draft.get('source'))}", ""]
    lines += ["## 候选事项核对", "", "| 编号 | 证据 | 事项 | 处理 | 对应需求/理由 |", "| --- | --- | --- | --- | --- |"]
    label = {"register": "拟登记", "merge": "并入", "exclude": "暂不登记", "unclear": "待澄清"}
    for item in draft["candidates"]:
        detail = item.get("requirement_id") or item.get("reason")
        lines.append(f"| {value(item['id'])} | {value(item['evidence'])} | {value(item['summary'])} | {label[item['decision']]} | {value(detail)} |")
    lines.append("")

    for item in draft["requirements"]:
        rid = item["id"]
        fields = item["fields"]
        lines += [f"## {rid}｜{value(fields.get('功能名称'))}", "", f"来源候选：{'、'.join(mapped[rid])}", "", "| 字段 | 拟填值 |", "| --- | --- |"]
        for name in form_fields:
            shown = "系统自动生成" if name in system_fields else value(fields.get(name))
            lines.append(f"| {name} | {shown} |")
        lines += ["", f"内部优先级依据：{value(item.get('priority_reason'))}", ""]
        questions = item.get("questions") or []
        if questions:
            lines += ["需确认：" + "；".join(str(q) for q in questions), ""]
    if warnings:
        lines += ["## 写入前待补", ""] + [f"- {message}" for message in warnings] + [""]
    lines += ["请确认拟新增的需求编号，并逐条指出要改的字段；未确认前不会写入飞书。完整预览应直接展示在对话中，本文件仅用于校验留档。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path, help="候选事项和需求字段的 JSON 文件")
    parser.add_argument("--schema", type=Path, help="可选：飞书实时字段 schema JSON，用于字段名称与展示顺序")
    parser.add_argument("--output", type=Path, help="可选：将预览写入 Markdown 文件")
    args = parser.parse_args()
    try:
        draft = json.loads(args.draft.read_text(encoding="utf-8"))
        form_fields = DEFAULT_FORM_FIELDS
        system_fields = {"需求ID"}
        if args.schema:
            schema = json.loads(args.schema.read_text(encoding="utf-8"))
            fields = schema.get("data", {}).get("fields")
            if schema.get("ok") is not True or not isinstance(fields, list) or not fields:
                fail("实时字段 schema 不完整")
            form_fields = [field["name"] for field in fields]
            if len(form_fields) != len(set(form_fields)):
                fail("实时字段 schema 含同名字段，需人工核实")
            system_fields = {field["name"] for field in fields if field.get("type") in {"formula", "lookup", "auto_number"}}
        mapped, warnings = validate(draft, form_fields)
        result = render(draft, mapped, warnings, form_fields, system_fields)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"草稿校验失败：{exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

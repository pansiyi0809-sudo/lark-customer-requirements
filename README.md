# 客户需求登记 Skill

把客户沟通录音或转写整理成一条或多条需求：先按业务目标归并，再展示飞书多维表格的全部字段；只有用户确认后才新增记录。适用于与本仓库 24 字段模板兼容的需求表。

**流程：**录音/转写 → 候选诉求与证据 → 按业务目标归并 → 实时字段与选项校验 → 人工确认 → 新增并回读。候选台账用于减少遗漏；查重和回读用于降低重复登记与字段写错的风险。

## 项目设计

- **减少遗漏与重复：**逐项记录客户诉求及证据，再把同一业务目标下的功能点合并为一条需求。
- **让结果可审阅：**提交前展示所有字段，缺失值明确留空，负责人、优先级和来源由使用者核对。
- **控制写入风险：**用飞书实时字段和选项校验草稿；用户确认后才写入，并回读创建结果。

## 第一次使用

1. 把仓库克隆到 `~/.codex/skills/lark-customer-requirements`，重新打开 Codex。已安装同名 Skill 时，先保留旧版备份，再用克隆目录替换。
2. 确保本机可运行 `lark-cli --help`，且 Codex 可使用 `lark-base`、`lark-shared` 等飞书 Skill。此仓库不包含飞书连接器或任何账号凭证；没有连接器时仍可整理和预览，但无法自动登记。
3. 向有权限的同事取得**目标飞书多维表格链接**，在 Skill 目录运行：

   ```bash
   python3 scripts/setup.py --base-url '你的飞书多维表格链接' --priority-policy-url '优先级规则文档链接' --temporary-default 否
   ```

   `--priority-policy-url` 可暂不填，但正式判级前需要取得适用规则。命令会创建被 Git 忽略的 `config.local.json`；每位同事在自己的电脑配置，别把内部链接或登录凭证提交到公开仓库。
4. 首次访问飞书时按 Codex 提示，用**自己的账号**完成授权；账号还须拥有目标表的编辑权限。将录音上传或粘贴转写，然后输入：“用 `$lark-customer-requirements` 整理并预览需求，确认后登记飞书。”
5. 检查每条需求的完整字段预览并明确确认。写入成功后，Skill 会回报需求 ID 和飞书记录 ID。

## 不连接飞书也能试

运行以下命令查看匿名示例的完整字段预览和模拟提交数据；它们只读本地文件，不创建飞书记录：

```bash
python3 scripts/check_draft.py examples/demo_draft.json --schema examples/demo_schema.json
python3 scripts/prepare_record.py examples/demo_draft.json examples/demo_schema.json --requirement-id R1
```

## 更新与协作

通过 Git 克隆安装的同事在 Skill 目录运行 `git pull`，重新打开 Codex 后使用新版本。维护者修改 `SKILL.md`、`references/` 或 `scripts/` 后提交并推送；变更字段模板时同时更新示例和校验脚本。公开仓库只保存 Skill 源码和匿名示例，不保存录音、转写、真实需求草稿、飞书 API 响应或本地配置。

## 项目边界

这是可复用的需求登记流程模板，不内置任何公司的表格地址、人员名单或授权。对字段名称不同的表，需要先调整模板并验证字段映射；不能仅替换 URL 就保证可写入。

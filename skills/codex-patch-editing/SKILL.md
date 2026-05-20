---
name: codex-patch-editing
description: Use when editing files in Codex and the agent needs reliable apply_patch syntax, especially to avoid JSON, shell heredocs, cat/echo/sed rewrites, or malformed patch blocks.
---

# Codex Patch Editing / apply_patch 编辑指南

使用 `apply_patch` 工具前先加载本 skill。也适用于为其他 agent 生成 patch 指令、或修复格式错误的 patch。

## 核心规则

- 使用专用的 `apply_patch` 工具编辑文件。
- `apply_patch` 是 FREEFORM 工具，输入是纯 patch 文本，不是 JSON。
- 不要通过 shell heredoc 调用 `apply_patch`。
- 不要给 `apply_patch` 输入包 ```patch 等 Markdown 代码围栏；本文档中的代码块仅为展示，实际调用时不加。
- 禁止用 `cat > file`、`echo > file`、`sed -i`、`perl -pi` 或 Python 重写脚本编辑文件。
- patch 应小而精准，基于当前文件内容生成。

## 三种基本形状

每个 patch 以 `*** Begin Patch` 开头，`*** End Patch` 结尾。

**更新文件：**

```patch
*** Begin Patch
*** Update File: path/to/file
@@
-old line
+new line
*** End Patch
```

**新增文件：**

文件路径使用仓库相对路径。

```patch
*** Begin Patch
*** Add File: path/to/file
+content line
+another content line
*** End Patch
```

**删除文件：**

```patch
*** Begin Patch
*** Delete File: path/to/file
*** End Patch
```

## 更新文件行前缀

| 前缀 | 含义 |
|------|------|
| 空格  | 上下文行（保留不变） |
| `-`  | 删除该行 |
| `+`  | 新增该行 |

新增文件时每一行内容（包括空行）都以 `+` 开头。

文件路径始终使用仓库相对路径，除非上下文明确要求其他方式。

## 失败处理

如果 patch 失败或有风险：
1. 重新读取目标文件。
2. 基于当前内容重新生成 patch。
3. 增加稳定上下文行。
4. 大编辑拆成小 patch。
5. 删除、移动、回滚、大范围重写等操作，意图不明时停止并询问。

## 调用前检查清单

- [ ] 以 `*** Begin Patch` 开头
- [ ] 以 `*** End Patch` 结尾
- [ ] 文件操作头（Add / Update / Delete File）正确
- [ ] 新增文件每行都有 `+`
- [ ] 更新文件的上下文行以空格开头
- [ ] 没有被 JSON 包裹
- [ ] 没有用 shell heredoc
- [ ] 没有包 Markdown 代码围栏
- [ ] 没有无关格式化或大范围重写

## 详细参考

- [详细语法](references/patch-syntax.md) — 多 hunk、移动/重命名、End of File 等
- [常见错误](references/common-errors.md) — 6 种典型翻车及正确写法
- [示例与模板](references/examples.md) — 最小示例集 + 非 GPT 模型的 AGENTS.md 模板

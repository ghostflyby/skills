# apply_patch 常见错误

## 1. 把 apply_patch 当 shell 命令用

错误（shell heredoc）：

```sh
apply_patch <<'PATCH'
*** Begin Patch
...
PATCH
```

正确：直接向 `apply_patch` 工具传入纯 patch 文本，不让 shell 执行它。

## 2. 用 JSON 包裹 patch

错误：

```json
{"patch":"*** Begin Patch\n..."}
```

`apply_patch` 是 FREEFORM 工具，输入不是 JSON。

正确：直接传入 patch 文本本身。

## 3. 新增文件漏掉 `+` 前缀

错误：

```patch
*** Begin Patch
*** Add File: docs/example.md
# Missing plus prefix
*** End Patch
```

正确：

```patch
*** Begin Patch
*** Add File: docs/example.md
+# Has plus prefix
*** End Patch
```

新增文件每一行（含空行）都必须以 `+` 开头。

## 4. 上下文行缺少空格前缀

错误：

```patch
*** Begin Patch
*** Update File: src/example.ts
@@
export const value = 1;
-export const oldName = true;
+export const newName = true;
*** End Patch
```

正确：

```patch
*** Begin Patch
*** Update File: src/example.ts
@@
 export const value = 1;
-export const oldName = true;
+export const newName = true;
*** End Patch
```

上下文行前面必须有一个空格。

## 5. 上下文与当前文件不一致

如果文件已被用户或其他工具修改，旧的上下文行可能无法匹配。

处理方式：先重新读取目标文件，再基于最新内容生成 patch。

## 6. 修改范围太大

大范围 patch 容易失败且难以审查。优先做小而明确的 patch，大型改动拆成多个逻辑独立的 patch。

# apply_patch 详细语法

## 更新文件

使用 `*** Update File:` 配合 `@@` 定位修改区域。

```patch
*** Begin Patch
*** Update File: src/example.ts
@@
 export function greet(name: string) {
-  return "Hello, " + name;
+  return `Hello, ${name}`;
 }
*** End Patch
```

行前缀含义：

| 前缀  | 含义           |
|-----|--------------|
| 空格  | 上下文行，文件中原样存在 |
| `-` | 删除这一行        |
| `+` | 新增这一行        |

上下文行前面的空格不可省略。

### 带更多上下文的更新

当文件中有多处相似文本时，提供更多上下文避免 patch 误匹配：

```patch
*** Begin Patch
*** Update File: src/config.ts
@@
 export const defaults = {
   timeoutMs: 30000,
-  retries: 1,
+  retries: 3,
   verbose: false,
 };
*** End Patch
```

宁可多带几行稳定上下文。

### 多处修改

一个 patch 可以更新多个文件：

```patch
*** Begin Patch
*** Update File: src/a.ts
@@
-export const name = "old";
+export const name = "new";
*** Update File: src/b.ts
@@
-console.log("old");
+console.log("new");
*** End Patch
```

同文件多个 `@@` 区块：

```patch
*** Begin Patch
*** Update File: src/example.ts
@@
-const first = "old";
+const first = "new";
@@
-const second = "old";
+const second = "new";
*** End Patch
```

## 新增文件

使用 `*** Add File:`，每一行内容（含空行）以 `+` 开头。

```patch
*** Begin Patch
*** Add File: docs/example.md
+# Example
+
+This is a new file.
+
+- Every content line starts with `+`.
*** End Patch
```

- `*** Add File:` 后写仓库相对路径。
- 空行也写成单独的 `+`。

## 删除文件

```patch
*** Begin Patch
*** Delete File: docs/old-example.md
*** End Patch
```

删除是破坏性操作，仅在用户明确要求时使用。

## 移动或重命名文件

使用 `*** Move to:`，放在 `*** Update File:` 之后：

```patch
*** Begin Patch
*** Update File: docs/old-name.md
*** Move to: docs/new-name.md
@@
-# Old Name
+# New Name
*** End Patch
```

仅重命名不修改内容：

```patch
*** Begin Patch
*** Update File: docs/old-name.md
*** Move to: docs/new-name.md
*** End Patch
```

重命名可能影响引用路径，执行前确认用户意图。

## 文件末尾标记

需要明确处理文件末尾时可用 `*** End of File`：

```patch
*** Begin Patch
*** Update File: src/example.ts
@@
 export const value = 1;
*** End of File
+export const extra = 2;
*** End Patch
```

通常不需要手写 `*** End of File`，普通 `@@` 区块已足够。

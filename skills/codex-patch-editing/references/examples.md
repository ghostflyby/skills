# apply_patch 示例与模板

## 最小可用示例集

### 替换一行

```patch
*** Begin Patch
*** Update File: README.md
@@
-Old title
+New title
*** End Patch
```

### 插入一行

```patch
*** Begin Patch
*** Update File: README.md
@@
 # Project
+Short project description.
 
 ## Usage
*** End Patch
```

### 删除一行

```patch
*** Begin Patch
*** Update File: README.md
@@
 # Project
-Temporary note.
 
 ## Usage
*** End Patch
```

### 新增文件

```patch
*** Begin Patch
*** Add File: docs/notes.md
+# Notes
+
+Initial notes.
*** End Patch
```

### 删除文件

```patch
*** Begin Patch
*** Delete File: docs/notes.md
*** End Patch
```

## 非 GPT 模型的 AGENTS.md 模板

可放入 AGENTS.md 的最短提示：

```
编辑文件时必须使用 apply_patch 工具。apply_patch 的输入是纯 patch 文本，不是 JSON，也不是 shell 命令。不要使用 cat、echo、sed -i、python 重写文件。

格式：
*** Begin Patch
*** Update File: path/to/file
@@
-old line
+new line
*** End Patch

新增文件时：
*** Begin Patch
*** Add File: path/to/file
+content line
+another content line
*** End Patch

删除文件时：
*** Begin Patch
*** Delete File: path/to/file
*** End Patch

更新文件时，上下文行前面必须有一个空格，删除行前面是 -，新增行前面是 +。
```

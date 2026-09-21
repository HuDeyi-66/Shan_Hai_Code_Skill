<p align="center">
  <img src="docs/assets/shanhai-header.png" alt="ShanHai（海珊）" />
</p>

[English](README.md) | [简体中文](README.zh-CN.md)

# ShanHai（海珊）

**法律文本证据 Skill**

海珊是一个可以独立使用的开源法律文本证据 Skill，用于法律/文本证据的结构化抽取与引用重建。它读取 UTF-8 法律文本，识别法律结构，产出带有精确字符、字节与行号区间的证据单元；引用可以回溯到原始文本并再次校验；结构问题以可检查的分类结果报出，而不是靠猜测填补。

不做静默推断：没读到就记为损失，位置不唯一就记为歧义，结构有问题就记为一个明确的诊断项。

## 独立使用是受支持的一等用法

海珊**不依赖私有 SeaFlow 基座**即可：

- 单独克隆；
- 单独测试；
- 单独运行；
- 集成到其他软件。

在 SeaFlow 环境中，海珊可以作为官方 Skill / 插件接入；是否接入是可选的，接入逻辑实现在 SeaFlow 一侧，海珊本身不导入 SeaFlow。

> **“作为 SeaFlow Skill” ≠ “必须依赖 SeaFlow 才能运行”。**
>
> 这两件事是分开的：接入 SeaFlow 是一种集成方式，独立运行是另一种方式，二者都受支持。

---

## 能力范围

下表为 Skill 在运行时声明能力，未列出的能力即未实现。

| 能力 | 支持程度 | 说明 |
| --- | --- | --- |
| 法律文本证据单元 | supported | 每个识别出的“条”产出一个证据单元；另产出“章”的容器单元，以及未识别出条文时的文档级单元 |
| 结构诊断 | supported | `empty_artifact`、`unsupported_structure`、`missing_marker`、`malformed_marker`、`numbering_gap`、`duplicate_marker`、`encoding_failure`，各自独立、互不合并 |
| 精确区间定位 | supported | 逐条记录字符区间、UTF-8 字节区间与 1 起始行号区间，均由原始字节计算 |
| 文本引用重建 | supported | 由“条”、段落或字符区间重建出精确且可再次校验的引用 |
| 段落切分 | partial | 段落按空行切分；单段条文只产出一个段落块 |
| 检索与排序 | unsupported | 本 Skill 按设计不包含检索、排序、全文索引、相似度或模糊匹配 |
| OCR 与非文本输入 | unsupported | 只读取 UTF-8 文本；图片、PDF 与二进制格式不属于文本工件 |
| 法律效力 | unsupported | 本 Skill 只记录文本“在哪里”，不对文本是否现行、是否适用、是否具有权威性作任何判断 |

歧义是一种结果，而不是错误：同一个“条”标记出现多次时，返回全部候选，且不选中任何一个；任何位置都不存在“取第一个”的兜底逻辑。

海珊**不提供**法律意见、法律语义推理、大模型生成、自主 Agent 行为、经过核验的法律权威性，也不支持所有法律文本格式。

## 安装

仅依赖 Python 标准库。无需安装任何包，也无需启动任何服务：

```bash
git clone https://github.com/HuDeyi-66/Shan_Hai_Code_Skill
cd Shan_Hai_Code_Skill
python --version        # 已在 Windows + CPython 3.13.14 上完成验证
```

以上即为全部安装步骤。

## 最小独立示例

一个函数即构成全部必要接口：

```python
from skills.shanhai import run_legal_text_evidence

result = run_legal_text_evidence("statute.txt", source_id="statute")

print(result.is_complete_success)          # 只要有任何损失，即为 False
for unit in result.units:
    print(unit.address.value, unit.loss)   # 精确位置，以及缺失了什么
```

`run_legal_text_evidence` 接受文件路径、原始字节，或由调用方自行构造的
`TextArtifact`。返回值包含证据单元、运行诊断，以及对“本次读取是否完整”的
如实判断。即使什么也没读到，也会返回结果并记录损失，而不是抛出异常。

也可以直接驱动内部组件：

```python
from skills.shanhai import ShanHaiLegalTextEvidence, TextArtifact, FixtureTextBackend

artifact = TextArtifact.from_file("statute.txt", "statute")
result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
    artifact, source_id="statute"
)
```

仓库内另有一个可直接运行的示例：

```bash
python examples/shanhai_legal_text_example.py
```

## 测试

```bash
python tests/run_all.py --quiet
```

不需要任何运行时、服务、同级目录或外部路径。仓库内有一组专门的隔离测试来保证这一点：如果 `skills/` 下任何模块引入了私有运行时依赖，测试会失败；同时会检查导入本包不会加载此类模块，并用一个**只包含本仓库**的全新解释器运行入口函数与示例。

## 已知限制

* **仅支持 UTF-8 法律文本。** 不支持 PDF、DOCX、OCR 与电子表格；能力范围之外的格式会被拒绝，而不是尝试解析。
* **中文法律标记。** 条文与章节识别针对编号中文标记（`第X条`、`第X章`）；`Article N` 形式的拉丁标题不在范围内，会被报为不支持的结构。
* **编码仅支持 UTF-8。** 无 BOM 的旧编码会被报为编码失败，而不是猜测。
* **段落切分为部分支持。** 仅按空行切分，不建模条文内部的更深层结构。
* **不做检索与排序。** 匹配与选择属于调用方的职责。
* **不做法律效力判断。** 只做抽取与定位。
* **平台验证范围。** 已在 Windows + CPython 3.13.14 上完成验证。运行时只依赖标准库，因此并未绑定该环境，但其他版本与平台尚未验证。

## 与 SeaFlow 的关系

海珊与海珞是两个独立发布的开源 Skill。SeaFlow 可以将海珊作为官方 Skill / 插件接入；独立运行不要求访问私有 SeaFlow 基座。

依赖方向只有一条：

```
SeaFlow（私有运行时）  ---适配--->  ShanHai（本仓库）
```

海珊从不导入 SeaFlow；即使完全不使用 SeaFlow，本仓库也不会有任何变化。

* SeaFlow 公开信息入口：<https://github.com/HuDeyi-66/SeaFlow>

本节链接均为**发现性链接**，不构成运行时依赖声明。

## 与海珞的关系

海珞（LuoHai）—— 表格证据 Skill —— 是海珊的**兄弟 Skill**，而不是依赖项。两个 Skill 互不导入，这一隔离由测试保证。

* 海珞仓库：<https://github.com/HuDeyi-66/Luo_Hai_Tables_Skill>

## 许可证

MIT，详见 `LICENSE`。

```
Copyright (c) 2026 Peng Wang (Hu Deyi)
```

本许可证仅覆盖本仓库。它不延伸到单独维护的私有 SeaFlow 基座；本仓库不对其作出任何许可声明。详见 `DEPENDENCIES.md`。

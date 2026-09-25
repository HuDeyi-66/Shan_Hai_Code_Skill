<p align="center">
  <img src="docs/assets/shanhai-header.png" alt="ShanHai（海珊）" />
</p>

[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [日本語](README.ja.md)

# ShanHai（海珊）

**法律文本證據 Skill**

海珊是一個可以獨立使用的開源法律文本證據 Skill，用於法律／文本證據的結構化抽取與引用重建。它讀取 UTF-8 法律文本，辨識法律結構，產出帶有精確字元、位元組與行號區間的證據單元；引用可以回溯到原始文本並再次校驗；結構問題以可檢查的分類結果報出，而不是靠猜測填補。

不做靜默推斷：沒讀到就記為損失，位置不唯一就記為歧義，結構有問題就記為一個明確的診斷項。

## 獨立使用是受支援的一等用法

海珊**不依賴私有 SeaFlow 基座**即可：

- 單獨複製（clone）；
- 單獨測試；
- 單獨執行；
- 整合到其他軟體。

在 SeaFlow 環境中，海珊可以作為官方 Skill / 外掛接入；是否接入是可選的，接入邏輯實作在 SeaFlow 一側，海珊本身不匯入 SeaFlow。

> **「作為 SeaFlow Skill」≠「必須依賴 SeaFlow 才能執行」。**
>
> 這兩件事是分開的：接入 SeaFlow 是一種整合方式，獨立執行是另一種方式，兩者都受支援。

---

<p align="center">
  <img src="docs/assets/shanhai-comic.png" alt="ShanHai（海珊）能力與邊界示意" />
</p>

## 能力範圍

下表為 Skill 在執行時宣告的能力，未列出的能力即未實作。

| 能力 | 支援程度 | 說明 |
| --- | --- | --- |
| 法律文本證據單元 | supported | 每個辨識出的「條」產出一個證據單元；另產出「章」的容器單元，以及未辨識出條文時的檔案層級單元 |
| 結構診斷 | supported | `empty_artifact`、`unsupported_structure`、`missing_marker`、`malformed_marker`、`numbering_gap`、`duplicate_marker`、`encoding_failure`，各自獨立、互不合併 |
| 精確區間定位 | supported | 逐條記錄字元區間、UTF-8 位元組區間與 1 起始行號區間，均由原始位元組計算 |
| 文本引用重建 | supported | 由「條」、段落或字元區間重建出精確且可再次校驗的引用 |
| 段落切分 | partial | 段落按空行切分；單段條文只產出一個段落塊 |
| 檢索與排序 | unsupported | 本 Skill 依設計不包含檢索、排序、全文索引、相似度或模糊比對 |
| OCR 與非文本輸入 | unsupported | 只讀取 UTF-8 文本；圖片、PDF 與二進位格式不屬於文本工件 |
| 法律效力 | unsupported | 本 Skill 只記錄文本「在哪裡」，不對文本是否現行、是否適用、是否具有權威性作任何判斷 |

歧義是一種結果，而不是錯誤：同一個「條」標記出現多次時，傳回全部候選，且不選中任何一個；任何位置都不存在「取第一個」的兜底邏輯。

海珊**不提供**法律意見、法律語意推理、大模型生成、自主 Agent 行為、經過核驗的法律權威性，也不支援所有法律文本格式。

## 目前已完成入庫並可檢索的法源

下表只列出**已完成入庫、並且可以檢索**的法源：海珊已經讀過這些文本，並能在其中定位到具體條文。若同一法源存在多個語言版本，則按語言分別列出，因為另一種語言的文本並不自動等於同等權威。

本倉庫是 **Skill，不是語料庫**。本倉庫只散布抽取能力，**法律文本本身不隨本倉庫散布**，因此複製本倉庫不會附帶下表所列的任何法源——Skill 與法源語料是兩回事。

海珊本身不做檢索排序：它在給定文本中定位並引用條文，比對與篩選由呼叫方負責。

### 中國法

| 法源 | 名稱 |
| --- | --- |
| `CN_Constitution` | 《中華人民共和國憲法》 |
| `CN_Criminal_Law` | 《中華人民共和國刑法》 |
| `CN_Criminal_Procedure_Law` | 《中華人民共和國刑事訴訟法》 |
| `CN_Civil_Code` | 《中華人民共和國民法典》 |
| `CN_Civil_Procedure_Law` | 《中華人民共和國民事訴訟法》 |
| `CN_Maritime_Law_2025` | 《中華人民共和國海商法》 |
| `CN_ECOLOGICAL_ENVIRONMENT_CODE_2026` | 《中華人民共和國生態環境法典》 |
| `CN_SPECIAL_MARITIME_PROCEDURE_LAW_1999` | 《中華人民共和國海事訴訟特別程序法》 |
| `CN_LAW_APPLICABLE_TO_FOREIGN_RELATED_CIVIL_RELATIONS_2010` | 《中華人民共和國涉外民事關係法律適用法》 |
| `CN_Anti-Unfair_Competition_Law` | 《中華人民共和國反不正當競爭法》 |
| `CN_Arbitration_Law` | 《中華人民共和國仲裁法》 |
| `CN_Bankruptcy_Law` | 《中華人民共和國企業破產法》 |
| `CN_Counterespionage_Law` | 《中華人民共和國反間諜法》 |
| `CN_Cybersecurity_Law` | 《中華人民共和國網路安全法》 |
| `CN_Labour_Law` | 《中華人民共和國勞動法》 |
| `CN_Maritime_Traffic_Safety_Law` | 《中華人民共和國海上交通安全法》 |
| `CN_Securities_Law` | 《中華人民共和國證券法》 |
| `CN_Regulation_Water_Transport` | 《國內水路運輸管理條例》 |
| `CN_Provisions_Water_Transport` | 《國內水路運輸管理規定》 |
| `CN_Provisions_on_Trade_Secret_Protection` | 《商業秘密保護規定》 |

### 日本法

| 法源 | 名稱 |
| --- | --- |
| `JP_INTL_CARRIAGE_GOODS_BY_SEA_2018` | 《国際海上物品運送法》（昭和三十二年法律第百七十二号），以其日文文本可檢索 |

### 海牙規則體系

文本**已於本地持有，但尚不能透過海珊檢索**。

| 已持有但尚不可檢索 | 原因 |
| --- | --- |
| 1924 年海牙規則、1968 年威斯比議定書、1979 年 SDR 議定書 | 英文 `Article N` 標題 |
| 海牙-威斯比合併文本 | 上述三部文書的衍生合併本，同樣是英文 `Article N` 標題 |

海珊會把它們報為不支援的結構，而不是猜測其條文。它們**刻意不列入上表的可檢索法源**，因為目前無法檢索或引用。

### 聯合國公約及相關資料

文本**已於本地持有，但尚不能透過海珊檢索**。

| 已持有但尚不可檢索 | 原因 |
| --- | --- |
| 1958 年《紐約公約》 | 其中文文本原則上可檢索，但所持文本未載明制定機關與保存機關，因此先置為待複核；英文文本與兩個 PDF 版本本 Skill 無法讀取 |
| 2008 年《鹿特丹規則》 | 僅中文文本可檢索，且其權威性尚未證實，另有四個條文無法唯一選定；英文文本與兩個 PDF 版本本 Skill 無法讀取 |
| 1978 年漢堡規則 | 英文 `Article N` 標題。其《共同理解》是該公約的解釋性附件，不是獨立文書，也不能單獨引用 |
| 1982 年《聯合國海洋法公約》 | 英文 `Article N` 標題 |
| 英國 Public General Act 1995 c.21（候選） | 掃描影像 PDF，身分無法由文本確認 |

《聯合國海洋法公約》以「來源包」形式持有：公約正文，連同屬於其組成部分的附件與《最後文件》材料。這些附件是公約的組成部分，不是獨立文書。

上表中的《鹿特丹規則》是唯一「所持文本確實可檢索」的情形：其中文文本可以解析條號，但有四個條文會傳回多個候選且不選中任何一個，且該文本的權威性尚未證實。因此它列在這裡而不是上表，以便讓這項限制緊挨著名稱顯示。

### 與《民法典》有關的一項已知限制

中文《民法典》可以檢索，但**部分以含「千」的中文數字書寫的條號目前無法定位**，因此這些條文的引用暫時無法解析——實際影響的是 999 條以上的條文。上表其他法源在條文層面均可正常解析。同一數字表示限制也在一份獨立維護的《生態環境法典》文本上被單獨觀察到。

## 安裝

只依賴標準庫。無需安裝套件，也無需啟動服務：

```bash
git clone https://github.com/HuDeyi-66/Shan_Hai_Code_Skill
cd Shan_Hai_Code_Skill
python --version        # 已在 Windows + CPython 3.13.14 上通過資格驗證
```

安裝到此為止。

## 最小獨立範例

整個必需介面只有一個函式：

```python
from skills.shanhai import run_legal_text_evidence

result = run_legal_text_evidence("statute.txt", source_id="statute")

print(result.is_complete_success)          # 有任何內容遺失即為 False
for unit in result.units:
    print(unit.address.value, unit.loss)   # 精確位置，以及缺了什麼
```

`run_legal_text_evidence` 接受檔案路徑、原始位元組，或你自己建構的 `TextArtifact`。它傳回的 run 結果帶有證據單元、執行診斷，以及對本次讀取是否完整的如實判斷。即使一份檔案什麼也沒讀出來，也會傳回結果並把損失記錄在案，而不是拋出例外。

如果需要更底層的入口：

```python
from skills.shanhai import ShanHaiLegalTextEvidence, TextArtifact, FixtureTextBackend

artifact = TextArtifact.from_file("statute.txt", "statute")
result = ShanHaiLegalTextEvidence(FixtureTextBackend()).run(
    artifact, source_id="statute"
)
```

倉庫內還有一個可直接執行的範例：

```bash
python examples/shanhai_legal_text_example.py
```

## 測試

```bash
python tests/run_all.py --quiet
```

不需要執行環境、服務、同目錄兄弟倉庫或任何外部路徑。專門的隔離測試套件對此作出證明：只要 `skills/` 下任何模組引入了私有執行環境的 import 就會失敗；它同時檢查 import 本套件不會載入此類模組，並在 `PYTHONPATH` **只包含本倉庫**的全新解譯器中執行入口函式與範例。

## 已知限制

* **只處理 UTF-8 法律文本。** 不支援 PDF、DOCX、OCR 或試算表；超出能力範圍的格式會被拒絕，而不是嘗試解析。
* **中文法律標記。** 條文與章的辨識針對編號中文標記（`第X條`、`第X章`）。`Article N` 形式的拉丁標題不在本 Skill 範圍內，會被報為不支援的結構。
* **含「千」的中文數字尚不能解析。** 部分以中文數字書寫的條號目前無法定位，因而相應引用無法解析。這一點針對的是數字書寫形式，而不是條號量級：使用半角數字的文本不受影響。
* **目錄與正文的章級歧義。** 目錄中的章標記與正文中真實的章結構並不總能可靠區分；當編號在「編」之間重新開始時，重複章號也可能是合法的。這只影響章級脈絡，條文級證據不受影響，且不做盲目去重。
* **僅支援 UTF-8 編碼。** 無 BOM 的舊編碼會被報為編碼失敗，而不是猜測。
* **段落切分是部分支援。** 段落只按空行切分；更細的條文內部結構未建模。
* **不做檢索與排序。** 比對與篩選屬於呼叫方。
* **不判斷法律效力。** 只做抽取與定位。
* **平台資格。** 已在 Windows + CPython 3.13.14 上通過驗證。執行環境只依賴標準庫，因此並未綁死在該環境，但其他版本與平台尚未驗證。

## 與 SeaFlow 的關係

海珊是兩個獨立發布的開源 Skill 之一。SeaFlow 可以把它接入為官方 Skill / 外掛；獨立使用不需要存取私有 SeaFlow 基座。

相依方向是單向的：

```
SeaFlow（私有執行環境）  ---適配--->  ShanHai（本倉庫）
```

海珊從不匯入 SeaFlow。即使你完全不使用 SeaFlow，本倉庫也不受影響。

* SeaFlow 公開資訊入口：<https://github.com/HuDeyi-66/SeaFlow>

本節連結是**發現入口**，不是執行期相依宣告。

## 與海珞（LuoHai）的關係

海珞（LuoHai）—— 表格證據 Skill —— 是海珊的**兄弟 Skill**，不是相依。兩個 Skill 互不匯入，且該隔離由測試斷言保證。

* 海珞倉庫：<https://github.com/HuDeyi-66/Luo_Hai_Tables_Skill>

## 授權條款

MIT，見 `LICENSE`。

```
Copyright (c) 2026 Peng Wang (Hu Deyi)
```

本授權條款涵蓋本倉庫，不延伸至單獨維護的私有 SeaFlow 基座執行環境；本倉庫不對其作任何授權聲明。詳見 `DEPENDENCIES.md`。

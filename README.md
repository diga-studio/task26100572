# task26100572

## entity_density：实体密度评分库

纯内存、纯 Python（无第三方依赖）的内容分析模块，衡量一篇正文有多少
字母/数字字符被明确的实体提及覆盖。词典与分析结果全部保存在内存中，
由上层直接以库的形式调用。

### 能力

- `prepare_dictionary(entities)`：准备可复用的实体词典。每个实体需要
  稳定 `id` 和若干非空 `aliases`；归一化后跨实体同名别名会被拒绝。
- `analyze_text(dictionary, text)`：对纯文本评分，返回分数与可解释的
  提及列表。
- `normalize_text(text)`：归一化（NFKC → casefold → 连续 Unicode 空白
  折叠为一个普通空格），匹配、计数、位置都以它为准。

### 规则摘要

- 提及必须匹配完整连续别名；别名首/尾字符若是 ASCII 字母、数字或
  下划线，则相邻的正文字符不能属于这三类（中文之间不要求空格）。
- 从候选提及中选出互不重叠（相邻允许）的一组：先最大化覆盖的
  字母/数字字符数（Unicode 类别 L 或 N），再最小化提及次数。
- 分数 = `floor(100 * 覆盖字符数 / 正文字母数字字符数)`，分母为 0
  时得 0 分。同一处文字不重复计覆盖，不同位置的重复提及分别计入。

### 用法

```python
from entity_density import prepare_dictionary, analyze_text

dictionary = prepare_dictionary([
    {"id": "fruit-apple", "aliases": ["苹果", "Apple", "ａｐｐｌｅ"]},
    {"id": "fruit-banana", "aliases": ["香蕉"]},
])

result = analyze_text(dictionary, "我爱ＡＰＰＬＥ和香蕉")
print(result.score)             # 70
print(result.normalized_text)   # 我爱apple和香蕉
for m in result.mentions:
    print(m.entity_id, m.start, m.end, m.text)
# fruit-apple 2 7 apple
# fruit-banana 8 10 香蕉
```

`AnalysisResult` 还提供 `covered_characters` 与 `total_characters`，
`Mention` 的 `start`/`end` 是归一化正文中的字符区间，可直接切片定位。

### 测试

```bash
python3 -m pytest tests/ -q
```

# entity-density

内容分析中的实体密度评分模块。纯 Python 标准库实现，词典与分析结果均在内存中，由上层直接作为库调用。

## 能力

- `EntityDictionary`：准备可复用的实体词典。每个实体有稳定 ID 和若干非空别名；归一化后跨实体同名别名会被拒绝。
- `analyze(text, dictionary)`：分析纯文本，返回密度分数与所选实体提及。

## 归一化

正文与别名统一执行：NFKC 归一化 → casefold → 连续 Unicode 空白折叠为一个普通空格。匹配、字符计数与位置区间均以归一化结果为准，标点不删除。

## 匹配与选择规则

- 提及必须匹配完整连续别名。若别名首/尾字符是 ASCII 字母、数字或下划线，则紧邻的正文前/后字符不能属于这三类；正文边界允许匹配，中文字符之间不要求空格。
- 从全部候选中选出互不重叠（相邻允许）的一组：先最大化覆盖的字母与数字字符数（Unicode 类别 L 或 N），覆盖量相同时最小化提及次数。
- 密度分 = `100 * 覆盖字符数 // 归一化正文中字母与数字字符总数`，分母为 0 时得 0 分。

## 用法

```python
from entity_density import EntityDictionary, analyze

dictionary = EntityDictionary()
dictionary.add_entity("e1", ["甲乙丙丁"])
dictionary.add_entity("e2", ["甲乙"])
dictionary.add_entity("e3", ["丙丁戊己"])

result = analyze("甲乙丙丁戊己", dictionary)
print(result.score)            # 100
for m in result.mentions:
    print(m.entity_id, m.alias, m.start, m.end)
    # 位置是归一化正文 result.normalized_text 中的字符区间 [start, end)
```

词典只需准备一次，可反复用于多篇文本的分析。

## 测试

```sh
python3 -m unittest discover -s tests
```

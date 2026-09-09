# -*- coding: utf-8 -*-
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import parser, report, export, llm
from sample_data import SAMPLE_MEETING_1, SAMPLE_MEETING_2, SAMPLE_MEETING_1_RESULT, SAMPLE_MEETING_2_RESULT

# 1) 文本清洗
c = parser.clean_text(SAMPLE_MEETING_1)
assert len(c) > 100
print('1. clean_text OK, len =', len(c))

# 2) 分块
chunks = parser.split_chunks(SAMPLE_MEETING_1 * 3, 8000)
print('2. split_chunks ->', len(chunks), 'blocks')

# 3) 聚合
agg = report.aggregate([SAMPLE_MEETING_1_RESULT, SAMPLE_MEETING_2_RESULT])
assert agg['meeting_count'] == 2
assert len(agg['todos']) >= 8
assert not agg['owner_df'].empty and not agg['priority_df'].empty
print('3. aggregate OK -> todos:', len(agg['todos']), '| owners:', len(agg['owner_df']))

# 4) 周报正文
text = report.build_weekly_text(agg, week_summary='本周进展顺利', highlights=['亮点A'], blockers=['风险B'], next_plan=['计划C'])
assert '本周共处理 2 场会议' in text
print('4. build_weekly_text OK')

# 5) Word 导出 - 纪要与周报
b1 = export.export_meeting_docx(SAMPLE_MEETING_1_RESULT)
b2 = export.export_weekly_docx(text, agg)
assert len(b1) > 1000 and len(b2) > 1000
print('5. export docx OK -> meeting:', len(b1), 'B, weekly:', len(b2), 'B')

# 6) LLM JSON 提取容错
j = llm._extract_json('```json\n{"a": 1}\n```')
assert j == {'a': 1}
j2 = llm._extract_json('好的，结果如下：{"b": [1,2]} 完毕')
assert j2 == {'b': [1, 2]}
j3 = llm._extract_json('【回复】{"c": {"d": true}} 结束')
assert j3 == {'c': {'d': True}}
print('6. _extract_json OK')

print()
print('ALL CORE TESTS PASSED')

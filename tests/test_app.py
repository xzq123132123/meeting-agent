# -*- coding: utf-8 -*-
"""AppTest 页面级测试：模拟用户完整操作流程"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from streamlit.testing.v1 import AppTest

APP = r"C:\Users\Administrator\Desktop\agent\meeting-agent\app.py"

at = AppTest.from_file(APP, default_timeout=60)
at.run()
assert not at.exception, f"初始加载异常: {at.exception}"
print("1. 初始加载 OK，无异常")

# 语音转写：示例模式直接模拟，无需文件
tb = [b for b in at.button if b.label == "🎙 转写为文字"]
assert tb, "未找到语音转写按钮"
tb[0].click()
at.run()
assert not at.exception, f"语音转写异常: {at.exception}"
assert "input_file_content" in at.session_state, "转写结果未写入输入"
assert len(at.session_state["input_file_content"]) > 100
print("1.5 示例语音转写 OK ->", len(at.session_state["input_file_content"]), "字")

# 分析语音转写结果（走真实分析，不重复）
an0 = [b for b in at.button if b.label == "✨ 开始智能分析"]
an0[0].click()
at.run()
assert not at.exception, f"语音纪要分析异常: {at.exception}"
assert len(at.session_state["meetings"]) == 1
print("1.8 语音内容分析 OK -> 生成 1 份纪要")

# 清空，隔离语音流程与后续示例流程
clr = [b for b in at.button if b.label == "清空已生成纪要"]
clr[0].click()
at.run()
assert not at.exception
assert len(at.session_state["meetings"]) == 0
print("1.9 清空 OK")

# 找到"载入示例 · 项目周会"按钮（主区 tab_sample 里）
btns = [b for b in at.button if b.label == "载入示例 · 项目周会"]
assert btns, "未找到示例载入按钮"
btns[0].click()
at.run()
assert not at.exception, f"载入示例后异常: {at.exception}"

# 点开始分析（示例模式默认开启）
analyze = [b for b in at.button if b.label == "✨ 开始智能分析"]
assert analyze, "未找到分析按钮"
analyze[0].click()
at.run()
assert not at.exception, f"分析后异常: {at.exception}"
assert len(at.session_state["meetings"]) == 1, f"应生成1份纪要, 实际{len(at.session_state['meetings'])}"
print("2. 示例分析 OK -> 生成 1 份纪要")

# 同一内容再次点击分析：应去重，不追加
analyze2 = [b for b in at.button if b.label == "✨ 开始智能分析"]
analyze2[0].click()
at.run()
assert not at.exception, f"重复分析异常: {at.exception}"
assert len(at.session_state["meetings"]) == 1, f"重复内容应去重, 实际{len(at.session_state['meetings'])}份"
assert any("已分析过" in str(w.value) for w in at.warning), "应提示内容已分析过"
print("2.5 重复点击去重 OK -> 仍 1 份，已提示")

# 再载入群聊并分析（凑 2 份做周报）
btns2 = [b for b in at.button if b.label == "载入示例 · 群聊记录"]
btns2[0].click()
at.run()
an2 = [b for b in at.button if b.label == "✨ 开始智能分析"]
an2[0].click()
at.run()
assert not at.exception, f"第二次分析异常: {at.exception}"
assert len(at.session_state["meetings"]) == 2, f"应生成2份纪要, 实际{len(at.session_state['meetings'])}"
print("3. 第二次分析 OK -> 共 2 份纪要")

# 生成周报
gen = [b for b in at.button if b.label == "生成周报"]
assert gen, "未找到生成周报按钮"
gen[0].click()
at.run()
assert not at.exception, f"生成周报异常: {at.exception}"
assert at.session_state["weekly_text"], "周报正文为空"
assert "本周共处理 2 场会议" in at.session_state["weekly_text"], "周报统计口径错误"
print("4. 周报生成 OK ->", at.session_state["weekly_text"].split(chr(10))[0])

# 检查下载按钮存在（纪要与周报）
dl = [b for b in at.get("download_button")]
print(f"5. 下载按钮数量: {len(dl)}（应 >= 3：2份纪要+1份周报）")
assert len(dl) >= 3

# 6) 智能问答：快捷指令（示例模式）
qa_btns = [b for b in at.button if b.label == "PPT 大纲"]
assert qa_btns, "未找到 PPT 大纲快捷按钮"
qa_btns[0].click()
at.run()
assert not at.exception, f"问答异常: {at.exception}"
assert len(at.session_state["qa_history"]) == 2, \
    f"应有问答 2 条（问+答）, 实际{len(at.session_state['qa_history'])}"
reply = at.session_state["qa_history"][1]["content"]
assert "裂缝检测项目周会汇报" in reply, "PPT 大纲回复内容不符"
print("6. 智能问答快捷指令 OK")

# 7) 多轮追问（示例模式关键词匹配）
if at.chat_input:
    at.chat_input[0].set_value("翻译成英文")
    at.run()
    assert not at.exception, f"追问异常: {at.exception}"
    assert len(at.session_state["qa_history"]) == 4, \
        f"追问后应有 4 条, 实际{len(at.session_state['qa_history'])}"
    assert "English" in at.session_state["qa_history"][3]["content"] or \
           "Minutes" in at.session_state["qa_history"][3]["content"], "英文纪要回复不符"
    print("7. 多轮追问（翻译成英文）OK")
else:
    print("7. chat_input 不可用，跳过追问测试")

print()
print("ALL APP TESTS PASSED")

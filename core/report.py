# -*- coding: utf-8 -*-
"""周报生成：聚合多份纪要，产出统计与周报内容"""
import json
import collections
import pandas as pd


def _ensure_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def aggregate(meetings: list):
    """聚合多份纪要 JSON -> 统计对象。"""
    topics, todos, risks = [], [], []
    titles = []
    for m in meetings:
        if not isinstance(m, dict):
            continue
        titles.append(m.get("title", "未命名会议"))
        topics.extend(_ensure_list(m.get("topics")))
        todos.extend(_ensure_list(m.get("todos")))
        risks.extend(_ensure_list(m.get("risks")))

    # 按负责人统计任务数
    owner_counter = collections.Counter()
    priority_counter = collections.Counter()
    for t in todos:
        owner = str(t.get("owner") or "待确认")
        priority = str(t.get("priority") or "中")
        owner_counter[owner] += 1
        priority_counter[priority] += 1

    owner_df = pd.DataFrame(
        [{"负责人": k, "任务数": v} for k, v in owner_counter.most_common()]
    ) if owner_counter else pd.DataFrame(columns=["负责人", "任务数"])

    priority_df = pd.DataFrame(
        [{"优先级": k, "数量": v} for k, v in priority_counter.most_common()]
    ) if priority_counter else pd.DataFrame(columns=["优先级", "数量"])

    return {
        "meeting_count": len(meetings),
        "titles": titles,
        "topics": topics,
        "todos": todos,
        "risks": risks,
        "owner_df": owner_df,
        "priority_df": priority_df,
    }


def build_weekly_text(agg: dict, week_summary=None, highlights=None,
                      blockers=None, next_plan=None) -> str:
    """基于聚合统计生成周报正文（模板 + 可选 LLM 润色结果）。"""
    lines = []
    lines.append(f"本周共处理 {agg['meeting_count']} 场会议/讨论，涉及 {len(agg['topics'])} 个议题，"
                 f"产出 {len(agg['todos'])} 项待办任务。")
    if week_summary:
        lines.append(f"\n【本周总结】\n{week_summary}")
    if highlights:
        lines.append("\n【本周亮点】")
        lines.extend(f"- {h}" for h in highlights)
    if blockers:
        lines.append("\n【风险与阻碍】")
        lines.extend(f"- {b}" for b in blockers)
    if next_plan:
        lines.append("\n【下周计划】")
        lines.extend(f"- {p}" for p in next_plan)
    lines.append("\n【待办任务】")
    for i, t in enumerate(agg["todos"], 1):
        owner = t.get("owner") or "待确认"
        deadline = t.get("deadline") or "未定"
        priority = t.get("priority") or "中"
        lines.append(f"{i}. [{priority}] {t.get('task', '')} — 负责人：{owner}，截止：{deadline}")
    if agg["risks"]:
        lines.append("\n【风险清单】")
        lines.extend(f"- {r}" for r in agg["risks"])
    return "\n".join(lines)


def serialize_meetings(meetings: list) -> str:
    return json.dumps(meetings, ensure_ascii=False, indent=2)

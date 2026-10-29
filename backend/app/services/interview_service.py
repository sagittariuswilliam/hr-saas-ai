"""
AI 面试服务
复用 llm.py 的 Qwen（OpenAI 兼容）chat()，提供：
1. generate_questions  —— 按 JD+简历出 6 题（固定题构），失败降级通用模板
2. maybe_followup      —— 规则判定是否需要 1 轮追问（纯规则，省 token）
3. grade_answers       —— 整卷评分出报告，JSON 解析失败降级启发式打分
"""
import json
import re
import secrets
from typing import Optional, List

from .llm import chat, qwen_llm


# ==================== token 生成 ====================

def generate_token() -> str:
    """生成 16 位候选人链接 token"""
    return secrets.token_urlsafe(12)[:16]


# ==================== 降级通用题模板（与简历/JD 无关） ====================

_FALLBACK_QUESTIONS = [
    {
        "index": 1, "type": "project_deep_dive",
        "text": "请介绍你最有成就感的一个项目：你在其中的角色、你本人独立完成的部分，以及最终可量化的结果。",
        "rubric": ["讲清个人分工而非团队整体", "有具体可量化的成果", "能说明关键技术/方法选择的原因"],
        "weak_answer_hint": "只描述团队做了什么、没有个人贡献细节",
        "min_words": 150,
    },
    {
        "index": 2, "type": "project_deep_dive",
        "text": "上述项目中遇到过最大的困难是什么？你当时有哪些备选方案，为什么最终选择了现在这个？",
        "rubric": ["困难描述具体真实", "展示权衡过程", "结果或复盘有闭环"],
        "weak_answer_hint": "泛泛而谈'沟通不畅''时间紧'，无方案对比",
        "min_words": 120,
    },
    {
        "index": 3, "type": "hard_skill",
        "text": "针对岗位所需的核心技能，请说明你目前最熟练的一项，并举一个真实工作场景说明你如何用它解决问题。",
        "rubric": ["技能与岗位需求直接相关", "场景真实有细节", "解决方案逻辑成立"],
        "weak_answer_hint": "只罗列技能名词，无落地场景",
        "min_words": 100,
    },
    {
        "index": 4, "type": "scenario",
        "text": "假设你入职后接手一个距交付只剩两周、但需求频繁变动的任务，你会怎么处理？请给出具体步骤。",
        "rubric": ["先澄清与排序需求", "主动对齐预期（上级/协作方）", "有风险控制手段"],
        "weak_answer_hint": "回答'加班做完'之类无方法步骤",
        "min_words": 100,
    },
    {
        "index": 5, "type": "behavioral",
        "text": "请讲一次你与同事或上级意见严重不一致的经历：你当时的做法和最后的结果是什么？",
        "rubric": ["事件具体可信", "体现倾听与说服而非硬扛", "有可验证的结果"],
        "weak_answer_hint": "称'从没和别人有过分歧'",
        "min_words": 100,
    },
    {
        "index": 6, "type": "motivation",
        "text": "你为什么考虑这个岗位？未来两三年你的职业重点是什么？你评估一份工作的主要标准有哪些？",
        "rubric": ["动机与岗位本身挂钩", "职业规划与岗位路径一致", "稳定性信号明确"],
        "weak_answer_hint": "只谈薪资通勤，对岗位无了解",
        "min_words": 80,
    },
]


def _fallback_questions() -> List[dict]:
    """降级通用题（深拷贝，重排 index）"""
    import copy
    qs = copy.deepcopy(_FALLBACK_QUESTIONS)
    for i, q in enumerate(qs, 1):
        q["index"] = i
    return qs


# ==================== LLM 调用 ====================

def _call_llm(prompt: str, max_tokens: int = 3000) -> Optional[str]:
    """调用 Qwen，返回文本；未配置/异常返回 None"""
    if not qwen_llm.api_key or not qwen_llm.model:
        return None
    try:
        return chat(
            [{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
    except Exception as e:
        print(f"[interview] 调用 Qwen 异常: {type(e).__name__}: {e}")
        return None


def _extract_json(text: str):
    """从 LLM 返回中提取 JSON（容忍 markdown 代码块/前后废话）"""
    if not text:
        return None
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
    text = text.strip()
    # 截取第一个 [ 或 { 到最后一个 ] 或 }
    m = re.search(r"[\[{]", text)
    if m:
        start = m.start()
        end = max(text.rfind("]"), text.rfind("}"))
        if end > start:
            text = text[start:end + 1]
    try:
        return json.loads(text)
    except Exception:
        return None


# ==================== 能力 1：出题 ====================

def generate_questions(jd_text: str, resume_text: str, position_name: str) -> List[dict]:
    """
    按固定题构生成 6 题：
    1-2 项目深挖、3 岗位硬技能、4 情境、5 行为协作、6 动机稳定性
    LLM 失败/解析失败 → 降级通用模板
    """
    prompt = f"""你是贵公司 HR 团队的资深面试官，要为候选人准备一份异步 AI 面试卷。

【应聘职位】{position_name}

【职位 JD】
{(jd_text or "")[:1200]}

【候选人简历摘要】
{(resume_text or "")[:2000]}

【出题要求】
严格按以下固定题构出 6 道题：
- 第1-2题：项目深挖（针对简历里的具体项目，第二问挖困难与权衡）
- 第3题：岗位硬技能（结合 JD 的核心技能要求）
- 第4题：情境题（入职后可能遇到的真实场景）
- 第5题：行为协作题（冲突/合作的真实经历）
- 第6题：动机与稳定性

【红线（必须遵守）】
- 禁止询问婚姻、生育、年龄、宗教信仰、政治立场、健康细节
- 题干用第二人称（"你"），每题不超过 120 字
- 每题给出 3 条评分要点 rubric、一个 weak_answer_hint（典型差回答特征）、min_words（该题合理最低字数，参考 80-200）

【输出格式】
只返回纯 JSON 数组，不要任何其他文字：
[
  {{"index":1,"type":"project_deep_dive","text":"题干","rubric":["要点1","要点2","要点3"],"weak_answer_hint":"...","min_words":150}},
  ...共6题...
]"""
    raw = _call_llm(prompt)
    data = _extract_json(raw)
    if isinstance(data, dict):  # 偶发：模型包一层 {"questions": [...]}
        data = data.get("questions") or data.get("data") or []
    if not isinstance(data, list) or len(data) < 6:
        print("[interview] 出题降级：LLM 失败或 JSON 解析失败")
        return _fallback_questions()
    # 字段规整：截断、去红线题、补齐 index
    # 兼容题干字段名漂移（text/question/题干/题目/content）
    TEXT_KEYS = ("text", "question", "题干", "题目", "content", "title")
    questions = []
    for i, q in enumerate(data[:6], 1):
        if not isinstance(q, dict):
            q = {"text": str(q)}
        text = ""
        for k in TEXT_KEYS:
            v = q.get(k)
            if v and str(v).strip():
                text = str(v).strip()
                break
        rubric = q.get("rubric") or q.get("评分要点") or []
        if isinstance(rubric, str):
            rubric = [rubric]
        questions.append({
            "index": i,
            "type": q.get("type", "other"),
            "text": text[:200],
            "rubric": [str(r) for r in (rubric or ["回答具体可信", "有细节与数据", "逻辑清晰"])][:3],
            "weak_answer_hint": str(q.get("weak_answer_hint", "")),
            "min_words": int(q.get("min_words", 100) or 100),
        })
    # 硬校验：任何一题题干为空 = 本次解析失败，整体降级到通用题（绝不存白卷）
    if any(not q["text"] for q in questions):
        print("[interview] 出题降级：存在空题干（LLM 字段名漂移），回退通用题")
        return _fallback_questions()
    return questions


# ==================== 能力 2：追问判定（纯规则，不调 LLM 省 token） ====================

def _rubric_hit_count(answer_text: str, rubric: List[str]) -> int:
    """粗糙的评分要点覆盖判定：把要点拆成 2-4 字词组，看是否出现在回答中"""
    hits = 0
    for item in rubric or []:
        words = [w for w in re.split(r"[\s，。、,.;；:/（）()]+", str(item)) if len(w) >= 2]
        if words and any(w in answer_text for w in words):
            hits += 1
    return hits


def maybe_followup(question_dict: dict, answer_text: str) -> Optional[str]:
    """
    若回答明显低于 rubric 要求（字数不足或要点覆盖 <2），生成 1 轮追问（≤60字）。
    规则判定，不调 LLM；追问文案模板化+带题干关键词。
    """
    answer_text = (answer_text or "").strip()
    min_words = int(question_dict.get("min_words", 100) or 100)
    rubric = question_dict.get("rubric") or []
    hits = _rubric_hit_count(answer_text, rubric)

    if len(answer_text) >= min_words * 0.6 and hits >= 2:
        return None

    # 提取题干关键词（取前 12 个汉字做引子）
    text = question_dict.get("text", "")
    kw = re.sub(r"[，。？！、,.!?\s]", "", text)[:12]
    if hits < 2:
        return f"你的回答里，关于「{kw}…」这部分，能否结合一个你亲历的具体事例和数据，再展开讲讲？"
    return f"关于「{kw}…」，你的回答篇幅偏短，能否补充具体的做法、遇到的困难和最终结果？"


# ==================== 能力 3：整卷评分 ====================

def grade_answers(questions_json: List[dict], answers: List[dict]) -> dict:
    """
    输入整套题（含 rubric）+ 候选人全部作答（含追问与回答），输出报告 dict。
    answers: [{index, answer_text, followup_question, followup_answer, paste_detected}]
    LLM 失败 → 启发式降级打分（不崩）。
    """
    paste_warnings = [f"第 {a['index']} 题提交时前端检测到疑似整段粘贴"
                      for a in answers if a.get("paste_detected")]

    prompt = f"""你是资深面试官，请对候选人的异步面试作答进行严格评分。

【题目与候选人作答】
{json.dumps([{"index": q.get("index"), "type": q.get("type"), "text": q.get("text"),
               "rubric": q.get("rubric"), "min_words": q.get("min_words"),
               "answer": next((a.get("answer_text") for a in answers if a.get("index") == q.get("index")), ""),
               "followup": next((a.get("followup_answer") for a in answers if a.get("index") == q.get("index")), "")}
              for q in questions_json], ensure_ascii=False)[:12000]}

【评分规则】
- 每题按 rubric 要点覆盖与回答质量打分（0-max_score），max_score 由你按题目重要性定，总和 100
- 总分 total_score 0-100；verdict：>=80 recommend，60-79 pending，<60 reject
- highlights/concerns 各 1-4 条，具体可信；hr_followup 给 HR 复试建议追问 2-4 条
- 若候选人某题存在"追问后补充回答"，以更完整信息为准

【输出格式】只返回纯 JSON：
{{"total_score":75,"verdict":"pending",
 "per_question":[{{"index":1,"score":12,"max_score":20,"comment":"一句话评语"}}],
 "highlights":["..."],"concerns":["..."],"hr_followup":["..."]}}"""

    data = _extract_json(_call_llm(prompt, max_tokens=2500) or "")
    if not isinstance(data, dict) or "total_score" not in data or "per_question" not in data:
        print("[interview] 评分降级：LLM 失败或 JSON 解析失败，使用启发式打分")
        data = _heuristic_grade(questions_json, answers)

    # 规整输出
    try:
        total = max(0, min(100, int(data.get("total_score", 0))))
    except Exception:
        total = 0
    verdict = "recommend" if total >= 80 else ("pending" if total >= 60 else "reject")
    return {
        "total_score": total,
        "verdict": verdict,
        "per_question": data.get("per_question", []),
        "highlights": data.get("highlights", []),
        "concerns": data.get("concerns", []),
        "paste_warnings": paste_warnings,
        "hr_followup": data.get("hr_followup", []),
    }


def _heuristic_grade(questions_json: List[dict], answers: List[dict]) -> dict:
    """启发式降级评分：按字数达成率 + rubric 要点覆盖"""
    n = max(len(questions_json), 1)
    per_question, concerns = [], []
    total = 0
    for q in questions_json:
        max_score = round(100 / n)
        a = next((x for x in answers if x.get("index") == q.get("index")), None)
        ans = (a or {}).get("answer_text") or ""
        word_ratio = min(1.0, len(ans) / max(int(q.get("min_words", 100) or 100), 1))
        hit_ratio = _rubric_hit_count(ans, q.get("rubric") or []) / 3.0
        score = round(max_score * (0.5 * word_ratio + 0.5 * hit_ratio))
        total += score
        per_question.append({
            "index": q.get("index"), "score": score, "max_score": max_score,
            "comment": "启发式评分（AI 评分服务暂不可用）：按篇幅与要点覆盖估算",
        })
        if score < max_score * 0.5:
            concerns.append(f"第 {q.get('index')} 题回答偏薄弱，建议复试重点确认")
    total = max(0, min(100, total))
    highlights = [] if total < 60 else ["全部题目均完成作答"]
    if not concerns:
        concerns = ["AI 评分降级，建议 HR 人工复核答案质量"]
    return {
        "total_score": total,
        "verdict": "recommend" if total >= 80 else ("pending" if total >= 60 else "reject"),
        "per_question": per_question,
        "highlights": highlights,
        "concerns": concerns,
        "hr_followup": ["建议线下复试验证项目真实性与个人贡献"],
    }

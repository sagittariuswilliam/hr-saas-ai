"""
HR-SaaS Dashboard 数据看板 API（V1.1 新增）

提供 4 个新端点（不动现有业务）：
  - GET /api/v1/dashboard/realtime      今日实时指标
  - GET /api/v1/dashboard/trend         时间序列趋势
  - GET /api/v1/dashboard/funnel        招聘漏斗（基于当前快照）
  - GET /api/v1/dashboard/ai-score      AI 匹配度均值

约束（来自 CLAUDE.md）：
- 0 预算：不引入新依赖
- 不加新表
- 用真实数据库查询
- 不动现有路由；本文件独立 router，由 main.py 显式 include
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import get_current_user
from ..models.models import User, Resume, ResumeStatus
from ..schemas.dashboard import (
    RealtimeMetricItem,
    RealtimeResponse,
    TrendPoint,
    TrendResponse,
    FunnelRates,
    FunnelResponse,
    AIScoreResponse,
)

router = APIRouter(prefix="/dashboard", tags=["数据看板(V1.1)"])


# ==================== 通用工具 ====================

def _range_window(range_key: str) -> tuple:
    """根据 range 返回 (start_date, end_date_exclusive, period_label_fn)
    - month: 当前自然月（1 号 → 下月 1 号）
    - quarter: 当前自然季度
    - year: 当前自然年
    period_label_fn 用于 trend/funnel 时间桶标签，季度返回 'YYYY-Qn'，月返回 'YYYY-MM'，年返回 'YYYY'。
    """
    today = date.today()

    if range_key == "month":
        start = today.replace(day=1)
        # 下月 1 号
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)

        def label(d):
            return f"{d.year:04d}-{d.month:02d}"

        return start, end, label

    if range_key == "year":
        start = today.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)

        def label(d):
            return f"{d.year:04d}"

        return start, end, label

    if range_key == "quarter":
        q = (today.month - 1) // 3 + 1
        start_month = (q - 1) * 3 + 1
        start = today.replace(month=start_month, day=1)
        if q == 4:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start_month + 3)

        def label(d):
            qn = (d.month - 1) // 3 + 1
            return f"{d.year:04d}-Q{qn}"

        return start, end, label

    # 默认按月
    return _range_window("month")


def _prev_window(start: date, end: date) -> tuple:
    """计算上一个等长窗口（用于 ai-score 的环比）"""
    length = (end - start).days
    prev_end = start
    prev_start = prev_end - timedelta(days=length)
    return prev_start, prev_end


def _apply_filters(query, project_id: Optional[int], position_id: Optional[int]):
    """统一过滤：未删除 + 可选 project/position"""
    query = query.filter(Resume.is_deleted == 0)
    if project_id is not None:
        query = query.filter(Resume.project_id == project_id)
    if position_id is not None:
        query = query.filter(Resume.position_id == position_id)
    return query


# ==================== 1. Realtime ====================

@router.get("/realtime", summary="实时指标（今日 vs 昨日）")
def get_realtime(
    project_id: Optional[int] = Query(None, description="项目ID过滤（不传=全部）"),
    position_id: Optional[int] = Query(None, description="职位ID过滤（不传=全部）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """今日实时指标（基于 resumes 表真实数据查询）：

    - today_resumes: created_at 落在今日的简历数
    - today_onboardings: status=onboarded 且 updated_at 落在今日
    - today_interviews: status∈{interview_scheduled, interviewing} 且 updated_at 落在今日

    vs_yesterday: 今天 - 昨天（同一指标在昨日的数值）；昨日无变化的情况下减数 = 0。
    全部基于数据库真实聚合，无 mock。
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    def count_resumes_today_created() -> int:
        q = db.query(func.count(Resume.id))
        q = _apply_filters(q, project_id, position_id)
        # SQLite 兼容性：把 date 转成字符串比较 created_at
        return q.filter(
            func.date(Resume.created_at) == today.isoformat()
        ).scalar() or 0

    def count_resumes_yesterday_created() -> int:
        q = db.query(func.count(Resume.id))
        q = _apply_filters(q, project_id, position_id)
        return q.filter(
            func.date(Resume.created_at) == yesterday.isoformat()
        ).scalar() or 0

    def count_status_updated_today(status_values: List[str]) -> int:
        q = db.query(func.count(Resume.id))
        q = _apply_filters(q, project_id, position_id)
        q = q.filter(Resume.status.in_([ResumeStatus(s) for s in status_values]))
        return q.filter(func.date(Resume.updated_at) == today.isoformat()).scalar() or 0

    def count_status_updated_yesterday(status_values: List[str]) -> int:
        q = db.query(func.count(Resume.id))
        q = _apply_filters(q, project_id, position_id)
        q = q.filter(Resume.status.in_([ResumeStatus(s) for s in status_values]))
        return q.filter(func.date(Resume.updated_at) == yesterday.isoformat()).scalar() or 0

    # 今日新简历 = 较昨日差值（按 created_at）
    today_val = count_resumes_today_created()
    yest_val = count_resumes_yesterday_created()

    # 今日新入职（按 updated_at，因为状态变到 onboarded 通常伴随 updated_at 更新）
    onboard_today = count_status_updated_today(["onboarded"])
    onboard_yest = count_status_updated_yesterday(["onboarded"])

    # 今日面试（interview_scheduled ∪ interviewing）
    interview_today = count_status_updated_today(["interview_scheduled", "interviewing"])
    interview_yest = count_status_updated_yesterday(["interview_scheduled", "interviewing"])

    realtime_resp = RealtimeResponse(
        today_resumes=RealtimeMetricItem(
            value=today_val,
            vs_yesterday=today_val - yest_val,
        ),
        today_onboardings=RealtimeMetricItem(
            value=onboard_today,
            vs_yesterday=onboard_today - onboard_yest,
        ),
        today_interviews=RealtimeMetricItem(
            value=interview_today,
            vs_yesterday=interview_today - interview_yest,
        ),
        project_id=project_id,
        position_id=position_id,
        today=today.isoformat(),
    )
    return {"code": 0, "message": "success", "data": realtime_resp}


# ==================== 2. Trend ====================

@router.get("/trend", summary="时间序列趋势（按 range 分桶）")
def get_trend(
    range: str = Query("month", pattern="^(month|quarter|year)$", description="时间范围"),
    project_id: Optional[int] = Query(None, description="项目ID过滤"),
    position_id: Optional[int] = Query(None, description="职位ID过滤"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """时间序列趋势：

    - 数据源：resumes.created_at（按简历入库时间分桶）
    - submissions: 该桶内新简历数（is_deleted=0）
    - onboardings: 该桶内 status=onboarded 的简历数（同样按 created_at）

    桶粒度：
    - month: 按自然月 YYYY-MM
    - quarter: 按自然季度 YYYY-Qn
    - year: 按自然年 YYYY

    出参只覆盖"有数据"的桶；若所有时间均无数据则 series=[]（不构造占位空桶）。
    """
    # 1) 取全量 created_at + status 的最小集（避免一次拉全表）
    q = db.query(
        func.date(Resume.created_at).label("d"),
        Resume.status,
    )
    q = _apply_filters(q, project_id, position_id)

    rows = q.all()

    bucket_submissions: Dict[str, int] = {}
    bucket_onboardings: Dict[str, int] = {}

    for r in rows:
        d_str = r.d  # sqlite 上 date(created_at) 返回 'YYYY-MM-DD'
        try:
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue

        if range == "month":
            key = f"{d.year:04d}-{d.month:02d}"
        elif range == "year":
            key = f"{d.year:04d}"
        else:  # quarter
            qn = (d.month - 1) // 3 + 1
            key = f"{d.year:04d}-Q{qn}"

        bucket_submissions[key] = bucket_submissions.get(key, 0) + 1
        status_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        if status_val == "onboarded":
            bucket_onboardings[key] = bucket_onboardings.get(key, 0) + 1

    series = [
        TrendPoint(
            date=k,
            submissions=bucket_submissions.get(k, 0),
            onboardings=bucket_onboardings.get(k, 0),
        )
        for k in sorted(set(bucket_submissions.keys()) | set(bucket_onboardings.keys()))
    ]

    trend_resp = TrendResponse(
        range=range,
        project_id=project_id,
        position_id=position_id,
        series=series,
    )
    return {"code": 0, "message": "success", "data": trend_resp}


# ==================== 3. Funnel ====================

@router.get("/funnel", summary="招聘漏斗（按 range 当前状态快照）")
def get_funnel(
    range: str = Query("month", pattern="^(month|quarter|year)$", description="时间范围"),
    project_id: Optional[int] = Query(None, description="项目ID过滤"),
    position_id: Optional[int] = Query(None, description="职位ID过滤"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """招聘漏斗（snapshot-based，按 resumes.status 当前状态聚合）。

    **口径限制（必读）**：
    本接口统计的是"截至当前停留在各状态的简历数"快照，**不是真实流程历史**。
    一份简历最终变为 onboarded 后，它只在 onboarded 桶里 +1，submitted/viewed/
    interviewing/hired 桶不会再次 +1。因此 submitted→viewed 这种"转化率"实际上是
    当前两种状态人数之比，反映的是存量结构，而非过程转化。

    区间过滤用 created_at 落在 [start, end) 内。
    """
    start, end, _ = _range_window(range)
    start_s = start.isoformat()
    end_s = end.isoformat()

    # 单次 GROUP BY status 拉回区间内的所有状态分布
    q = db.query(Resume.status, func.count(Resume.id).label("c"))
    q = _apply_filters(q, project_id, position_id)
    q = q.filter(Resume.created_at >= start_s, Resume.created_at < end_s)
    rows = q.group_by(Resume.status).all()

    stages: Dict[str, int] = {
        "submitted": 0,
        "viewed": 0,
        "interview_scheduled": 0,
        "interviewing": 0,
        "hired": 0,
        "onboarded": 0,
    }
    total = 0
    for status_val, c in rows:
        key = status_val.value if hasattr(status_val, "value") else str(status_val)
        total += c
        if key in stages:
            stages[key] = c
        # rejected 等不在 stages 中的状态：进 total，但不参与漏斗

    def pct(num, den):
        if not den:
            return 0.0
        return round(num / den * 100, 1)

    rates = FunnelRates(
        submitted_to_viewed=pct(stages["viewed"], stages["submitted"]),
        viewed_to_interview=pct(stages["interview_scheduled"], stages["viewed"]),
        interview_to_interviewing=pct(stages["interviewing"], stages["interview_scheduled"]),
        interviewing_to_hired=pct(stages["hired"], stages["interviewing"]),
        hired_to_onboarded=pct(stages["onboarded"], stages["hired"]),
    )

    funnel_resp = FunnelResponse(
        range=range,
        project_id=project_id,
        position_id=position_id,
        stages=stages,
        total=total,
        rates=rates,
    )
    return {"code": 0, "message": "success", "data": funnel_resp}


# ==================== 4. AI Score ====================

@router.get("/ai-score", summary="AI 匹配度均值（含环比）")
def get_ai_score(
    range: str = Query("month", pattern="^(month|quarter|year)$", description="时间范围"),
    project_id: Optional[int] = Query(None, description="项目ID过滤"),
    position_id: Optional[int] = Query(None, description="职位ID过滤"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI 匹配度（来自 resumes.match_score）：

    - 数据源：resumes.match_score（0-100 整数列）
    - 区间：按 created_at 过滤
    - avg_score: 区间内 match_score IS NOT NULL 的简历平均匹配度（1 位小数）
    - vs_last_period: 与等长的上一窗口均值之差（avg - prev_avg）

    注意：match_score 在不同简历中存在为 NULL 的情况，统计时自动忽略。
    """
    start, end, _ = _range_window(range)
    prev_start, prev_end = _prev_window(start, end)

    def agg(s: date, e: date):
        q = db.query(
            func.avg(Resume.match_score),
            func.count(Resume.id),
        )
        q = _apply_filters(q, project_id, position_id)
        q = q.filter(Resume.match_score.isnot(None))
        q = q.filter(Resume.created_at >= s.isoformat(), Resume.created_at < e.isoformat())
        avg_v, cnt_v = q.one()
        return (float(avg_v) if avg_v is not None else None, int(cnt_v or 0))

    cur_avg, cur_n = agg(start, end)
    prev_avg, prev_n = agg(prev_start, prev_end)

    avg_score = round(cur_avg, 1) if cur_avg is not None else 0.0
    prev_avg_v = round(prev_avg, 1) if prev_avg is not None else 0.0
    vs = round(avg_score - prev_avg_v, 1)

    ai_score_resp = AIScoreResponse(
        range=range,
        project_id=project_id,
        position_id=position_id,
        avg_score=avg_score,
        sample_count=cur_n,
        vs_last_period=vs,
        period_start=start.isoformat(),
        period_end=end.isoformat(),
    )
    return {"code": 0, "message": "success", "data": ai_score_resp}

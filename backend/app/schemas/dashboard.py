"""
Dashboard 数据看板 Pydantic Schemas（V1.1 新增）

仅用于 4 个新 dashboard endpoint 的响应结构定义。
不动现有业务 schema。
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ==================== Realtime（实时指标） ====================

class RealtimeMetricItem(BaseModel):
    """单个实时指标"""
    value: int = Field(..., description="今日数值")
    vs_yesterday: int = Field(..., description="较昨日差值（今 - 昨），可负")


class RealtimeResponse(BaseModel):
    """GET /dashboard/realtime 响应"""
    today_resumes: RealtimeMetricItem = Field(..., description="今日新简历数（created_at = 今日）")
    today_onboardings: RealtimeMetricItem = Field(..., description="今日新入职数（status=onboarded 且 updated_at = 今日）")
    today_interviews: RealtimeMetricItem = Field(..., description="今日面试数（status∈{interview_scheduled, interviewing} 且 updated_at = 今日）")
    project_id: Optional[int] = Field(None, description="项目过滤（None 表示全部）")
    position_id: Optional[int] = Field(None, description="职位过滤（None 表示全部）")
    today: str = Field(..., description="今日日期 YYYY-MM-DD（服务端口径）")


# ==================== Trend（时间趋势） ====================

class TrendPoint(BaseModel):
    """时间序列中的一个点"""
    date: str = Field(..., description="时间区间 key，month→YYYY-MM，quarter→YYYY-Qn，year→YYYY")
    submissions: int = Field(..., description="该区间新简历数")
    onboardings: int = Field(..., description="该区间最终入职数（status=onboarded 且 created_at 落入区间）")


class TrendResponse(BaseModel):
    """GET /dashboard/trend 响应"""
    range: str = Field(..., description="时间范围：month|quarter|year")
    project_id: Optional[int] = Field(None, description="项目过滤")
    position_id: Optional[int] = Field(None, description="职位过滤")
    series: List[TrendPoint] = Field(..., description="时间序列数据点")


# ==================== Funnel（漏斗） ====================

class FunnelStage(BaseModel):
    """漏斗中一个阶段的人数"""
    count: int = Field(..., description="该阶段当前停留在该状态的简历数")


class FunnelRates(BaseModel):
    """各阶段的转化率（百分比，保留 1 位小数）"""
    submitted_to_viewed: float = Field(..., description="submitted → viewed")
    viewed_to_interview: float = Field(..., description="viewed → interview_scheduled")
    interview_to_interviewing: float = Field(..., description="interview_scheduled → interviewing")
    interviewing_to_hired: float = Field(..., description="interviewing → hired")
    hired_to_onboarded: float = Field(..., description="hired → onboarded")


class FunnelResponse(BaseModel):
    """GET /dashboard/funnel 响应

    口径说明（重要）：
    本漏斗按 resumes.status 的【当前状态】聚合，统计的是"截至当前
    停留在某个状态的简历数"。**不是真实流程历史**——例如某简历
    从 submitted → onboarded 后，它只在 onboarded 计数中显示 1 次，
    之前的 submitted/viewed/interviewed/hired 计数中不再包含它。

    这意味着"submitted → viewed 转化率"等不是真实转化率，而是
    当前快照中两个状态的人数比，需要谨慎解读。
    """
    range: str = Field(..., description="时间范围：month|quarter|year")
    project_id: Optional[int] = Field(None, description="项目过滤")
    position_id: Optional[int] = Field(None, description="职位过滤")
    stages: dict = Field(..., description="各阶段人数 {submitted, viewed, interview_scheduled, interviewing, hired, onboarded}")
    total: int = Field(..., description="区间内总简历数（is_deleted=0）")
    rates: FunnelRates = Field(..., description="各阶段转化率（基于当前快照）")
    note: str = Field(
        "funnel 基于 statuses 当前快照，非流程历史；interpret with caution",
        description="口径提醒",
    )


# ==================== AI Score（AI 匹配度） ====================

class AIScoreResponse(BaseModel):
    """GET /dashboard/ai-score 响应"""
    range: str = Field(..., description="时间范围：month|quarter|year")
    project_id: Optional[int] = Field(None, description="项目过滤")
    position_id: Optional[int] = Field(None, description="职位过滤")
    avg_score: float = Field(..., description="平均匹配度（1 位小数）")
    sample_count: int = Field(..., description="样本数（match_score IS NOT NULL 且 created_at 在区间内）")
    vs_last_period: float = Field(..., description="对比上一周期差值（1 位小数；当前 - 上周期）")
    period_start: str = Field(..., description="当前周期起点 YYYY-MM-DD")
    period_end: str = Field(..., description="当前周期终点 YYYY-MM-DD")

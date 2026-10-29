"""
语音转写服务 — DashScope qwen3-asr-flash（百炼，同步 multimodal-generation 端点）

语音作答链路：
  候选人语音作答的录音 → 本服务转写为文本 → 存 answer_text → 下游评分零改动。

渠道说明：
  - 百炼 OpenAI 兼容口无 ASR 能力，故本服务直连 DashScope 原生 multimodal-generation 端点。
  - Key 通过环境变量 DASHSCOPE_API_KEY（或 backend/.env）配置。
  - 音频走 base64 直传（data URL），无公网 URL 依赖，候选人录音不出服务器之外
    （除百炼推理链路），满足 0 预算 + 隐私最小化。
  - 限制：单段音频 ≤ 5 分钟、≤ 10MB（单题 ≤60s 的场景天然满足）。
"""
import os
import base64
import json
import threading
from typing import Optional

import httpx

from ..core.config import settings

# 百炼原生多模态端点（OpenAI 兼容口无 ASR，必须走这个）
_ASR_MODEL = "qwen3-asr-flash"

# 转写超时：连接 10s / 总 120s（本地 60s 音频实测 <10s，留足余量）
_CONNECT_TIMEOUT = 10
_READ_TIMEOUT = 120

# 音频规格硬上限（超限直接拒绝，不发请求）
_MAX_AUDIO_BYTES = 10 * 1024 * 1024


class ASRError(RuntimeError):
    """语音转写失败（配置缺失/超限/网络/接口报错统一归到这里，调用方决定降级策略）"""


def _get_api_key() -> str:
    """读取 DASHSCOPE_API_KEY（环境变量 / backend/.env，经 Settings 加载）"""
    key = (settings.DASHSCOPE_API_KEY or os.environ.get("DASHSCOPE_API_KEY", "")).strip()
    if not key:
        raise ASRError("语音服务未配置：请在 .env 中设置 DASHSCOPE_API_KEY")
    return key


def transcribe_wav(audio_bytes: bytes) -> str:
    """
    转写一段 WAV（16kHz 单声道推荐）音频为中文文本。

    Args:
        audio_bytes: 音频文件原始字节

    Returns:
        转写文本（可能为空串——静音录音）

    Raises:
        ASRError: 配置缺失 / 超过大小上限 / 网络或接口错误 / 响应格式异常
    """
    if not audio_bytes:
        raise ASRError("音频为空")
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        raise ASRError("音频超过 10MB 上限")

    api_key = _get_api_key()
    data_url = "data:audio/wav;base64," + base64.b64encode(audio_bytes).decode()
    payload = {
        "model": _ASR_MODEL,
        "input": {
            "messages": [{"role": "user", "content": [{"audio": data_url}]}]
        },
        "parameters": {"asr_options": {"enable_itn": True}},
    }
    try:
        resp = httpx.post(
            settings.DASHSCOPE_ASR_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json=payload,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        )
    except httpx.HTTPError as exc:
        raise ASRError(f"语音服务网络异常: {type(exc).__name__}") from exc

    if resp.status_code != 200:
        # 不透出原始 body 给最终用户，但留到日志层面可查（调用方 log exc）
        raise ASRError(f"语音服务返回 {resp.status_code}")

    try:
        data = resp.json()
        content = data["output"]["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        raise ASRError("语音服务响应格式异常") from exc

    # content 是 [{"text": "..."}] 形态（实测 2026-10-12）
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(seg.get("text", "") for seg in content
                       if isinstance(seg, dict)).strip()
    raise ASRError("语音服务响应内容格式异常")

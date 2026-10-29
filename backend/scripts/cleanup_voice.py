#!/usr/bin/env python3
"""
VR-11: 面试原声 30 天自动清理。
删除 uploads/interview_voices/ 下 mtime 超过 30 天的音频文件及空目录。
DB 中的转写文本与 voice_answer_urls 引用保留（已脱敏为文字，仅文件删除）。
建议配置定时任务每日执行（保留期 30 天）。
"""
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(BASE_DIR, "uploads", "interview_voices")
RETENTION_DAYS = 30

def main():
    if not os.path.isdir(VOICE_DIR):
        print("no voice dir, nothing to do")
        return
    cutoff = time.time() - RETENTION_DAYS * 86400
    removed = 0
    freed = 0
    for root, dirs, files in os.walk(VOICE_DIR, topdown=False):
        for fname in files:
            fp = os.path.join(root, fname)
            try:
                if os.path.getmtime(fp) < cutoff:
                    freed += os.path.getsize(fp)
                    os.remove(fp)
                    removed += 1
            except OSError as e:
                print(f"skip {fp}: {e}", file=sys.stderr)
        # 清掉空的 token 目录
        if root != VOICE_DIR and not os.listdir(root):
            try:
                os.rmdir(root)
            except OSError:
                pass
    print(f"removed={removed} freed={freed/1024/1024:.1f}MB")

if __name__ == "__main__":
    main()

#!/bin/bash
# AdCraft quick tunnel 监控（adcraft-public-url.timer 每 5 分钟触发）
# 1) 从 cloudflared journal 提取最新 quick tunnel URL，写入 /opt/adcraft/public_url.txt
# 2) 看门狗：检测到隧道注册失败或公网不可达时自动重启 cloudflared（10 分钟冷却防重启风暴）
#    —— 2026-08-15 事故：quick tunnel hostname 被 CF 回收（Tunnel not found），站点公网整体不可达，须人工重启。
set -u
OUT=/opt/adcraft/public_url.txt
STATE=/opt/adcraft/.tunnel_last_restart
WATCHLOG=/opt/adcraft/tunnel-watchdog.log
NOW=$(date '+%Y-%m-%d %H:%M:%S')
NOW_EPOCH=$(date +%s)
COOLDOWN=600  # 两次重启至少间隔 10 分钟

# --- 1. 提取 journal 里最新的 quick tunnel URL（重启后新 URL 约 10 秒后打印）---
URL=$(journalctl -u cloudflared-tunnel --no-pager -o cat 2>/dev/null \
  | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1)

# --- 2. 看门狗：隧道是否异常 ---
TUNNEL_DEAD=0
# 2a. 最近一次重启之后 journal 是否出现注册失败（Tunnel not found / Register tunnel error）
LAST=$(cat "$STATE" 2>/dev/null || echo 0)
if [ "$LAST" -gt 0 ]; then
  SINCE=$(date -d "@$LAST" '+%Y-%m-%d %H:%M:%S')
else
  SINCE="15 min ago"
fi
if journalctl -u cloudflared-tunnel --since "$SINCE" --no-pager -o cat 2>/dev/null \
   | grep -qE "Register tunnel error|Tunnel not found"; then
  TUNNEL_DEAD=1
fi
# 2b. 有 URL 且公网连接级失败（HTTP 错误码 22 不算，那说明隧道本身可达）
if [ -n "$URL" ]; then
  curl -s -o /dev/null --max-time 15 "$URL/" >/dev/null 2>&1
  RC=$?
  if [ "$RC" -ne 0 ] && [ "$RC" -ne 22 ]; then
    TUNNEL_DEAD=1
  fi
fi

if [ "$TUNNEL_DEAD" = "1" ] && [ $((NOW_EPOCH - LAST)) -ge "$COOLDOWN" ]; then
  echo "[$NOW] 隧道异常（URL=${URL:-无}），重启 cloudflared" >> "$WATCHLOG"
  systemctl restart cloudflared-tunnel.service
  echo "$NOW_EPOCH" > "$STATE"
fi

# --- 3. 记录当前 URL（tail -1 取 journal 最新一条）---
if [ -n "$URL" ]; then
  printf 'last_updated=%s\nurl=%s\n' "$NOW" "$URL" > "$OUT"
else
  # 新日志里还没有 URL（如服务刚重启），保留上次记录，只更新检查时间
  if [ -f "$OUT" ]; then
    OLD=$(grep '^url=' "$OUT" | head -1)
    { printf 'last_checked=%s\n' "$NOW"; printf '%s\n' "$OLD"; } > "$OUT"
  else
    printf 'last_checked=%s\nurl=(not found yet)\n' "$NOW" > "$OUT"
  fi
fi

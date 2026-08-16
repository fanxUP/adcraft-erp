#!/usr/bin/env bash
# AdCraft 健康监控：探测后端健康 + 磁盘/内存阈值，异常时输出告警并可推送 webhook
set -u

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/api/v1/health}"
DISK_THRESHOLD="${DISK_THRESHOLD:-85}"
MEM_THRESHOLD="${MEM_THRESHOLD:-90}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"   # 钉钉/企业微信/自定义 webhook，留空则不推送

NOW=$(date '+%F %T')
issues=()

# 1) 后端健康（DB 连通性）
if ! curl -sf -m 5 "$HEALTH_URL" >/dev/null 2>&1; then
  issues+=("后端健康检查失败: $HEALTH_URL")
fi

# 2) 磁盘使用率
DISK_USED=$(df / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
if [ -n "$DISK_USED" ] && [ "$DISK_USED" -gt "$DISK_THRESHOLD" ] 2>/dev/null; then
  issues+=("磁盘使用率 ${DISK_USED}% > ${DISK_THRESHOLD}%")
fi

# 3) 内存使用率
MEM_USED=$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')
if [ -n "$MEM_USED" ] && [ "$MEM_USED" -gt "$MEM_THRESHOLD" ] 2>/dev/null; then
  issues+=("内存使用率 ${MEM_USED}% > ${MEM_THRESHOLD}%")
fi

if [ ${#issues[@]} -gt 0 ]; then
  MSG="[AdCraft] $(IFS=';'; echo "${issues[*]}")"
  echo "[$NOW] ALERT: $MSG" >&2
  if [ -n "$ALERT_WEBHOOK_URL" ]; then
    curl -sf -m 10 -H "Content-Type: application/json" \
      -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"$MSG\"}}" \
      "$ALERT_WEBHOOK_URL" >/dev/null 2>&1 || true
  fi
  exit 1
fi

exit 0

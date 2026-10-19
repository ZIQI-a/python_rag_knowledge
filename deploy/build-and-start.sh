#!/usr/bin/env bash
# 首次部署使用独立后台任务构建，避开面板接口超时；状态和日志可在文件管理中查看。
set -Eeuo pipefail
umask 077
cd /opt/rag-kb

compose_file=${1:-/opt/rag-kb/deploy/docker-compose.yml}
log_file=/opt/rag-kb/deploy/build.log
status_file=/opt/rag-kb/deploy/build.status

# 只允许本脚本运行一个实例；不要同时点击面板的启动或重建。
exec 9>/opt/rag-kb/deploy/.build.lock
if ! flock -n 9; then
  echo "已有构建脚本运行，请查看 deploy/build.log。" >&2
  exit 1
fi

exec > >(tee -a "$log_file") 2>&1

finish() {
  # 无论成功、错误或收到停止信号，都保存最终状态。
  local code=$?
  local result=FAILED
  if [ "$code" -eq 0 ]; then result=SUCCESS; fi
  printf '%s exit_code=%s time=%s\n' "$result" "$code" "$(date -Is)" > "$status_file"
  echo "[$(date -Is)] $result，退出码 $code"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'RUNNING time=%s\n' "$(date -Is)" > "$status_file"
echo "[$(date -Is)] 开始构建；日志：$log_file"

# 先校验，不把完整配置或环境变量写入日志。
docker compose -f "$compose_file" config --quiet
export COMPOSE_PARALLEL_LIMIT=1

# 每次仅构建一个服务；后端首次安装依赖后，其余服务复用构建缓存。
echo "[$(date -Is)] 阶段 1/3：构建数据库镜像"
docker compose --progress plain -f "$compose_file" build postgres
echo "[$(date -Is)] 阶段 2/3：构建后端镜像"
docker compose --progress plain -f "$compose_file" build init api worker

# 初始化失败时保留容器，便于在面板中查看 init 日志；不删除数据卷。
echo "[$(date -Is)] 阶段 3/3：启动数据库、初始化、API 和 worker"
docker compose -f "$compose_file" up -d --no-build
docker compose -f "$compose_file" ps -a

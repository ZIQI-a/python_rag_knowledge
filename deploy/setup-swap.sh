#!/usr/bin/env bash
# 为当前小内存服务器增加 2 GiB Swap；已有 Swap 时跳过，不覆盖已有文件。
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "请在 1Panel 的 root 终端中执行此脚本。" >&2
  exit 1
fi

if [ -n "$(swapon --show=NAME --noheadings)" ]; then
  echo "已有 Swap，保留现有配置："
  swapon --show
  exit 0
fi

swap_path=/swapfile-rag-knowledge
if [ -e "$swap_path" ]; then
  echo "$swap_path 已存在，请先检查；脚本不会覆盖它。" >&2
  exit 1
fi

# 创建文件后仍需为系统保留磁盘空间，防止小磁盘被占满。
available_kb=$(df -Pk / | awk 'NR == 2 {print $4}')
if [ "$available_kb" -lt 4194304 ]; then
  echo "根分区剩余不足 4 GiB，请先释放空间再配置 Swap。" >&2
  exit 1
fi

fallocate -l 2G "$swap_path"
chmod 600 "$swap_path"
mkswap "$swap_path"
swapon "$swap_path"

# 首次添加开机挂载条目；不修改其他已有挂载配置。
if ! awk -v path="$swap_path" '$1 == path {found=1} END {exit !found}' /etc/fstab; then
  printf '%s none swap sw 0 0\n' "$swap_path" >> /etc/fstab
fi

echo "已启用 2 GiB Swap，并配置开机启用。"
free -h

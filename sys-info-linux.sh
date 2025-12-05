#!/bin/bash

if [ -r /etc/os-release ]; then
    # Подключаем файл как переменные окружения: появится $PRETTY_NAME, $NAME и т.п.
    . /etc/os-release
    OS_NAME="$PRETTY_NAME"
else
    OS_NAME="$(uname -o) $(uname -r)"
fi

KERNEL="Linux $(uname -r)"       # Версия ядра
ARCH="$(uname -m)"               # Архитектура (x86_64, armv7l, и т.п.)
HOSTNAME="$(hostname)"           # Имя машины
USER_NAME="$(whoami)"            # Текущий пользователь

mem_kb() {
    # Берём строку по ключу, например "MemTotal:", и вытаскиваем второе поле (число в kB)
    grep "^$1:" /proc/meminfo | awk '{print $2}'
}

mem_total_kb=$(mem_kb MemTotal)
mem_avail_kb=$(mem_kb MemAvailable)
swap_total_kb=$(mem_kb SwapTotal)
swap_free_kb=$(mem_kb SwapFree)
vmalloc_kb=$(mem_kb VmallocTotal)

# Если VmallocTotal нет (на некоторых системах), просто считаем 0
[ -z "$vmalloc_kb" ] && vmalloc_kb=0

ram_total_mb=$((mem_total_kb / 1024))
ram_free_mb=$((mem_avail_kb / 1024))
swap_total_mb=$((swap_total_kb / 1024))
swap_free_mb=$((swap_free_kb / 1024))
vmalloc_mb=$((vmalloc_kb / 1024))

# ---------- Процессоры и load average ----------

CPUS="$(nproc)"              

# /proc/loadavg хранит 3 значения средней загрузки за 1, 5 и 15 минут
read load1 load5 load15 _ < /proc/loadavg


declare -A FSTYPE         

# Читаем список всех точек монтирования
while read -r dev mnt fstype rest; do
    # Отфильтровываем "служебные" файловые системы
    case "$fstype" in
        proc|sysfs|tmpfs|devtmpfs|devpts|cgroup*|overlay|squashfs|ramfs|rpc_pipefs|securityfs|pstore|autofs|mqueue|debugfs|tracefs)
            continue;;
    esac
    FSTYPE["$mnt"]="$fstype"
done < /proc/mounts

echo "OS: $OS_NAME"
echo "Kernel: $KERNEL"
echo "Architecture: $ARCH"
echo "Hostname: $HOSTNAME"
echo "User: $USER_NAME"
echo "RAM: ${ram_free_mb}MB free / ${ram_total_mb}MB total"
echo "Swap: ${swap_total_mb}MB total / ${swap_free_mb}MB free"
echo "Virtual memory: ${vmalloc_mb}MB"
echo "Processors: $CPUS"
echo "Load average: $load1, $load5, $load15"
echo "Drives:"

# df -kP даёт размеры в килобайтах в удобном для парсинга формате (POSIX)
df -kP | tail -n +2 | while read -r fs size used avail pct mountpoint; do
    fstype="${FSTYPE[$mountpoint]}"
    [ -z "$fstype" ] && continue   # пропускаем, если не нашли тип ФС в /proc/mounts

    total_gb=$((size / 1024 / 1024))
    free_gb=$((avail / 1024 / 1024))

    printf "  %-10s %-7s %dGB free / %dGB total\n" "$mountpoint" "$fstype" "$free_gb" "$total_gb"
done

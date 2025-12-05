import ctypes, sys
from ctypes import wintypes

# === Подключение системных библиотек Windows (WINAPI DLL) ===
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)   # ядро WinAPI
psapi    = ctypes.WinDLL('psapi',    use_last_error=True)   # API производительности
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)   # безопасность / пользователи
ntdll    = ctypes.WinDLL('ntdll',    use_last_error=True)   # внутреннее API Windows

to_mb = lambda x: x // (1024 * 1024)
to_gb = lambda x: x // (1024 * 1024 * 1024)


# ---------- ОС через RtlGetVersion (WinAPI: ntdll.dll) ----------
class OSINFO(ctypes.Structure):
    _fields_ = [
        ('Size', wintypes.DWORD),
        ('Major', wintypes.DWORD),
        ('Minor', wintypes.DWORD),
        ('Build', wintypes.DWORD),
        ('Platform', wintypes.DWORD),
        ('CSD', ctypes.c_wchar * 128),
        ('SPMajor', wintypes.WORD),
        ('SPMinor', wintypes.WORD),
        ('SuiteMask', wintypes.WORD),
        ('ProductType', ctypes.c_ubyte),
        ('Reserved', ctypes.c_ubyte),
    ]

def get_os():
    info = OSINFO()
    info.Size = ctypes.sizeof(info)
    ntdll.RtlGetVersion(ctypes.byref(info))   # ← ВЫЗОВ WinAPI
    return "Windows 10 or Greater" if info.Major >= 10 else f"Windows {info.Major}.{info.Minor}"


# ---------- Имя компьютера (WinAPI: kernel32.dll) ----------
def get_computer():
    buf = ctypes.create_unicode_buffer(64)
    size = wintypes.DWORD(len(buf))
    kernel32.GetComputerNameW(buf, ctypes.byref(size))  # ← ВЫЗОВ WinAPI
    return buf.value


# ---------- Имя пользователя (WinAPI: advapi32.dll) ----------
def get_user():
    buf = ctypes.create_unicode_buffer(64)
    size = wintypes.DWORD(len(buf))
    advapi32.GetUserNameW(buf, ctypes.byref(size))       # ← ВЫЗОВ WinAPI
    return buf.value


# ---------- Архитектура и CPU (WinAPI: kernel32.dll) ----------
class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ('arch', wintypes.WORD),
        ('res', wintypes.WORD),
        ('PageSize', wintypes.DWORD),
        ('MinAddr', ctypes.c_void_p),
        ('MaxAddr', ctypes.c_void_p),
        ('Mask', ctypes.c_void_p),
        ('CPUs', wintypes.DWORD)
    ]

def get_cpu_arch():
    info = SYSTEM_INFO()
    kernel32.GetNativeSystemInfo(ctypes.byref(info))      # ← ВЫЗОВ WinAPI
    arch = {9: "x64 (AMD64)", 0: "x86", 5: "ARM"}.get(info.arch, "Unknown")
    return arch, info.CPUs


# ---------- Память (WinAPI: GlobalMemoryStatusEx из kernel32.dll) ----------
class MEMORY(ctypes.Structure):
    _fields_ = [
        ('Size', wintypes.DWORD),
        ('Load', wintypes.DWORD),
        ('TotalPhys', ctypes.c_ulonglong),
        ('AvailPhys', ctypes.c_ulonglong),
        ('TotalPF', ctypes.c_ulonglong),
        ('AvailPF', ctypes.c_ulonglong),
        ('TotalVirt', ctypes.c_ulonglong),
        ('AvailVirt', ctypes.c_ulonglong),
        ('Ext', ctypes.c_ulonglong),
    ]

def get_memory():
    m = MEMORY()
    m.Size = ctypes.sizeof(MEMORY)
    kernel32.GlobalMemoryStatusEx(ctypes.byref(m))        # ← ВЫЗОВ WinAPI
    used = to_mb(m.TotalPhys - m.AvailPhys)
    total = to_mb(m.TotalPhys)
    virt = to_mb(m.TotalPF)
    return used, total, virt, m.Load


# ---------- Файл подкачки (WinAPI: GetPerformanceInfo из psapi.dll) ----------
class PERF(ctypes.Structure):
    _fields_ = [
        ('Size', wintypes.DWORD),
        ('CommitTotal', ctypes.c_size_t),
        ('CommitLimit', ctypes.c_size_t),
        ('CommitPeak', ctypes.c_size_t),
        ('_', ctypes.c_size_t * 7),
        ('PageSize', ctypes.c_size_t)
    ]

def get_pagefile():
    p = PERF()
    p.Size = ctypes.sizeof(PERF)
    psapi.GetPerformanceInfo(ctypes.byref(p), p.Size)      # ← ВЫЗОВ WinAPI
    cur = to_mb(p.CommitTotal * p.PageSize)
    lim = to_mb(p.CommitLimit * p.PageSize)
    return cur, lim


# ---------- Диски (WinAPI: GetLogicalDriveStrings + GetDiskFreeSpaceEx) ----------
def get_drives():
    buf = ctypes.create_unicode_buffer(256)
    kernel32.GetLogicalDriveStringsW(len(buf), buf)        # ← ВЫЗОВ WinAPI
    for d in buf.value.split('\x00'):
        if d:
            fs = ctypes.create_unicode_buffer(16)
            kernel32.GetVolumeInformationW(d, None, 0, None, None, None, fs, len(fs))  # ← WinAPI
            free = ctypes.c_ulonglong()
            total = ctypes.c_ulonglong()
            kernel32.GetDiskFreeSpaceExW(d, None, ctypes.byref(total), ctypes.byref(free))  # ← WinAPI
            yield d, fs.value, to_gb(free.value), to_gb(total.value)


# ---------- Основной вывод ----------
os_str = get_os()
pc     = get_computer()
user   = get_user()
arch, cpu = get_cpu_arch()
ram_u, ram_t, virt, load = get_memory()
pcur, pmax = get_pagefile()

print(f"OS: {os_str}")
print(f"Computer Name: {pc}")
print(f"User: {user}")
print(f"Architecture: {arch}")
print(f"RAM: {ram_u}MB / {ram_t}MB")
print(f"Virtual Memory: {virt}MB")
print(f"Memory Load: {load}%")
print(f"Pagefile: {pcur}MB / {pmax}MB\n")
print(f"Processors: {cpu}")
print("Drives:")
for d, fs, fr, tt in get_drives():
    print(f"  - {d} ({fs}): {fr} GB free / {tt} GB total")

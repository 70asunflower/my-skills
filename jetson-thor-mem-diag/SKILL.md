---
name: jetson-thor-mem-diag
description: Diagnose and reclaim mysterious RAM usage on a Jetson AGX Thor (Blackwell, unified memory) when jtop/tegrastats show tens of GB "used" but ps shows no model process, the port is not listening, and `free -h` reports large `available`. Recognizes the KReclaimable NVIDIA driver cache pool trap and the free-vs-jtop accounting mismatch; recovers memory with drop_caches. Trigger when the user mentions Thor memory weirdness, jtop showing 103G, KReclaimable, drop_caches, or "memory not freed after stopping llama-server / model still resident in RAM".
compatibility: WorkBuddy on Windows with Python 3 and SSH/paramiko access to the Thor box. Default target 10.120.66.3 (root) reached via D:\Project\workspace\workbuddy\thor-deploy\ssh_exec.py. Credentials are user-specific — never commit them; read from the workspace script or environment.
metadata:
  version: "1.0.0"
  target: "WorkBuddy + Jetson AGX Thor"
---

# Jetson Thor 内存异常排查与回收

## 触发场景（一句话识别）
- jtop / tegrastats 显示 `RAM xxxG/122GB` 占用高，但 `ps` 找不到 llama-server / vLLM / python 训练进程
- 模型服务端口（如 8080）没监听，内存却还被占
- `free -h` 报 `used 5.6G` 但 jtop 报 `used 103G` —— 两个工具数字"打架"
- 用户质疑："是不是没清干净 / 模型权重还驻留在内存 / 统一内存占了 103GB"

## 根因（核心知识）
Jetson AGX Thor 是 **128GB LPDDR5X 统一内存**，GPU 与主存共享。CUDA 进程（llama-server / vLLM / PyTorch）加载大模型权重后，即便**进程已退出**，NVIDIA Tegra/Blackwell 内核驱动仍会把那块统一内存保留为一个**可回收缓存池**，对外表现为：

```
/proc/meminfo:
KReclaimable:   103453416 kB   # ≈ 98.6 GB，驱动保留的 GPU 页缓存池
```

这笔内存**不挂在任何一个用户进程的 RSS 上**，所以常规手段都"看不到"它：
- `ps aux --sort=-%mem` 看不到（无大进程）
- `lsof | grep .gguf` 看不到打开的文件
- `ss -tlnp | grep 8080` 端口已释放

但它确实存在，体量 ≈ 你刚跑的模型量化体积（如 UD-IQ3_XXS ≈ 103GB），所以 jtop 显示的占用几乎正好等于模型体积。

## 为什么 free 和 jtop 数字不一样
同一笔 KReclaimable 内存，两家统计口径不同：

| 工具 | KReclaimable 算进 | 表现 |
|---|---|---|
| `free -h` | `available` | used 只报 ~5.6G，available 报 ~117G（误导性地"看起来很空"） |
| jtop | `used` | used 报 ~103G（直观但偏保守） |

jtop 没坏，`free` 也没坏 —— 只是对"已用"定义不同。**jtop 的 `used` 才是你肉眼看到的占用量**；`free` 的 `available` 才是"系统还能拿出来用"的真实数字。这也是为什么盲目信 `free` 会得出"内存很空"的错误结论。

## 诊断流程（按序执行）
1. `free -h` —— 看 used / available 是否自相矛盾
2. `cat /proc/meminfo` —— 看 `KReclaimable`、`MemFree`、`MemAvailable`
3. `ps aux | grep -i llama`（及 vllm / python 训练进程）—— 确认进程确实已退
4. `ss -tlnp | grep <port>` —— 确认服务端口已释放
5. `find /proc -maxdepth 2 -type l -name exe -exec readlink {} \; 2>/dev/null | grep -i llama` —— 兜底确认无残留二进制
6. 若 `KReclaimable ≈ 模型体积` 且无任何相关进程 → **确诊驱动缓存池，既非泄漏、也非进程残留**

### 一键诊断（Thor 远程）
```bash
cd /d/Project/workspace/workbuddy/thor-deploy
python ssh_exec.py "free -h; echo '---'; grep -E 'MemFree|MemAvailable|KReclaimable|AnonPages' /proc/meminfo; echo '--- procs ---'; ps aux | grep -iE 'llama|vllm' | grep -v grep; echo '--- port ---'; ss -tlnp | grep 8080 || echo 'port free'"
```

## 回收命令（已验证有效）
在 Thor 上执行：
```bash
sync
echo 3 > /proc/sys/vm/drop_caches
```
执行后核对 `/proc/meminfo`：
```
KReclaimable: 从 ~103G   →  98M
MemFree:      从 ~1.4G   →  ~118G
```
jtop 随即显示 RAM ~4-5G / 122G。

### 一键回收（Thor 远程）
```bash
cd /d/Project/workspace/workbuddy/thor-deploy
python ssh_exec.py "sync; echo 3 > /proc/sys/vm/drop_caches; grep -E 'MemFree|KReclaimable' /proc/meminfo"
```

## 给用户的结论话术
> 不是没清干净——llama-server 进程确实杀了，是 Tegra/Blackwell 驱动保留了 CUDA 退出后的统一内存缓存池（`KReclaimable`，约 103G，正好等于模型体积）。它不是进程内存，所以 `ps` 看不到；`free` 把它算进 `available` 所以显示很空，jtop 把它算进 `used` 所以显示占满。两者都对，只是口径不同。已用 `echo 3 > /proc/sys/vm/drop_caches` 手动回收，内存回到 ~118G 空闲。

## 复用要点
- 这是 Jetson 统一内存架构的**正常行为，不是内存泄漏**。驱动为性能保留池，内存压力下内核会自动回收，但 `free` 的 free 列不会主动体现，需手动 `drop_caches`。
- 每次在 Thor 杀掉大模型服务后，若 jtop 还显示几十 G 占着，直接跑上面的 `sync && echo 3 > /proc/sys/vm/drop_caches` 两行。
- 不要靠 `free -h` 的 `used` 列判断 Thor 内存是否干净，要看 `/proc/meminfo` 的 `KReclaimable`。
- 远程执行一律走 `D:\Project\workspace\workbuddy\thor-deploy\ssh_exec.py`，内含 Thor 的 host/user/pass（不要硬编码到别处）。
- 区分 `EMC 0%`：`EMC = External Memory Controller` = 内存**带宽**利用率，不是内存**占用量**；0% 只代表此刻无活跃读写，不能作为"模型已卸载"的证据。判断依据是 `free`/`/proc/meminfo`/`ps`。

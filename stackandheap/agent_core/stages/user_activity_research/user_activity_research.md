# aw-client 读取/查询指南（面向数据分析，不涉及写入）

> 适用版本：aw-client 0.5.x；示例基于本仓库 `.venv` 环境与本机运行的 ActivityWatch 服务（默认端口 5600）。
>
> 文档目标：只覆盖“读取/查询”能力，帮助数据分析师顺畅获取 ActivityWatch 数据进行统计与建模。本文显式排除任何写入、创建或修改服务器端数据的 API。

- 基本概念
  - Bucket（桶）：按来源/类型存放事件的集合，例如 `aw-watcher-window_*`、`aw-watcher-afk_*`、`aw-watcher-vscode_*`。
  - Event（事件）：最小记录单元，常见字段：`id`, `timestamp`, `duration`, `data`。`timestamp` 必须是“带时区”的时间；`duration` 为 `timedelta` 或秒数；`data` 为字典。
  - AwQL（查询）：服务器端查询语言，通过 `client.query()` 调用（进阶用法）。



## 快速上手（只读）

```python
from aw_client import ActivityWatchClient
from datetime import datetime, timedelta, timezone

client = ActivityWatchClient('analysis-doc')
client.wait_for_start(timeout=10)  # 等待服务就绪

# 1) 列出所有桶（只读）
buckets = client.get_buckets()
print(list(buckets.keys()))

# 2) 读取最近 24 小时的窗口事件（只读）
end = datetime.now(timezone.utc)
start = end - timedelta(days=1)
events = client.get_events('aw-watcher-window_dada-MacBook-Air', start=start, end=end)
print(len(events), events[:2])
```

## 事件读取时的字段获取

```python
e = events[0]
ts = e['timestamp']     # datetime（带 tz）
dur = e['duration']     # timedelta 或 0
app = e['data'].get('app')
title = e['data'].get('title')
```

---

## API 参考（只读/查询）

### 1) 服务与连接

- `wait_for_start(timeout: int = 10) -> None`

  - 轮询 `/info` 直到可达或超时；用于在脚本启动时确保服务可用。

  - 用例：

    ```python
    client = ActivityWatchClient('analysis-doc')
    client.wait_for_start(10)
    ```

- `get_info() -> dict`

  - 返回服务器信息（如 `hostname`, `testing`）。

  - 用例：

    ```python
    info = client.get_info()
    ```

- `connect()` / `disconnect()` / 上下文管理

  - 读操作不强制要求手动调用；推荐使用上下文管理器：

    ```python
    with ActivityWatchClient('analysis-doc') as c:
        print(c.get_info())
    ```

### 2) Bucket（桶）只读接口

- `get_buckets() -> dict`

  - 返回 `{bucket_id: meta}`，其中 `meta` 常含 `id, created, name, type, client, hostname, data, last_updated`。

  - 用例：

    ```python
    buckets = client.get_buckets()
    for bid, meta in buckets.items():
        print(bid, meta.get('type'), meta.get('client'))
    ```

- `export_bucket(bucket_id: str) -> dict` / `export_all() -> dict`

  - 以 JSON 兼容结构导出某个桶或全部桶（只读导出，不改变服务器数据）。

  - 用例：

    ```python
    raw = client.export_bucket('aw-watcher-vscode_dada-MacBook-Air')
    all_raw = client.export_all()
    ```

### 3) 事件只读接口

- `get_events(bucket_id: str, limit: int = -1, start: datetime|None = None, end: datetime|None = None) -> List[Event]`

  - 读取事件；建议总是提供 `start/end`，且必须为“带时区”的时间（UTC 推荐）。

  - 用例（过去 7 天窗口事件）：

    ```python
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    events = client.get_events('aw-watcher-window_dada-MacBook-Air', start=start, end=end)
    ```

- `get_event(bucket_id: str, event_id: int) -> Optional[Event]`

  - 按 ID 获取单个事件（只读）。

- `get_eventcount(bucket_id: str, limit: int = -1, start: datetime|None = None, end: datetime|None = None) -> int`

  - 返回时间范围内事件数量，常用于快速估算体量或分页策略。

### 4) 设置（只读）

- `get_setting(key: str|None = None) -> dict`
  - 不带 `key` 返回全部设置；带 `key` 返回单项设置。仅用于读取。

### 5) 查询（AwQL，进阶只读）

- `query(query: str, timeperiods: List[Tuple[datetime, datetime]], name: str|None = None, cache: bool = False) -> List[Any]`
  - 运行服务器端查询语句；`timeperiods` 为若干 `(start, end)`，必须带时区。
  - `cache=True` 时必须提供 `name` 以启用服务器缓存。
  - 适用场景：在服务端完成聚合/变换；但若统计逻辑个性化或复杂，直接 `get_events` 到本地做 Pandas/Numpy 处理更直观。

---

## 实用注意事项（只读场景）

- 始终使用带时区的时间：`datetime.now(timezone.utc)`；否则 `get_events` 会抛错或返回异常结果。
- 某些 watcher（如 VS Code）会产生 `duration=0` 的瞬时事件；做时长聚合时需过滤或与临近事件合并。
- 锁屏窗口（如 `loginwindow`、`登录`）会显著抬高“前台时间”；进行活跃度分析时应单独统计或剔除。
- 大量数据导出时优先使用 `export_bucket`/`export_all`，随后在本地进行离线统计，避免频繁远程调用。

---

## 完整示例（面向数据分析，读取/查询）

示例均为可直接运行的独立脚本片段，且只使用读取接口。

### 示例 1：近 14 天应用时长 Top10（排除锁屏）

```python
from collections import Counter
from datetime import datetime, timedelta, timezone
from aw_client import ActivityWatchClient

client = ActivityWatchClient('analysis-ex1')
client.wait_for_start(10)

end = datetime.now(timezone.utc)
start = end - timedelta(days=14)

bucket = 'aw-watcher-window_dada-MacBook-Air'
events = client.get_events(bucket, start=start, end=end)

app_time = Counter()
for e in events:
    dur = e['duration'].total_seconds() if e['duration'] else 0
    if dur <= 0:
        continue
    app = (e['data'] or {}).get('app', 'Unknown')
    if app in ('loginwindow', '登录'):
        continue
    app_time[app] += dur

top10 = app_time.most_common(10)
print('Top10 apps by hours (excluding lock screen):')
for app, sec in top10:
    print(f'  - {app}: {sec/3600:.2f}h')
```

### 示例 2：按日统计 Python 编码时长并导出 CSV

```python
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from aw_client import ActivityWatchClient

client = ActivityWatchClient('analysis-ex2')
client.wait_for_start(10)

end = datetime.now(timezone.utc)
start = end - timedelta(days=14)

bucket = 'aw-watcher-vscode_dada-MacBook-Air'
events = client.get_events(bucket, start=start, end=end)

tz = datetime.now().astimezone().tzinfo
daily = defaultdict(float)

for e in events:
    dur = e['duration'].total_seconds() if e['duration'] else 0
    lang = (e['data'] or {}).get('language')
    if dur <= 0 or lang != 'python':
        continue
    day = e['timestamp'].astimezone(tz).date().isoformat()
    daily[day] += dur

print('date,hours_python')
for day in sorted(daily.keys()):
    print(f'{day},{daily[day]/3600:.2f}')
```

### 示例 3：按 星期×小时 构建活跃热力图数据（JSON 输出）

```python
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from aw_client import ActivityWatchClient

client = ActivityWatchClient('analysis-ex3')
client.wait_for_start(10)

end = datetime.now(timezone.utc)
start = end - timedelta(days=14)

bucket = 'aw-watcher-window_dada-MacBook-Air'
events = client.get_events(bucket, start=start, end=end)

tz = datetime.now().astimezone().tzinfo
grid = defaultdict(float)  # key: (weekday, hour)

for e in events:
    dur = e['duration'].total_seconds() if e['duration'] else 0
    if dur <= 0:
        continue
    app = (e['data'] or {}).get('app', 'Unknown')
    if app in ('loginwindow', '登录'):
        continue
    ts = e['timestamp'].astimezone(tz)
    key = (ts.strftime('%A'), ts.hour)
    grid[key] += dur

# 组织为 {weekday: [24 小时数组(单位小时)]}
weekdays = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
heatmap = {w: [round(grid.get((w,h), 0.0)/3600, 2) for h in range(24)] for w in weekdays}
print(json.dumps(heatmap, ensure_ascii=False, indent=2))
```
"""粒子系统：固定步长、寿命、发射与排序。

修复要点（与 README 的 10 个问题一一对应）：

1. 积分只接受固定 dt（见 ``step_particle`` / ``fixed_step_update``），
   渲染帧率变化不改变轨迹；
2. 半隐式 Euler：先积分速度，再用新速度积分位置；
3. 寿命按秒递减（``age_lifetime``），与帧率无关；
4. 发射走时间累积器（``emit``），低帧补量、高帧缓存，不产生脉冲；
5. 单帧发射数量有硬上限，卡顿后不会一帧喷满；
6. 撞地按恢复系数反弹，而不是直接停住；
7. 透明粒子按相机距离从远到近排序，等距时按 id 升序保证稳定；
8. 粒子 id 去重（``dedupe_ids``），同一粒子不会被重复发射/绘制；
9. 世界空间发射器只对局部位置做一次平台变换（``apply_world_transform``）；
10. 异步排序结果应用前与当前帧粒子数量/范围校验
    （``validate_async_sort``），过期结果直接丢弃。
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, List, Sequence, Tuple

Vec3 = Tuple[float, float, float]

# 固定物理步长：60Hz。渲染帧率可以是 30Hz 或 120Hz，物理轨迹始终一致。
FIXED_DT = 1.0 / 60.0
# 单帧允许追赶的最大物理步数，防止长时间卡顿后“死亡螺旋”。
MAX_STEPS_PER_FRAME = 8


def step_particle(
    pos: Vec3,
    vel: Vec3,
    accel: Vec3,
    dt: float,
    floor_z: float,
    restitution: float,
) -> Tuple[Vec3, Vec3]:
    """固定步长积分并处理地面反弹。

    半隐式 Euler：先用加速度更新速度，再用 *更新后的* 速度推进位置，
    因此轨迹只取决于调用方传入的固定 ``dt``，与渲染帧率无关。
    位置越过地面（y 轴，参数沿用历史命名 ``floor_z``）时钳制到地面，
    法向速度按 ``-restitution`` 反弹；切向分量保持不变。
    """
    if dt == 0.0:
        return (float(pos[0]), float(pos[1]), float(pos[2])), (
            float(vel[0]),
            float(vel[1]),
            float(vel[2]),
        )

    # 1) 先积分速度
    new_vel = (
        vel[0] + accel[0] * dt,
        vel[1] + accel[1] * dt,
        vel[2] + accel[2] * dt,
    )
    # 2) 再用新速度积分位置
    new_pos = (
        pos[0] + new_vel[0] * dt,
        pos[1] + new_vel[1] * dt,
        pos[2] + new_vel[2] * dt,
    )

    # 3) 地面碰撞：钳制位置 + 恢复系数反弹（仅法向/y 分量）
    if new_pos[1] < floor_z:
        new_pos = (new_pos[0], float(floor_z), new_pos[2])
        new_vel = (new_vel[0], -restitution * new_vel[1], new_vel[2])

    return new_pos, new_vel


def fixed_step_update(
    particles: list,
    frame_dt: float,
    accumulator: float,
    step_fn: Callable,
    fixed_dt: float = FIXED_DT,
    max_steps: int = MAX_STEPS_PER_FRAME,
) -> Tuple[list, float]:
    """把可变帧时间拆成固定步长驱动粒子，返回更新后的粒子与余量。

    渲染侧无论 30Hz 还是 120Hz 都把帧时间倒进同一个累积器，物理只按
    ``fixed_dt`` 推进；``max_steps`` 限制单帧追赶步数，卡顿尖峰不会
    演变成无限补步。未消费的时间留给下一帧，不丢不补。
    """
    accumulator += frame_dt
    steps = 0
    while accumulator >= fixed_dt and steps < max_steps:
        particles = step_fn(particles, fixed_dt)
        accumulator -= fixed_dt
        steps += 1
    # 超过追赶上限的时间直接丢弃，避免下一帧继续雪崩。
    if steps == max_steps:
        accumulator = min(accumulator, fixed_dt)
    return particles, accumulator


def age_lifetime(remaining_life: float, dt: float) -> Tuple[float, bool]:
    """寿命按秒递减，返回 ``(剩余寿命, 是否存活)``。

    低帧率下每帧只扣掉真实流逝的秒数，粒子不会因为帧数少而提前死亡。
    """
    remaining = remaining_life - dt
    return remaining, remaining > 0.0


def emit(
    rate: float,
    dt: float,
    accumulator: float,
    max_per_frame: int,
) -> Tuple[int, float]:
    """按累积器返回本帧发射数量与余量。

    ``rate`` 是每秒发射数。本帧的可发射预算 = 历史余量 + ``rate*dt``，
    预算的整数部分即发射数，小数部分留到后续帧——帧率波动时发射速率
    保持恒定，不会一帧喷一堆、一帧不喷。发射数受 ``max_per_frame``
    硬截断，被截断的预算继续留在累积器里延后发射。
    """
    total = accumulator + rate * dt
    count = math.floor(total)
    if count > max_per_frame:
        count = max_per_frame
    remainder = total - count
    return count, remainder


def sort_particles(
    particles: Sequence[Tuple[int, float, float, float]],
    camera: Vec3,
) -> List[int]:
    """按相机距离从远到近返回粒子 id（透明物体 painter's algorithm）。

    每个粒子是 ``(id, x, y, z)``。使用距离平方排序，避免开方；距离
    相同（含对称的负坐标）时按 id 升序，保证绘制顺序确定、可复现。
    """
    cx, cy, cz = camera

    def key(particle):
        pid, x, y, z = particle
        dist_sq = (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2
        return (-dist_sq, pid)

    return [particle[0] for particle in sorted(particles, key=key)]


def dedupe_ids(ids: Iterable[int]) -> List[int]:
    """对粒子 id 去重，保留首次出现顺序。

    同一粒子在同一帧只会被发射/绘制一次，避免重复发射与重复计数。
    """
    seen = set()
    unique: List[int] = []
    for pid in ids:
        if pid not in seen:
            seen.add(pid)
            unique.append(pid)
    return unique


def apply_world_transform(
    local_pos: Vec3,
    platform_transform: Tuple[Vec3, Vec3, Vec3, Vec3],
) -> Vec3:
    """世界空间发射器：局部位置只做一次平台仿射变换。

    ``platform_transform`` 为 4x4 仿射矩阵的行主序前三行
    ``(row0, row1, row2)``，每行 ``(a, b, c, tx)``；点以齐次坐标
    ``(x, y, z, 1)`` 参与计算。发射器跟随平台时由调用方保证每帧只
    调用一次，平台矩阵更新不会被重复累加到粒子世界坐标上。
    """
    x, y, z = local_pos
    return (
        platform_transform[0][0] * x
        + platform_transform[0][1] * y
        + platform_transform[0][2] * z
        + platform_transform[0][3],
        platform_transform[1][0] * x
        + platform_transform[1][1] * y
        + platform_transform[1][2] * z
        + platform_transform[1][3],
        platform_transform[2][0] * x
        + platform_transform[2][1] * y
        + platform_transform[2][2] * z
        + platform_transform[2][3],
    )


def validate_async_sort(
    indices: Sequence[int],
    particle_count: int,
) -> List[int]:
    """校验异步排序结果是否仍匹配当前帧粒子集合。

    排序任务在另一线程完成时，本帧粒子可能已经消亡或新生，索引数量
    变化即说明结果过期；任何索引越界同样视为过期。过期结果返回空
    列表，由调用方回退到当前帧的默认绘制顺序，杜绝错序绘制。
    """
    if len(indices) != particle_count:
        return []
    if particle_count and max(indices) >= particle_count:
        return []
    if particle_count and min(indices) < 0:
        return []
    return list(indices)

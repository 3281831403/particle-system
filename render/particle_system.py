"""粒子系统：固定步长、寿命、发射与排序：待实现的核心模块。"""

from __future__ import annotations


def step_particle(pos, vel, accel, dt, floor_z, restitution):
    """固定步长积分并处理地面反弹。"""
    raise NotImplementedError

def emit(rate, dt, accumulator, max_per_frame):
    """按累积器返回本帧数量与余量。"""
    raise NotImplementedError

def sort_particles(particles, camera):
    """按相机距离从远到近返回 id。"""
    raise NotImplementedError

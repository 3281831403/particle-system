# 粒子系统：固定步长、寿命、发射与排序

粒子在可变帧率下飞散、寿命错位、发射脉冲、透明排序反转。本仓库固定积分与发射契约。

- 领域：游戏、图形与多媒体
- 子方向：图形渲染
- 语言/框架：Python 3, pytest
- 初始状态：15 个参数化用例全部失败

## 目录结构

```
README.md
conftest.py
.gitignore
render/__init__.py
render/particle_system.py
tests/test_particle_system.py
```

## 需要修复的 10 个问题

1. 粒子积分使用固定 dt，帧率变化不改变轨迹
2. 速度与加速度先积分速度再积分位置
3. 寿命按秒归一，低帧率下不提前死亡
4. 发射按累积器计算数量，不随帧率脉冲
5. 单帧发射数量有上限，避免卡顿尖峰
6. 粒子撞地按恢复系数反弹
7. 透明粒子按相机距离从远到近排序
8. 粒子 id 去重，不重复绘制
9. 世界空间发射器跟随平台时不重复变换
10. 异步排序结果与当前帧粒子数校验

## 15 条验收契约

    01. step gravity — `step_particle`
    02. step velocity — `step_particle`
    03. step bounce — `step_particle`
    04. step floor — `step_particle`
    05. step zero dt — `step_particle`
    06. emit exact — `emit`
    07. emit accumulate — `emit`
    08. emit cap — `emit`
    09. emit zero — `emit`
    10. emit remainder — `emit`
    11. sort two — `sort_particles`
    12. sort three — `sort_particles`
    13. sort tie — `sort_particles`
    14. sort empty — `sort_particles`
    15. sort negative — `sort_particles`

## 当前状态

`render/particle_system.py` 只保留函数签名与文档字符串，所有函数体统一
`raise NotImplementedError`。`tests/test_particle_system.py` 使用一个
`@pytest.mark.parametrize` 装载 15 条契约，初始全部失败且没有 collection error。

```bash
python -m pytest -q
```

预期输出包含 `15 failed`。实现 `render/particle_system.py` 后，15 条契约应全部通过。

import pytest

from render import particle_system as mod

CASES = [
    pytest.param('step_particle', ((0, 0, 0), (0, 0, 0), (0, -9.8, 0), 0.1, -10.0, 0.5), ((0.0, -0.09800000000000002, 0.0), (0.0, -0.9800000000000001, 0.0)), True, id='01_step_gravity'),
    pytest.param('step_particle', ((0, 0, 0), (1, 0, 0), (0, 0, 0), 0.5, -10.0, 0.5), ((0.5, 0.0, 0.0), (1.0, 0.0, 0.0)), True, id='02_step_velocity'),
    pytest.param('step_particle', ((0, 0.1, 0), (0, -1, 0), (0, -9.8, 0), 0.1, 0.0, 0.5), ((0.0, 0.0, 0.0), (0.0, 0.99, 0.0)), True, id='03_step_bounce'),
    pytest.param('step_particle', ((0, -0.5, 0), (0, 0, 0), (0, 0, 0), 0.1, 0.0, 0.5), ((0.0, 0.0, 0.0), (0.0, -0.0, 0.0)), True, id='04_step_floor'),
    pytest.param('step_particle', ((1, 2, 3), (4, 5, 6), (0, 0, 0), 0.0, 0.0, 0.5), ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)), True, id='05_step_zero_dt'),
    pytest.param('emit', (10.0, 0.1, 0.0, 10), (1, 0.0), True, id='06_emit_exact'),
    pytest.param('emit', (10.0, 0.05, 0.8, 10), (1, 0.30000000000000004), True, id='07_emit_accumulate'),
    pytest.param('emit', (100.0, 1.0, 0.0, 10), (10, 90.0), True, id='08_emit_cap'),
    pytest.param('emit', (10.0, 0.0, 0.0, 10), (0, 0.0), True, id='09_emit_zero'),
    pytest.param('emit', (3.0, 0.5, 0.25, 10), (1, 0.75), True, id='10_emit_remainder'),
    pytest.param('sort_particles', ([(1, 0, 0, 1), (2, 0, 0, 5)], (0, 0, 0)), [2, 1], False, id='11_sort_two'),
    pytest.param('sort_particles', ([(1, 0, 0, 1), (2, 0, 0, 5), (3, 0, 0, 3)], (0, 0, 0)), [2, 3, 1], False, id='12_sort_three'),
    pytest.param('sort_particles', ([(1, 0, 0, 1), (2, 0, 0, 1)], (0, 0, 0)), [1, 2], False, id='13_sort_tie'),
    pytest.param('sort_particles', ([], (0, 0, 0)), [], False, id='14_sort_empty'),
    pytest.param('sort_particles', ([(1, 0, 0, -2), (2, 0, 0, 2)], (0, 0, 0)), [1, 2], False, id='15_sort_negative'),
]


def assert_close(actual, expected):
    if isinstance(expected, tuple):
        assert isinstance(actual, tuple) and len(actual) == len(expected)
        for a, e in zip(actual, expected):
            assert_close(a, e)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for a, e in zip(actual, expected):
            assert_close(a, e)
    elif isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_close(actual[key], expected[key])
    else:
        assert actual == pytest.approx(expected)


@pytest.mark.parametrize("func_name,args,expected,approx", CASES)
def test_particle_system_contract(func_name, args, expected, approx):
    func = getattr(mod, func_name)
    result = func(*args)
    if approx:
        assert_close(result, expected)
    else:
        assert result == expected

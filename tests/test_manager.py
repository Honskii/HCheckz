from hcheckz import (
    readiness_point,
    set_ready,
    set_unready,
    del_readiness_point
)

from hcheckz.hcheckz import _Manager


def test_create_readiness_point():
    readiness_point("kafka")

    assert "kafka" in _Manager.get_readiness_points()

def test_delete_point():
    readiness_point("kafka")
    del_readiness_point("kafka")

    assert "kafka" not in _Manager.get_readiness_points()

    readiness_point("kafka")
    set_ready("kafka")
    del_readiness_point("kafka")

    assert "kafka" not in _Manager.get_readiness_points()

    readiness_point("kafka")
    set_unready("kafka", "TEST", "test")
    del_readiness_point("kafka")

    assert "kafka" not in _Manager.get_readiness_points()


def test_set_ready():
    readiness_point("redis")
    set_ready("redis")

    assert "redis" not in _Manager.get_unreadinesses()
    assert "redis" in _Manager.get_readiness_points()

    del_readiness_point("redis")


def test_set_unready():
    readiness_point("prometheus")
    set_ready("prometheus")
    set_unready("prometheus", "TEST", "test")

    assert "prometheus" in _Manager.get_readiness_points()
    assert "prometheus" in _Manager.get_unreadinesses()

    del_readiness_point("prometheus")


def test_exist_check():
    try:
        set_ready("loki")
    except KeyError:
        assert True
    else:
        assert False

    try:
        set_unready("loki", "TEST", "test")
    except KeyError:
        assert True
    else:
        assert False

    try:
        del_readiness_point("loki")
    except KeyError:
        assert True
    else:
        assert False


def test_type_errors():
    try:
        set_ready(123) # type: ignore
    except TypeError:
        assert True
    else:
        assert False

    try:
        set_unready(12, "TEST", "test") # type: ignore
    except TypeError:
        assert True
    else:
        assert False

    try:
        set_unready("loki", 665, "test") # type: ignore
    except TypeError:
        assert True
    else:
        assert False

    try:
        set_unready("loki", "TEST", 432) # type: ignore
    except TypeError:
        assert True
    else:
        assert False

    try:
        del_readiness_point(443) # type: ignore
    except TypeError:
        assert True
    else:
        assert False

    try:
        readiness_point(443) # type: ignore
    except TypeError:
        assert True
    else:
        assert False

def test_front():
    assert readiness_point == _Manager.readiness_point
    assert del_readiness_point == _Manager.delete_readiness_point
    assert set_unready == _Manager.set_unready
    assert set_ready == _Manager.set_ready

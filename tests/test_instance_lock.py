from wallpaper_studio.instance_lock import InstanceLock, InstanceLockError


def test_second_instance_is_rejected(studio_home):
    first = InstanceLock()
    first.acquire()
    second = InstanceLock()
    try:
        try:
            second.acquire()
            raise AssertionError("second instance should not start")
        except InstanceLockError as exc:
            assert "只能打开一次" in str(exc)
    finally:
        first.release()

    third = InstanceLock()
    third.acquire()
    third.release()

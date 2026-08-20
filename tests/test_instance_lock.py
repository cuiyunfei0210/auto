from wallpaper_studio.instance_lock import InstanceLock, InstanceLockError, already_running_message


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


def test_already_running_message_points_at_existing_ui():
    text = already_running_message("http://127.0.0.1:8765")
    assert "只能打开一次" in text
    assert "http://127.0.0.1:8765" in text

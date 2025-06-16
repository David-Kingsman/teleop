import unittest
import threading
import time
import socketio
import ssl
from teleop import Teleop


def get_message():
    return {
        "move": False,
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "orientation": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
        "reference_frame": "base",
    }


BASE_URL = "https://localhost:4443"


class TestPoseCompounding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__last_pose = None
        cls.__last_message = None
        cls.__callback_event = threading.Event()

        def callback(pose, message):
            cls.__last_pose = pose
            cls.__last_message = message
            cls.__callback_event.set()
            print(f"Callback triggered: pose={pose is not None}, message={message}")

        cls.teleop = Teleop(natural_phone_orientation_euler=[0, 0, 0])
        cls.teleop.subscribe(callback)
        cls.thread = threading.Thread(target=cls.teleop.run)
        cls.thread.daemon = True
        cls.thread.start()

        time.sleep(3)

        cls.sio = socketio.Client(ssl_verify=False, logger=False, engineio_logger=False)

        @cls.sio.event
        def connect():
            print("Connected to server")

        @cls.sio.event
        def disconnect():
            print("Disconnected from server")

        @cls.sio.event
        def connect_error(data):
            print(f"Connection error: {data}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                cls.sio.connect(
                    BASE_URL, transports=["polling"], wait_timeout=10, retry=True
                )
                break
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)

        time.sleep(2)

    def setUp(self):
        self.__class__.__last_pose = None
        self.__class__.__last_message = None
        self.__class__.__callback_event.clear()

    def _wait_for_callback(self, timeout=10.0):
        return self.__callback_event.wait(timeout=timeout)

    def test_response(self):
        if not self.sio.connected:
            self.skipTest("Socket.IO client not connected")

        payload = get_message()
        print(f"Sending payload: {payload}")

        self.sio.emit("pose", payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("Callback was not triggered within 10 seconds")

        self.assertIsNotNone(
            self.__last_message, "Message should not be None after callback"
        )

    def test_single_position_update(self):
        if not self.sio.connected:
            self.skipTest("Socket.IO client not connected")

        payload = get_message()
        print(f"Sending first payload: {payload}")

        payload["move"] = True
        self.sio.emit("pose", payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("First callback was not triggered within 10 seconds")

        self.assertIsNotNone(
            self.__last_pose,
            f"Pose should not be None after first emit. Last message: {self.__last_message}",
        )
        self.assertIsNotNone(
            self.__last_message, "Message should not be None after first emit"
        )

        self.__callback_event.clear()

        payload["move"] = True
        payload["position"]["y"] = 0.05
        print(f"Sending second payload: {payload}")
        self.sio.emit("pose", payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("Second callback was not triggered within 10 seconds")

        self.assertAlmostEqual(self.__last_pose[2, 3], 0.05, places=5)

        self.__callback_event.clear()

        payload["move"] = True
        payload["position"]["y"] = 0.1
        print(f"Sending third payload: {payload}")
        self.sio.emit("pose", payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("Third callback was not triggered within 10 seconds")

        self.assertAlmostEqual(self.__last_pose[2, 3], 0.1, places=5)

    @classmethod
    def tearDownClass(cls):
        try:
            if hasattr(cls, "sio") and cls.sio.connected:
                cls.sio.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {e}")


if __name__ == "__main__":
    unittest.main()

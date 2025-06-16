import unittest
import threading
import time
import socketio
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
    def __callback(cls, pose, message):
        cls.__last_pose = pose
        cls.__last_message = message
        print(pose)

    @classmethod
    def setUpClass(cls):
        cls.__last_pose = None
        cls.__last_message = None

        cls.teleop = Teleop(natural_phone_orientation_euler=[0, 0, 0])
        cls.teleop.subscribe(cls.__callback)
        cls.thread = threading.Thread(target=cls.teleop.run)
        cls.thread.daemon = True
        cls.thread.start()

        time.sleep(2)

        cls.sio = socketio.Client(ssl_verify=False)

        @cls.sio.event
        def connect():
            print("Connected to server")

        @cls.sio.event
        def disconnect():
            print("Disconnected from server")

        cls.sio.connect(BASE_URL)
        time.sleep(1)

    def test_response(self):
        payload = get_message()

        self.sio.emit("pose", payload)
        time.sleep(0.1)

        self.assertIsNotNone(self.__last_message)

    def test_single_position_update(self):
        payload = get_message()

        # The first message with `move==True` is used as a reference
        payload["move"] = True
        self.sio.emit("pose", payload)
        time.sleep(0.1)

        self.assertIsNotNone(self.__last_pose)
        self.assertIsNotNone(self.__last_message)

        # Move the phone up by 5cm (Y-axis)
        payload["move"] = True
        payload["position"]["y"] = 0.05
        self.sio.emit("pose", payload)
        time.sleep(0.1)

        # In total the result should be 5cm on the Z-axis because of the RUB -> FLU conversion
        self.assertEqual(self.__last_pose[2, 3], 0.05)

        # Move the phone up by another 5cm (Y-axis)
        payload["move"] = True
        payload["position"]["y"] = 0.1
        self.sio.emit("pose", payload)
        time.sleep(0.1)

        self.assertEqual(self.__last_pose[2, 3], 0.1)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "sio") and cls.sio.connected:
            cls.sio.disconnect()


if __name__ == "__main__":
    unittest.main()

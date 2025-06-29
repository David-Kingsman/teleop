import unittest
import threading
import time
import json
import ssl
import websocket
from teleop import Teleop


def get_message():
    return {
        "move": False,
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "orientation": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
        "reference_frame": "base",
    }


BASE_URL = "ws://localhost:4443/ws"


class TestPoseCompounding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__last_pose = None
        cls.__last_message = None
        cls.__callback_event = threading.Event()
        cls.__ws = None
        cls.__ws_connected = threading.Event()  # Use Event for connection tracking
        cls.__ws_error = None

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

        # WebSocket event handlers
        def on_message(ws, message):
            try:
                data = json.loads(message)
                print(f"Received from server: {data}")
            except json.JSONDecodeError:
                print(f"Received non-JSON message: {message}")

        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            cls.__ws_error = error
            cls.__ws_connected.clear()

        def on_close(ws, close_status_code, close_msg):
            print(f"WebSocket connection closed: {close_status_code} - {close_msg}")
            cls.__ws_connected.clear()

        def on_open(ws):
            print("WebSocket connection opened")
            cls.__ws_connected.set()  # Signal that connection is established

        # Create WebSocket connection
        websocket.enableTrace(True)  # Enable for debugging
        
        # Use wss:// for HTTPS or ws:// for HTTP
        url = BASE_URL.replace("ws://", "wss://") if "4443" in BASE_URL else BASE_URL
        
        cls.__ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        # Start WebSocket in separate thread
        cls.__ws_thread = threading.Thread(
            target=cls.__ws.run_forever,
            kwargs={
                'sslopt': {
                    "cert_reqs": ssl.CERT_NONE,
                    "check_hostname": False
                } if url.startswith("wss://") else None
            }
        )
        cls.__ws_thread.daemon = True
        cls.__ws_thread.start()

        # Wait for connection to be established
        connection_established = cls.__ws_connected.wait(timeout=10)
        if not connection_established:
            if cls.__ws_error:
                raise Exception(f"WebSocket connection failed: {cls.__ws_error}")
            else:
                raise Exception("WebSocket connection timeout")
        
        # Give a small buffer after connection
        time.sleep(0.5)

    def setUp(self):
        self.__class__.__last_pose = None
        self.__class__.__last_message = None
        self.__class__.__callback_event.clear()

    def _wait_for_callback(self, timeout=10.0):
        return self.__callback_event.wait(timeout=timeout)

    def _send_message(self, payload):
        """Send message to WebSocket server"""
        # Check if connection is still active
        if not self.__ws_connected.is_set():
            raise Exception("WebSocket connection not active")
            
        if not hasattr(self.__ws, 'sock') or self.__ws.sock is None:
            raise Exception("WebSocket socket is None")
            
        message = {
            "type": "pose",
            "data": payload
        }
        
        try:
            self.__ws.send(json.dumps(message))
        except Exception as e:
            # Connection might have been closed, try to reconnect
            self.__ws_connected.clear()
            raise Exception(f"Failed to send message: {e}")

    def test_response(self):
        if not self.__ws_connected.is_set():
            self.skipTest("WebSocket client not connected")

        payload = get_message()
        print(f"Sending payload: {payload}")

        self._send_message(payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("Callback was not triggered within 10 seconds")

        self.assertIsNotNone(
            self.__last_message, "Message should not be None after callback"
        )

    def test_single_position_update(self):
        if not self.__ws_connected.is_set():
            self.skipTest("WebSocket client not connected")

        payload = get_message()
        print(f"Sending first payload: {payload}")

        payload["move"] = True
        self._send_message(payload)

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
        self._send_message(payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("Second callback was not triggered within 10 seconds")

        self.assertAlmostEqual(self.__last_pose[2, 3], 0.05, places=5)

        self.__callback_event.clear()

        payload["move"] = True
        payload["position"]["y"] = 0.1
        print(f"Sending third payload: {payload}")
        self._send_message(payload)

        if not self._wait_for_callback(timeout=10.0):
            self.fail("Third callback was not triggered within 10 seconds")

        self.assertAlmostEqual(self.__last_pose[2, 3], 0.1, places=5)

    @classmethod
    def tearDownClass(cls):
        try:
            if hasattr(cls, '__ws') and cls.__ws:
                cls.__ws.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")


if __name__ == "__main__":
    unittest.main()

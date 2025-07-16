from typing import Any
from lerobot.teleoperators.teleoperator import Teleoperator
from .config import LeTeleopConfig
from teleop import Teleop
import numpy as np
import threading


class LeTeleop(Teleoperator):
    config_class = LeTeleopConfig
    name = "teleop"

    def __init__(self, config: LeTeleopConfig):
        super().__init__(config)
        self.config = config
        self._connected = False
        self._calibrated = True
        self._home = False

        self._server = Teleop(host=config.host, port=int(config.port))
        self._server.subscribe(self._on_teleop_callback)
        self._gripper_state = 0.0
        self._last_pose = np.eye(4)
        self._mutex = threading.Lock()

    def _on_teleop_callback(self, pose, message):
        with self._mutex:
            if message["move"]:
                self._last_pose = pose
            else:
                self._last_pose = None

            if message["gripper"] is not None:
                self._gripper_state = 2.0 if message["gripper"] == "open" else 0.0
            self._home = (
                message["reservedButtonA"] is not None and message["reservedButtonA"]
            )

    @property
    def action_features(self) -> dict[str, type]:
        if self.config.use_gripper:
            return {"pose_from_initial": np.ndarray, "gripper": float, "home": bool}
        else:
            return {
                "pose_from_initial": np.ndarray,
            }

    @property
    def feedback_features(self) -> dict[str, type]:
        return {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, calibrate: bool = True) -> None:
        self._connected = True
        threading.Thread(target=self._server.run, daemon=True).start()

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    def get_action(self) -> dict[str, Any]:
        last_pose = None
        with self._mutex:
            if self._last_pose is not None:
                last_pose = self._last_pose.copy()

        action = {}
        if last_pose is not None:
            action["pose_from_initial"] = last_pose
        if self.config.use_gripper:
            action["gripper"] = self._gripper_state
        if self._home:
            action["home"] = True
        return action

    def send_feedback(self, feedback: dict[str, float]) -> None:
        # TODO(rcadene, aliberts): Implement force feedback
        raise NotImplementedError

    def disconnect(self) -> None:
        self._connected = False
        self._server.stop()

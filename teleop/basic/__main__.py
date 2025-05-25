import numpy as np
import argparse
from teleop import Teleop


def main():
    parser = argparse.ArgumentParser(description="Teleop Example")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP address")
    parser.add_argument("--port", type=int, default=4443, help="Port number")
    args = parser.parse_args()

    def callback(pose, message):
        print(f"Pose: {pose}")
        print(f"Message: {message}")

    teleop = Teleop(host=args.host, port=args.port)
    teleop.set_pose(np.eye(4))
    teleop.subscribe(callback)
    teleop.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate Python code from proto files."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
PROTO_FILE = PROJECT_ROOT / "proto" / "image_processor.proto"
OUTPUT_DIR = PROJECT_ROOT


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{PROJECT_ROOT}",
        f"--python_out={OUTPUT_DIR}",
        f"--grpc_python_out={OUTPUT_DIR}",
        PROTO_FILE.relative_to(PROJECT_ROOT).as_posix(),
    ]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode == 0:
        print("Generated image_processor_pb2.py and image_processor_pb2_grpc.py")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

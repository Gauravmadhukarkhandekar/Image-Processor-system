"""
Example gRPC client for Image Processor service.
Reads image, sends operations (rotate 90, resize 800x600, grayscale), saves result.
"""

import argparse
import sys
from pathlib import Path

import grpc

# Add project root for proto imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proto.image_processor_pb2 import Operation, ProcessImageRequest
from proto.image_processor_pb2_grpc import ImageProcessorServiceStub


def process_image_file(
    image_path: str,
    output_path: str,
    host: str = "localhost",
    port: int = 50051,
    operations: list[Operation] | None = None,
    generate_thumbnail: bool = False,
    thumbnail_width: int = 128,
    thumbnail_height: int = 128,
) -> None:
    """
    Send image to server, apply operations, save result.

    Args:
        image_path: Path to input image
        output_path: Path to save processed image
        host: Server host
        port: Server port
        operations: List of operations (default: rotate 90, resize 800x600, grayscale)
        generate_thumbnail: Request thumbnail in response
        thumbnail_width: Thumbnail width when generate_thumbnail=True
        thumbnail_height: Thumbnail height when generate_thumbnail=True
    """
    if operations is None:
        operations = [
            Operation(type="rotate_right"),  # rotate 90 degrees
            Operation(type="resize", width=800, height=600),
            Operation(type="grayscale"),
        ]

    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path!r}. Use the path to an existing image (e.g. C:\\Users\\gaura\\Pictures\\photo.jpg).")
    image_data = path.read_bytes()

    request = ProcessImageRequest(
        image_data=image_data,
        operations=operations,
        generate_thumbnail=generate_thumbnail,
        thumbnail_width=thumbnail_width,
        thumbnail_height=thumbnail_height,
    )

    channel = grpc.insecure_channel(
        f"{host}:{port}",
        options=[
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),  # 50MB
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
        ],
    )
    stub = ImageProcessorServiceStub(channel)

    response = stub.ProcessImage(request)

    Path(output_path).write_bytes(response.processed_image)
    print(f"Processed image saved to {output_path}")

    if response.thumbnail_image and generate_thumbnail:
        thumb_path = Path(output_path).with_stem(
            Path(output_path).stem + "_thumb"
        ).with_suffix(Path(output_path).suffix)
        Path(thumb_path).write_bytes(response.thumbnail_image)
        print(f"Thumbnail saved to {thumb_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Image Processor gRPC client")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("-o", "--output", default="output.png", help="Output path")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=50051, help="Server port")
    parser.add_argument("--thumbnail", action="store_true", help="Request thumbnail")
    parser.add_argument("--thumb-width", type=int, default=128)
    parser.add_argument("--thumb-height", type=int, default=128)
    args = parser.parse_args()

    process_image_file(
        image_path=args.image,
        output_path=args.output,
        host=args.host,
        port=args.port,
        generate_thumbnail=args.thumbnail,
        thumbnail_width=args.thumb_width,
        thumbnail_height=args.thumb_height,
    )


if __name__ == "__main__":
    main()

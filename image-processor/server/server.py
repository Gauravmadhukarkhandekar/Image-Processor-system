"""
gRPC server for Image Processor - stateless, cloud-ready.
"""

import logging
from concurrent import futures
import sys
from pathlib import Path

import grpc

# Add project root for imports (run from image-processor/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from server.image_service import ImageProcessingError, process_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import generated modules (after proto generation; generated files live in proto/)
try:
    from proto.image_processor_pb2 import ProcessImageRequest, ProcessImageResponse
    from proto.image_processor_pb2_grpc import ImageProcessorServiceServicer, add_ImageProcessorServiceServicer_to_server
except ImportError:
    logger.warning("Proto modules not found. Run: python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/image_processor.proto")
    raise


class ImageProcessorServicer(ImageProcessorServiceServicer):
    """Stateless image processing service implementation."""

    def ProcessImage(self, request: ProcessImageRequest, context: grpc.ServicerContext) -> ProcessImageResponse:
        try:
            thumb_w = request.thumbnail_width if request.thumbnail_width > 0 else 256
            thumb_h = request.thumbnail_height if request.thumbnail_height > 0 else 256
            processed_bytes, thumbnail_bytes = process_image(
                image_data=request.image_data,
                operations=list(request.operations),
                generate_thumbnail=request.generate_thumbnail,
                thumbnail_width=thumb_w,
                thumbnail_height=thumb_h,
            )
            return ProcessImageResponse(
                processed_image=processed_bytes,
                thumbnail_image=thumbnail_bytes if thumbnail_bytes else b"",
            )
        except ImageProcessingError as e:
            logger.warning("Image processing error: %s", e)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ProcessImageResponse()
        except Exception as e:
            logger.exception("Unexpected error processing image")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ProcessImageResponse()


def serve(port: int = 50051) -> None:
    """Start the gRPC server."""
    max_msg = 50 * 1024 * 1024  # 50MB
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", max_msg),
            ("grpc.max_receive_message_length", max_msg),
        ],
    )
    add_ImageProcessorServiceServicer_to_server(ImageProcessorServicer(), server)
    # Bind localhost only; avoids Windows bind issues with 0.0.0.0 / [::]
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    logger.info("Image Processor server listening on port %d", port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

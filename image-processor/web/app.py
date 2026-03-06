"""
Web frontend backend: FastAPI app that bridges REST API to the gRPC Image Processor service.
"""

import base64
import sys
from pathlib import Path

import grpc
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

# Project root for proto imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from proto.image_processor_pb2 import Operation, ProcessImageRequest
from proto.image_processor_pb2_grpc import ImageProcessorServiceStub

from server.image_service import ImageProcessingError, process_image as process_image_in_process

app = FastAPI(title="Image Processor", version="1.0")

GRPC_HOST = "localhost"
GRPC_PORT = 50051
MAX_MB = 50 * 1024 * 1024


def get_grpc_stub():
    channel = grpc.insecure_channel(
        f"{GRPC_HOST}:{GRPC_PORT}",
        options=[
            ("grpc.max_receive_message_length", MAX_MB),
            ("grpc.max_send_message_length", MAX_MB),
        ],
    )
    return ImageProcessorServiceStub(channel)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the frontend."""
    html_path = Path(__file__).parent / "static" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    operations: str = Form("[]"),
    generate_thumbnail: str = Form("false"),
    thumbnail_width: int = Form(128),
    thumbnail_height: int = Form(128),
):
    """
    Accept image + operations (JSON), call gRPC service, return processed image and optional thumbnail as base64.
    """
    import json

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file (e.g. JPEG, PNG).")

    image_data = await file.read()
    if len(image_data) > MAX_MB:
        raise HTTPException(400, "Image too large (max 50MB).")

    try:
        ops_list = json.loads(operations)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid operations JSON: {e}")

    op_messages = []
    for op in ops_list:
        t = op.get("type", "").strip().lower()
        if not t:
            continue
        msg = Operation(type=t)
        if "angle" in op:
            msg.angle = int(op["angle"])
        if "width" in op:
            msg.width = int(op["width"])
        if "height" in op:
            msg.height = int(op["height"])
        op_messages.append(msg)

    request = ProcessImageRequest(
        image_data=image_data,
        operations=op_messages,
        generate_thumbnail=generate_thumbnail.lower() in ("true", "1", "yes"),
        thumbnail_width=max(1, thumbnail_width),
        thumbnail_height=max(1, thumbnail_height),
    )

    # Try gRPC first; on any failure, fall back to in-process (same Pillow logic)
    processed_bytes = None
    thumbnail_bytes = None
    try:
        stub = get_grpc_stub()
        response = stub.ProcessImage(request, timeout=60)
        processed_bytes = response.processed_image
        thumbnail_bytes = response.thumbnail_image or None
    except (grpc.RpcError, OSError, ConnectionError) as e:
        # Fall back to in-process processing (works even when gRPC server is down or errors)
        try:
            gen_thumb = generate_thumbnail.lower() in ("true", "1", "yes")
            thumb_w = max(1, thumbnail_width)
            thumb_h = max(1, thumbnail_height)
            ops_clean = [o for o in ops_list if o.get("type", "").strip()]
            processed_bytes, thumbnail_bytes = process_image_in_process(
                image_data, ops_clean, generate_thumbnail=gen_thumb, thumbnail_width=thumb_w, thumbnail_height=thumb_h
            )
        except ImageProcessingError as ie:
            raise HTTPException(400, str(ie))

    if processed_bytes is None:
        raise HTTPException(502, "Processing failed.")

    result = {
        "processed_image": base64.b64encode(processed_bytes).decode("ascii"),
        "thumbnail_image": base64.b64encode(thumbnail_bytes).decode("ascii") if thumbnail_bytes else None,
    }
    return result

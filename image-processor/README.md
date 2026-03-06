# Image Processor gRPC Service

A cloud-ready, stateless image processing RPC service built with Python 3.11, gRPC, and Pillow. Processes images entirely in memory—no disk storage.

## Features

- **Single API call**: Send image + operations, receive processed result
- **Stateless**: No filesystem writes, no state between requests
- **In-memory**: All processing via `io.BytesIO` and Pillow
- **Cloud deployable**: Designed for containerized/serverless deployment

## Supported Operations

| Operation           | Parameters   | Description                    |
|---------------------|-------------|--------------------------------|
| `flip_horizontal`   | —           | Mirror image horizontally      |
| `flip_vertical`     | —           | Flip image vertically          |
| `rotate_degrees`   | `angle`     | Rotate by angle (counter-clockwise) |
| `rotate_left`       | —           | Rotate 90° left                |
| `rotate_right`      | —           | Rotate 90° right               |
| `resize`            | `width`, `height` | Resize to dimensions      |
| `grayscale`         | —           | Convert to grayscale           |
| `generate_thumbnail`| `width`, `height` | Generate thumbnail (separate output) |

## Project Structure

```
image-processor/
├── proto/
│   └── image_processor.proto
├── server/
│   ├── server.py
│   └── image_service.py
├── client/
│   └── client.py
├── web/
│   ├── app.py           # FastAPI REST bridge to gRPC
│   └── static/
│       └── index.html   # Frontend UI
├── generate_proto.py
├── requirements.txt
└── README.md
```

## Setup

### 1. Create virtual environment (recommended)

```bash
cd image-processor
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate protobuf code

```bash
python generate_proto.py
```

This creates `image_processor_pb2.py` and `image_processor_pb2_grpc.py` in the project root.

## Running the Server

From the `image-processor` directory:

```bash
python -m server.server
```

Server listens on `localhost:50051` by default.

## Running the Client

Example: rotate 90°, resize to 800×600, convert to grayscale:

```bash
python -m client.client input.jpg -o output.png
```

With thumbnail:

```bash
python -m client.client input.jpg -o output.png --thumbnail --thumb-width 128 --thumb-height 128
```

Options:

- `image` — Input image path
- `-o, --output` — Output path (default: `output.png`)
- `--host` — Server host (default: `localhost`)
- `--port` — Server port (default: `50051`)
- `--thumbnail` — Request thumbnail in response
- `--thumb-width`, `--thumb-height` — Thumbnail dimensions

## Web Frontend

A browser UI is available that talks to the gRPC service via a REST API.

**1. Start the gRPC server** (in one terminal):

```bash
python -m server.server
```

**2. Start the web app** (in another terminal):

```bash
cd image-processor
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
```

**3. Open in browser:** [http://localhost:8000](http://localhost:8000)

Upload an image, choose operations (flip, rotate, resize, grayscale, thumbnail), then click **Process image**. Download the result from the page.

## API

### ProcessImage

**Request:**

- `image_data` (bytes): Raw image bytes
- `operations` (repeated Operation): Operations to apply in order
- `generate_thumbnail` (bool): Include thumbnail in response
- `thumbnail_width`, `thumbnail_height` (optional): Thumbnail size when `generate_thumbnail=true`

**Operation:**

- `type` (string): Operation name
- `angle` (int32): For `rotate_degrees`
- `width`, `height` (int32): For `resize`, `generate_thumbnail`

**Response:**

- `processed_image` (bytes): Processed image (PNG)
- `thumbnail_image` (bytes): Thumbnail when requested (PNG)

## Programmatic Usage

```python
import grpc
from image_processor_pb2 import Operation, ProcessImageRequest
from image_processor_pb2_grpc import ImageProcessorServiceStub

channel = grpc.insecure_channel("localhost:50051")
stub = ImageProcessorServiceStub(channel)

request = ProcessImageRequest(
    image_data=open("input.jpg", "rb").read(),
    operations=[
        Operation(type="rotate_right"),
        Operation(type="resize", width=800, height=600),
        Operation(type="grayscale"),
    ],
    generate_thumbnail=True,
    thumbnail_width=128,
    thumbnail_height=128,
)

response = stub.ProcessImage(request)
open("output.png", "wb").write(response.processed_image)
if response.thumbnail_image:
    open("thumb.png", "wb").write(response.thumbnail_image)
```

## Error Handling

- Invalid image data → `INVALID_ARGUMENT`
- Unknown/invalid operation → `INVALID_ARGUMENT`
- Server errors → `INTERNAL`

## Deployment

- **Docker**: Package the app and run the server in a container
- **Kubernetes**: Deploy as a stateless service
- **Cloud Run / Lambda**: Stateless design fits serverless

Max message size is 50MB; adjust via `grpc.max_message_length` if needed.

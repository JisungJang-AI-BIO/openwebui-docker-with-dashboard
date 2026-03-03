"""
title: Animated GIF Creator
author: Internal Team
author_url: https://github.com/anthropics/skills
description: Create animated GIFs optimized for Slack and messaging.
    Use when user requests GIF creation, animated images, emoji animations,
    or Slack-ready animated graphics.
required_open_webui_version: 0.8.5
requirements: Pillow, imageio, numpy
version: 1.0.0
licence: MIT
"""

import asyncio
import base64
import io
import math
import os
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


# =============================================================================
# EventEmitter Helper
# =============================================================================
class EventEmitter:
    def __init__(self, event_emitter: Callable[[dict], Any] = None, user: dict = None):
        self.event_emitter = event_emitter
        self.user = user or {}

    async def emit(self, description="Unknown State", status="in_progress", done=False):
        if self.event_emitter:
            await self.event_emitter(
                {"type": "status", "data": {"status": status, "description": description, "done": done}}
            )

    async def progress(self, description: str):
        await self.emit(description)

    async def success(self, description: str):
        await self.emit(description, "success", True)

    async def error(self, description: str):
        await self.emit(description, "error", True)

    async def send_file_link(self, file_path: str, filename: str, mime_type: str = None):
        """Upload file to OpenWebUI Files API and emit download link.
        Falls back to base64 data URI if the API is unavailable.
        """
        if not self.event_emitter or not os.path.exists(file_path):
            return
        if mime_type is None:
            ext = Path(filename).suffix.lower()
            mime_map = {
                ".gif": "image/gif", ".png": "image/png",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            }
            mime_type = mime_map.get(ext, "image/gif")

        is_image = mime_type.startswith("image/")
        url = await self._upload_to_openwebui(file_path, filename, mime_type)

        if url:
            if is_image:
                content = f"\n\n📎 **{filename}**\n\n![{filename}]({url})\n\n[Download {filename}]({url})\n"
            else:
                content = f"\n\n📎 **{filename}**\n\n[Download {filename}]({url})\n"
        else:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            data_uri = f"data:{mime_type};base64,{b64}"
            if is_image:
                content = f"\n\n📎 **{filename}**\n\n![{filename}]({data_uri})\n\n[Download {filename}]({data_uri})\n"
            else:
                content = f"\n\n📎 **{filename}**\n\n[Download {filename}]({data_uri})\n"

        await self.event_emitter({"type": "message", "data": {"content": content}})

    async def _upload_to_openwebui(self, file_path: str, filename: str, mime_type: str) -> Optional[str]:
        """Upload file via OpenWebUI's internal Files API. Returns download URL or None."""
        try:
            import httpx
            import jwt

            user_id = self.user.get("id", "")
            secret = os.environ.get("WEBUI_SECRET_KEY", "")
            if not user_id or not secret:
                return None

            token = jwt.encode({"id": user_id}, secret, algorithm="HS256")
            if isinstance(token, bytes):
                token = token.decode("utf-8")

            port = os.environ.get("PORT", "8080")
            with open(file_path, "rb") as f:
                resp = httpx.post(
                    f"http://localhost:{port}/api/v1/files/",
                    files={"file": (filename, f, mime_type)},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0,
                )

            if resp.status_code in (200, 201):
                file_id = resp.json().get("id")
                if file_id:
                    return f"/api/v1/files/{file_id}/content"
            return None
        except Exception:
            return None


# =============================================================================
# GIFBuilder
# =============================================================================
class GIFBuilder:
    """Helper class to build animated GIFs frame by frame using PIL."""

    def __init__(self, width: int, height: int, fps: int = 15):
        from PIL import Image
        self.width = width
        self.height = height
        self.fps = fps
        self.frames = []

    def blank_frame(self, bg_color=(255, 255, 255)):
        from PIL import Image
        return Image.new("RGBA", (self.width, self.height), bg_color)

    def add_frame(self, image):
        self.frames.append(image.copy())

    def save(self, path: str, num_colors: int = 64, optimize_for_emoji: bool = False, loop: int = 0):
        import imageio
        import numpy as np

        if not self.frames:
            raise ValueError("No frames added")

        duration_ms = 1000 / self.fps
        images_np = []
        for frame in self.frames:
            if frame.mode == "RGBA":
                bg = frame.copy()
                bg = bg.convert("RGB")
            else:
                bg = frame.convert("RGB")

            # Quantize colors
            quantized = bg.quantize(colors=num_colors, method=2)
            images_np.append(np.array(quantized.convert("RGB")))

        imageio.mimsave(path, images_np, duration=duration_ms / 1000, loop=loop)

        if optimize_for_emoji:
            file_size = os.path.getsize(path)
            if file_size > 256 * 1024:
                # Try reducing colors further
                for nc in [48, 32, 24, 16]:
                    images_np2 = []
                    for frame in self.frames:
                        bg = frame.convert("RGB")
                        q = bg.quantize(colors=nc, method=2)
                        images_np2.append(np.array(q.convert("RGB")))
                    imageio.mimsave(path, images_np2, duration=duration_ms / 1000, loop=loop)
                    if os.path.getsize(path) <= 256 * 1024:
                        break


# =============================================================================
# Easing Functions
# =============================================================================
def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2

def ease_in_cubic(t):
    return t * t * t

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_out_bounce(t):
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


# =============================================================================
# Main Tool Class
# =============================================================================
class Tools:
    class Valves(BaseModel):
        TEMP_DIR: str = Field(default="/tmp/openwebui-gif", description="Temporary file storage path")
        MAX_WIDTH: int = Field(default=512, description="Maximum GIF width in pixels")
        MAX_HEIGHT: int = Field(default=512, description="Maximum GIF height in pixels")
        MAX_FPS: int = Field(default=30, description="Maximum frames per second")
        MAX_FRAMES: int = Field(default=120, description="Maximum number of frames")

    def __init__(self):
        self.valves = self.Valves()
        self.citation = False

    async def create_gif(
        self,
        drawing_code: str,
        filename: str = "animation.gif",
        width: int = 480,
        height: int = 480,
        fps: int = 15,
        num_frames: int = 30,
        num_colors: int = 64,
        bg_color: str = "white",
        optimize_for_emoji: bool = False,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Create an animated GIF by executing Python drawing code for each frame.

        The drawing_code receives these variables:
        - `frame`: PIL Image object for the current frame
        - `draw`: PIL ImageDraw object
        - `t`: normalized time (0.0 to 1.0 across all frames)
        - `frame_num`: current frame number (0-indexed)
        - `total_frames`: total number of frames
        - `width`, `height`: GIF dimensions
        - `math`, `ease_*`: math module and easing functions

        Example drawing_code:
        ```
        cx, cy = width // 2, height // 2
        radius = int(50 + 30 * math.sin(t * 2 * math.pi))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill='red')
        ```

        Slack constraints:
        - Emoji: 128x128, <256KB, <3 seconds
        - Message: 480x480, <5MB
        - FPS: 10-30

        :param drawing_code: Python code using PIL ImageDraw to draw each frame
        :param filename: Output filename
        :param width: GIF width in pixels (max 512)
        :param height: GIF height in pixels (max 512)
        :param fps: Frames per second (10-30)
        :param num_frames: Total number of frames
        :param num_colors: Color palette size (16-128, fewer = smaller file)
        :param bg_color: Background color (e.g. "white", "#1a1a2e", "transparent")
        :param optimize_for_emoji: If true, aggressively optimize for <256KB
        :return: Status with preview and download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)
        await emitter.progress("Creating GIF...")

        # Clamp values
        width = min(width, self.valves.MAX_WIDTH)
        height = min(height, self.valves.MAX_HEIGHT)
        fps = min(max(fps, 1), self.valves.MAX_FPS)
        num_frames = min(max(num_frames, 2), self.valves.MAX_FRAMES)
        num_colors = min(max(num_colors, 8), 256)

        if optimize_for_emoji:
            width = min(width, 128)
            height = min(height, 128)

        try:
            from PIL import Image, ImageDraw, ImageFont

            builder = GIFBuilder(width, height, fps)

            # Parse background color
            if bg_color == "transparent":
                bg = (0, 0, 0, 0)
            elif bg_color.startswith("#"):
                hex_color = bg_color.lstrip("#")
                bg = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (255,)
            else:
                color_map = {"white": (255, 255, 255, 255), "black": (0, 0, 0, 255),
                             "red": (255, 0, 0, 255), "blue": (0, 0, 255, 255),
                             "green": (0, 128, 0, 255)}
                bg = color_map.get(bg_color.lower(), (255, 255, 255, 255))

            # Build frames
            for i in range(num_frames):
                await emitter.progress(f"Rendering frame {i+1}/{num_frames}...")
                frame = builder.blank_frame(bg)
                draw_obj = ImageDraw.Draw(frame)

                t = i / max(num_frames - 1, 1)

                # Execute user drawing code
                exec_globals = {
                    "frame": frame, "draw": draw_obj,
                    "t": t, "frame_num": i, "total_frames": num_frames,
                    "width": width, "height": height,
                    "math": math, "Image": Image, "ImageDraw": ImageDraw,
                    "ease_in_out_quad": ease_in_out_quad,
                    "ease_in_cubic": ease_in_cubic,
                    "ease_out_cubic": ease_out_cubic,
                    "ease_out_bounce": ease_out_bounce,
                    "ease_out_elastic": ease_out_elastic,
                }
                exec(drawing_code, exec_globals)

                builder.add_frame(frame)

            temp_dir = self._ensure_temp_dir()
            output_path = os.path.join(temp_dir, filename)

            await emitter.progress("Encoding GIF...")
            builder.save(output_path, num_colors=num_colors, optimize_for_emoji=optimize_for_emoji)

            file_size = os.path.getsize(output_path)
            duration_s = num_frames / fps

            await emitter.send_file_link(output_path, filename)
            await emitter.success(f"Created {filename}")

            slack_ready = "Yes" if (file_size < 5 * 1024 * 1024) else "No (>5MB)"
            emoji_ready = "Yes" if (file_size < 256 * 1024 and width <= 128 and height <= 128) else "No"

            return (
                f"Created '{filename}': {width}x{height}, {num_frames} frames, "
                f"{fps} FPS, {duration_s:.1f}s, {file_size:,} bytes.\n"
                f"Slack message ready: {slack_ready}\n"
                f"Slack emoji ready: {emoji_ready}"
            )

        except SyntaxError as e:
            await emitter.error(f"Code syntax error: {e}")
            return f"Error in drawing_code: {str(e)}"
        except Exception as e:
            await emitter.error(f"GIF creation error: {str(e)}")
            return f"Error: {str(e)}"

    async def create_simple_gif(
        self,
        animation_type: str = "pulse",
        text: str = "",
        color: str = "#FF6B6B",
        filename: str = "animation.gif",
        size: int = 128,
        __user__: dict = None,
        __event_emitter__: Callable[[dict], Any] = None,
    ) -> str:
        """
        Create a simple animated GIF from preset animation types.
        Good for quick Slack reactions and emoji.

        :param animation_type: "pulse", "bounce", "spin", "shake", "wave", "sparkle"
        :param text: Optional text/emoji to render (single character works best)
        :param color: Primary color (hex, e.g. "#FF6B6B")
        :param filename: Output filename
        :param size: GIF size in pixels (square)
        :return: Status with download link
        """
        emitter = EventEmitter(__event_emitter__, __user__)

        presets = {
            "pulse": (
                "r = int((width//4) * (0.7 + 0.3 * math.sin(t * 2 * math.pi)))\n"
                "cx, cy = width//2, height//2\n"
                f"draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill='{color}')\n"
            ),
            "bounce": (
                "cx = width // 2\n"
                "cy = int(height * 0.7 - height * 0.4 * abs(math.sin(t * math.pi)))\n"
                "r = width // 5\n"
                f"draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill='{color}')\n"
                f"shadow_w = int(r * (0.5 + 0.5 * abs(math.sin(t * math.pi))))\n"
                f"draw.ellipse([cx-shadow_w, int(height*0.85)-3, cx+shadow_w, int(height*0.85)+3], fill='#00000040')\n"
            ),
            "spin": (
                "import math as m\n"
                "cx, cy = width//2, height//2\n"
                "r = width // 3\n"
                "angle = t * 2 * m.pi\n"
                "pts = []\n"
                "for i in range(5):\n"
                "    a = angle + i * 2 * m.pi / 5\n"
                "    pts.append((cx + int(r * m.cos(a)), cy + int(r * m.sin(a))))\n"
                f"draw.polygon(pts, fill='{color}')\n"
            ),
            "shake": (
                "import random\n"
                "random.seed(frame_num)\n"
                "ox = random.randint(-5, 5) if frame_num % 2 == 0 else 0\n"
                "oy = random.randint(-3, 3) if frame_num % 2 == 0 else 0\n"
                "cx, cy = width//2 + ox, height//2 + oy\n"
                "r = width // 4\n"
                f"draw.rounded_rectangle([cx-r, cy-r, cx+r, cy+r], radius=r//4, fill='{color}')\n"
            ),
            "wave": (
                "for i in range(5):\n"
                "    x = int(width * (i + 0.5) / 5)\n"
                "    y = int(height // 2 + 15 * math.sin(t * 2 * math.pi + i * 0.8))\n"
                "    r = width // 12\n"
                f"    draw.ellipse([x-r, y-r, x+r, y+r], fill='{color}')\n"
            ),
            "sparkle": (
                "import random\n"
                "random.seed(42)\n"
                "positions = [(random.randint(10, width-10), random.randint(10, height-10)) for _ in range(8)]\n"
                "for idx, (sx, sy) in enumerate(positions):\n"
                "    phase = (t + idx * 0.125) % 1.0\n"
                "    size_val = int(8 * abs(math.sin(phase * math.pi)))\n"
                "    if size_val > 1:\n"
                f"        draw.line([(sx-size_val, sy), (sx+size_val, sy)], fill='{color}', width=2)\n"
                f"        draw.line([(sx, sy-size_val), (sx, sy+size_val)], fill='{color}', width=2)\n"
            ),
        }

        if animation_type not in presets:
            return f"Error: Unknown type '{animation_type}'. Available: {', '.join(presets.keys())}"

        code = presets[animation_type]

        return await self.create_gif(
            drawing_code=code,
            filename=filename,
            width=size,
            height=size,
            fps=15,
            num_frames=30,
            num_colors=48,
            bg_color="white",
            optimize_for_emoji=(size <= 128),
            __user__=__user__,
            __event_emitter__=__event_emitter__,
        )

    def _ensure_temp_dir(self) -> str:
        os.makedirs(self.valves.TEMP_DIR, exist_ok=True)
        return self.valves.TEMP_DIR

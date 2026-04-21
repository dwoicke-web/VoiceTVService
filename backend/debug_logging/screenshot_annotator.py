"""
Screenshot annotation utility: Draw bounding boxes and labels on screenshots.
"""

import base64
import io
from typing import Optional, List, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont


class BoundingBox:
    """Represents a bounding box with optional label and color."""

    def __init__(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        label: str = '',
        color: str = 'green',
        thickness: int = 3,
    ):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.label = label
        self.color = color
        self.thickness = thickness

    def to_dict(self) -> Dict[str, Any]:
        return {
            'x1': self.x1,
            'y1': self.y1,
            'x2': self.x2,
            'y2': self.y2,
            'label': self.label,
            'color': self.color,
        }


class ScreenshotAnnotator:
    """Annotates screenshots with bounding boxes and labels."""

    # Color palette for box drawing
    COLORS = {
        'green': (0, 255, 0),
        'red': (255, 0, 0),
        'blue': (0, 0, 255),
        'yellow': (255, 255, 0),
        'cyan': (0, 255, 255),
        'magenta': (255, 0, 255),
        'white': (255, 255, 255),
        'orange': (255, 165, 0),
    }

    @staticmethod
    def from_base64(base64_str: str) -> Image.Image:
        """Load image from base64 string."""
        try:
            image_bytes = base64.b64decode(base64_str)
            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise ValueError(f"Failed to decode base64 image: {e}")

    @staticmethod
    def to_base64(img: Image.Image, format: str = 'PNG') -> str:
        """Convert PIL image to base64 string."""
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    @staticmethod
    def annotate(
        image: Image.Image,
        boxes: List[BoundingBox],
        draw_labels: bool = True,
    ) -> Image.Image:
        """
        Draw bounding boxes on an image.

        Args:
            image: PIL Image object
            boxes: List of BoundingBox objects
            draw_labels: Whether to draw label text

        Returns:
            Annotated PIL Image object (original is not modified)
        """
        # Make a copy to avoid modifying the original
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)

        for box in boxes:
            # Get RGB tuple for the color
            color_rgb = ScreenshotAnnotator.COLORS.get(box.color, ScreenshotAnnotator.COLORS['green'])

            # Draw the rectangle
            draw.rectangle(
                [(box.x1, box.y1), (box.x2, box.y2)],
                outline=color_rgb,
                width=box.thickness,
            )

            # Draw label if provided
            if draw_labels and box.label:
                label_bg_color = color_rgb
                label_text_color = (0, 0, 0)  # Black text

                # Try to use a default font, fall back to default if not available
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                except Exception:
                    font = ImageFont.load_default()

                # Get text bounding box to size the background
                bbox = draw.textbbox((0, 0), box.label, font=font)
                text_width = bbox[2] - bbox[0] + 4
                text_height = bbox[3] - bbox[1] + 4

                # Draw label background
                label_x = box.x1
                label_y = max(0, box.y1 - text_height - 2)
                draw.rectangle(
                    [(label_x, label_y), (label_x + text_width, label_y + text_height)],
                    fill=label_bg_color,
                )

                # Draw label text
                draw.text(
                    (label_x + 2, label_y + 2),
                    box.label,
                    fill=label_text_color,
                    font=font,
                )

        return img_copy

    @staticmethod
    def annotate_from_base64(
        base64_str: str,
        boxes: List[BoundingBox],
        draw_labels: bool = True,
        output_format: str = 'PNG',
    ) -> str:
        """
        Annotate a base64-encoded image and return annotated image as base64.

        Args:
            base64_str: Input image as base64 string
            boxes: List of BoundingBox objects to draw
            draw_labels: Whether to draw label text
            output_format: Output image format (PNG, JPEG, etc.)

        Returns:
            Annotated image as base64 string
        """
        image = ScreenshotAnnotator.from_base64(base64_str)
        annotated = ScreenshotAnnotator.annotate(image, boxes, draw_labels)
        return ScreenshotAnnotator.to_base64(annotated, format=output_format)

    @staticmethod
    def annotate_file(
        input_path: str,
        output_path: str,
        boxes: List[BoundingBox],
        draw_labels: bool = True,
    ) -> None:
        """
        Annotate an image file and save to disk.

        Args:
            input_path: Path to input image
            output_path: Path to save annotated image
            boxes: List of BoundingBox objects to draw
            draw_labels: Whether to draw label text
        """
        image = Image.open(input_path)
        annotated = ScreenshotAnnotator.annotate(image, boxes, draw_labels)
        annotated.save(output_path)

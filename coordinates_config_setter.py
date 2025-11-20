import cv2
import json
import argparse
from pathlib import Path


class CoordinateSelector:
    def __init__(self, image_path, output_file="coordinates_output.json"):
        self.image_path = image_path
        self.output_file = output_file
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"Could not load image: {image_path}")

        self.original_image = self.image.copy()
        self.rectangles = []
        self.current_rect = None
        self.drawing = False
        self.start_point = None

        # Window name
        self.window_name = "Coordinate Selector - Draw rectangles, Press 'u' to undo, 'r' to reset, 'q' to quit"

        # Load existing coordinates if file exists
        self.load_coordinates()

    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for drawing rectangles"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # Start drawing
            self.drawing = True
            self.start_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                # Update current rectangle while drawing
                self.image = self.original_image.copy()

                # Draw all saved rectangles
                for i, coord in enumerate(self.rectangles):
                    cv2.rectangle(
                        self.image,
                        (coord["x"], coord["y"]),
                        (coord["x"] + coord["width"], coord["y"] + coord["height"]),
                        (0, 255, 0),
                        2,
                    )
                    # Add index label
                    cv2.putText(
                        self.image,
                        f"#{i + 1}",
                        (coord["x"], coord["y"] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                    )

                # Draw current rectangle being drawn
                cv2.rectangle(self.image, self.start_point, (x, y), (0, 0, 255), 2)

        elif event == cv2.EVENT_LBUTTONUP:
            if self.drawing:
                # Finish drawing
                self.drawing = False
                end_point = (x, y)

                # Calculate rectangle coordinates
                x1 = min(self.start_point[0], end_point[0])
                y1 = min(self.start_point[1], end_point[1])
                x2 = max(self.start_point[0], end_point[0])
                y2 = max(self.start_point[1], end_point[1])

                width = x2 - x1
                height = y2 - y1

                # Only add if rectangle has area
                if width > 5 and height > 5:
                    rect_data = {"x": x1, "y": y1, "width": width, "height": height}
                    self.rectangles.append(rect_data)
                    print(
                        f"✅ Rectangle #{len(self.rectangles)} added: ({x1}, {y1}) - {width}x{height}px"
                    )

                    # Auto-save after each rectangle
                    self.save_coordinates()

                # Redraw everything
                self.redraw()

    def redraw(self):
        """Redraw the image with all rectangles"""
        self.image = self.original_image.copy()

        for i, coord in enumerate(self.rectangles):
            cv2.rectangle(
                self.image,
                (coord["x"], coord["y"]),
                (coord["x"] + coord["width"], coord["y"] + coord["height"]),
                (0, 255, 0),
                2,
            )
            # Add index label
            cv2.putText(
                self.image,
                f"#{i + 1}",
                (coord["x"], coord["y"] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

    def load_coordinates(self):
        """Load existing coordinates from JSON file if it exists"""
        if Path(self.output_file).exists():
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    self.rectangles = json.load(f)
                print(
                    f"📂 Loaded {len(self.rectangles)} existing rectangles from {self.output_file}"
                )
                self.redraw()
            except Exception as e:
                print(f"⚠️  Could not load existing coordinates: {e}")

    def save_coordinates(self):
        """Save coordinates to JSON file"""
        if not self.rectangles:
            return False

        try:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(self.rectangles, f, indent=2, ensure_ascii=False)

            print(f"💾 Saved {len(self.rectangles)} rectangles to: {self.output_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving coordinates: {e}")
            return False

    def reset(self):
        """Clear all rectangles"""
        self.rectangles = []
        self.save_coordinates()
        self.redraw()
        print("\n🔄 Reset - all rectangles cleared")

    def undo(self):
        """Remove last rectangle"""
        if self.rectangles:
            self.rectangles.pop()
            self.save_coordinates()
            self.redraw()
            print(f"\n↩️  Undone - Rectangle #{len(self.rectangles) + 1} removed")
        else:
            print("\n⚠️  Nothing to undo")

    def generate_masked_image(self, output_path="coordinates_output.png"):
        """Generate a masked image with black rectangles and save it"""
        if not self.rectangles:
            print("⚠️  No rectangles to mask!")
            return False

        try:
            # Create a copy of the original image
            masked_image = self.original_image.copy()

            # Apply black rectangles to all coordinates
            for coord in self.rectangles:
                cv2.rectangle(
                    masked_image,
                    (coord["x"], coord["y"]),
                    (coord["x"] + coord["width"], coord["y"] + coord["height"]),
                    (0, 0, 0),  # Black color
                    -1,
                )  # Filled rectangle

            # Save the masked image
            cv2.imwrite(output_path, masked_image)
            print(f"\n✅ Masked image saved to: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Error generating masked image: {e}")
            return False

    def run(self):
        """Main loop for the coordinate selector"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        # Get image dimensions
        height, width = self.image.shape[:2]
        print(f"\n🖼️  Image loaded: {self.image_path}")
        print(f"   Dimensions: {width}x{height}px")
        print("\n" + "=" * 70)
        print("INSTRUCTIONS:")
        print("=" * 70)
        print("  • Click and drag to draw rectangles")
        print("  • Coordinates are auto-saved to coordinates_output.json")
        print("  • Press 'u' to undo last rectangle")
        print("  • Press 'r' to reset (clear all rectangles)")
        print("  • Press 'q' to quit and generate masked image")
        print("=" * 70 + "\n")

        while True:
            cv2.imshow(self.window_name, self.image)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                # Generate masked image before quitting
                self.generate_masked_image()
                print("\n👋 Quit - masked image generated as coordinates_output.png")
                break
            elif key == ord("r"):
                # Reset
                self.reset()
            elif key == ord("u"):
                # Undo
                self.undo()

        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="Interactive coordinate selector for sensitive data masking"
    )
    parser.add_argument("-i", "--image", required=True, help="Path to the image file")
    parser.add_argument(
        "-o",
        "--output",
        default="coordinates_output.json",
        help="Output JSON file path (default: coordinates_output.json)",
    )

    args = parser.parse_args()

    try:
        selector = CoordinateSelector(args.image, args.output)
        selector.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

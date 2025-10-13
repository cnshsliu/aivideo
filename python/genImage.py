from moviepy.editor import ImageClip, CompositeVideoClip, ColorClip
import numpy as np
import cv2

# Set dimensions for 9:16 aspect ratio (e.g., 1080x1920 for vertical Full HD)
width, height = 1080, 1920


# Create a linear gradient background (deep black to dark purple)
def create_gradient(height, width, start_color, end_color):
    gradient = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        t = y / height
        color = [int(start_color[i] * (1 - t) + end_color[i] * t) for i in range(3)]
        gradient[y, :] = color
    return gradient


# Colors in RGB (cyberpunk palette)
black = [0, 0, 0]
dark_purple = [50, 0, 100]
neon_blue = [0, 255, 255]
neon_pink = [255, 20, 147]
metallic_silver = [192, 192, 192]

# Create base gradient background
gradient_bg = create_gradient(height, width, black, dark_purple)


# Add glowing neon lines (horizontal and diagonal for dynamic effect)
def add_neon_lines(image, num_lines=5, color=neon_blue, thickness=2):
    img = image.copy()
    for _ in range(num_lines):
        # Random horizontal line
        y = np.random.randint(0, height)
        cv2.line(img, (0, y), (width, y), color, thickness)
        # Random diagonal line
        x1, y1 = np.random.randint(0, width // 4), np.random.randint(0, height // 4)
        x2, y2 = (
            np.random.randint(3 * width // 4, width),
            np.random.randint(3 * height // 4, height),
        )
        cv2.line(img, (x1, y1), (x2, y2), color, thickness)
    # Apply slight blur for glowing effect
    img = cv2.GaussianBlur(img, (15, 15), 0)
    return img


# Add neon lines to the gradient background
image_with_lines = add_neon_lines(
    gradient_bg, num_lines=8, color=neon_blue, thickness=2
)
image_with_lines = add_neon_lines(
    image_with_lines, num_lines=5, color=neon_pink, thickness=2
)


# Add subtle geometric shapes (e.g., faint triangles)
def add_geometric_shapes(image, num_shapes=10, color=metallic_silver, alpha=0.3):
    img = image.copy()
    overlay = img.copy()
    for _ in range(num_shapes):
        # Random triangle vertices
        pts = np.array(
            [
                [np.random.randint(0, width), np.random.randint(0, height)],
                [np.random.randint(0, width), np.random.randint(0, height)],
                [np.random.randint(0, width), np.random.randint(0, height)],
            ]
        )
        cv2.fillPoly(overlay, [pts], color)
    # Blend overlay with original image for transparency
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    return img


# Add geometric shapes
final_image = add_geometric_shapes(
    image_with_lines, num_shapes=10, color=metallic_silver
)

# Convert the image to a MoviePy ImageClip
image_clip = ImageClip(final_image, duration=1)

# Create a black background clip to ensure 9:16 aspect ratio
background = ColorClip(size=(width, height), color=(0, 0, 0), duration=1)

# Composite the image on the background
final_clip = CompositeVideoClip([background, image_clip.set_position("center")])

# Save the image as a PNG (single frame)
final_clip.save_frame("futuristic_background.png", t=0)

print("Image saved as 'futuristic_background.png'")

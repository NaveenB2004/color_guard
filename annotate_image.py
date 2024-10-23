import json
import os
import sys
import tempfile

import cv2
from colorthief import ColorThief


# Convert RGB tuple to hexadecimal color
def rgb_to_hex(color):
    return "#{:02x}{:02x}{:02x}".format(color[0], color[1], color[2])


# Check if color is close to white
def is_near_white(color, threshold=240):
    return all(c >= threshold for c in color)


def find_primary_and_secondary_colors(image_path):
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return None, None

    ct = ColorThief(image_path)

    # Get a larger palette of colors (12 colors)
    palette = ct.get_palette(color_count=12, quality=1)

    # Sort colors by their perceived brightness to avoid inversion issues
    palette.sort(key=lambda c: sum(c) / 3)  # Sort by average RGB value (brightness)

    # Filter out colors that are too dark
    filtered_palette = [color for color in palette if sum(color) / 3 > 30]  # Ignore very dark colors

    # Check for white or near-white primary color
    primary_color = None
    secondary_color = None

    for color in filtered_palette:
        if is_near_white(color):
            primary_color = (255, 255, 255)  # Force white if it's near-white
            break
    else:
        # Choose the brightest color if no white is found
        primary_color = filtered_palette[-1]

    # Assign secondary color (next color in palette)
    if len(filtered_palette) > 1:
        secondary_color = filtered_palette[-1] if primary_color != filtered_palette[-1] else filtered_palette[-2]

    return primary_color, secondary_color


# Function to get dominant color of a cropped element
def dominant_color_of_element(cropped_image):
    if cropped_image is None or cropped_image.size == 0:
        print("Empty or invalid cropped image, skipping color extraction.")
        return None

    # Convert image to RGB format (from BGR, which is OpenCV's default)
    rgb_cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)

    # Write the RGB image to a temporary file and extract the dominant color using ColorThief
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        temp_filename = temp_file.name
        cv2.imwrite(temp_filename, rgb_cropped_image)

    try:
        # Extract the dominant color
        ct = ColorThief(temp_filename)
        element_color = ct.get_color(quality=1)
        return element_color
    except Exception as e:
        print(f"Error extracting color: {e}")
        return None
    finally:
        # Make sure to clean up the temp file
        try:
            os.remove(temp_filename)
        except Exception as cleanup_error:
            print(f"Error cleaning up temp file: {cleanup_error}")


# Function to classify the UI element based on its bounding box and size
def classify_element(contour, image_shape):
    x, y, w, h = cv2.boundingRect(contour)
    aspect_ratio = w / float(h)
    area = cv2.contourArea(contour)
    image_height, image_width, _ = image_shape

    if y < 0.1 * image_height and w > 0.9 * image_width:
        return "Top App Bar"
    elif y > 0.85 * image_height and w > 0.9 * image_width:
        return "Bottom App Bar"
    elif 1.2 > aspect_ratio > 0.8 and 1000 < area < 8000:
        return "Button"
    elif aspect_ratio > 2.5 and area > 800:
        return "Label"
    else:
        return "Unknown"


# Function to detect, annotate, and crop clickable elements
def detect_clickable_elements(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Image not found or unable to load: {image_path}")

    # Convert to grayscale and apply blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

    # Apply morphological operations to merge close contours
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Find contours from the morphed image
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Annotated image copy
    annotated_image = image.copy()

    # List to store dominant color and cropped images of each detected element
    element_data = []

    # Annotate detected contours and extract dominant color
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)

        if area > 500:  # Only process elements larger than 500px area
            element_type = classify_element(contour, annotated_image.shape)

            # Draw bounding box on the annotated image
            cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(annotated_image, element_type, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

            # Extract the cropped image for this element
            cropped_image = image[y:y + h, x:x + w]  # Crop from the original image
            element_color = dominant_color_of_element(cropped_image)

            # Save the data if the color extraction was successful
            if element_color is not None:
                color_hex = rgb_to_hex(element_color)
                element_data.append({
                    "type": element_type,
                    "color": color_hex,
                    "coords": (x, y, w, h)
                })
            else:
                element_data.append({
                    "type": element_type,
                    "color": "N/A",
                    "coords": (x, y, w, h)
                })

            # Save the cropped image
            cropped_path = os.path.join("uploads", f"cropped_element_{len(element_data)}.jpg")
            cv2.imwrite(cropped_path, cropped_image)

    # Save the annotated image
    annotated_image_path = os.path.join("uploads", "annotated_image.jpg")
    cv2.imwrite(annotated_image_path, annotated_image)

    # Save element metadata to a JSON file
    with open(os.path.join("uploads", "element_data.json"), "w") as json_file:
        json.dump(element_data, json_file)

    return annotated_image, element_data


def main():
    # Get the image path from the command line argument
    image_path = sys.argv[1]

    # Call the function to get primary and secondary colors
    primary_color, secondary_color = find_primary_and_secondary_colors(image_path)

    # Print the primary and secondary colors to be captured by the PHP script
    primary_color_hex = rgb_to_hex(primary_color) if primary_color else "N/A"
    secondary_color_hex = rgb_to_hex(secondary_color) if secondary_color else "N/A"

    print(primary_color_hex)
    print(secondary_color_hex)

    # Annotate elements and get the dominant color of each element
    detect_clickable_elements(image_path)


if __name__ == "__main__":
    main()

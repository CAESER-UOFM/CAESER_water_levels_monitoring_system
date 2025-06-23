import tkinter as tk
from tkinter import filedialog
from PIL import Image
import os

def convert_png_to_webp():
    # Create a root window but keep it hidden
    root = tk.Tk()
    root.withdraw()
    
    # Open file dialog to select a PNG file
    file_path = filedialog.askopenfilename(
        title="Select PNG Image",
        filetypes=[("PNG files", "*.png")]
    )
    
    if not file_path:
        print("No file selected. Exiting.")
        return
    
    try:
        # Open the image
        image = Image.open(file_path)
        
        # Get the directory and filename without extension
        directory = os.path.dirname(file_path)
        filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Create output path with .webp extension
        output_path = os.path.join(directory, f"{filename}.webp")
        
        # Convert and save as WebP
        # You can adjust the quality parameter (0-100) as needed
        image.save(output_path, format="WEBP", quality=80)
        
        print(f"Successfully converted {file_path} to WebP!")
        print(f"Saved as: {output_path}")
        
    except Exception as e:
        print(f"Error converting image: {e}")
    
    finally:
        # Clean up the tkinter instance
        root.destroy()

if __name__ == "__main__":
    # Check if PIL/Pillow is installed
    try:
        import PIL
        print(f"Using PIL/Pillow version: {PIL.__version__}")
        convert_png_to_webp()
    except ImportError:
        print("Error: PIL/Pillow is not installed.")
        print("Please install it using: pip install Pillow")
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import os

def convert_webp_to_png():
    # Create a root window but keep it hidden
    root = tk.Tk()
    root.withdraw()
    
    # Open file dialog to select a WebP file
    file_path = filedialog.askopenfilename(
        title="Select WebP Image",
        filetypes=[("WebP files", "*.webp"), ("All image files", "*.webp;*.jpg;*.jpeg")]
    )
    
    if not file_path:
        print("No file selected. Exiting.")
        return
    
    try:
        # Open the WebP image
        image = Image.open(file_path)
        
        # Get the directory and filename without extension
        directory = os.path.dirname(file_path)
        filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Create output path with .png extension
        output_path = os.path.join(directory, f"{filename}.png")
        
        # Convert to RGBA to ensure transparency is preserved
        if image.mode != 'RGBA' and 'transparency' in image.info:
            image = image.convert('RGBA')
            
        # Save with maximum quality
        image.save(output_path, format="PNG")
        
        print(f"Successfully converted {file_path} to PNG!")
        print(f"Saved as: {output_path}")
        print(f"Image dimensions: {image.width}x{image.height}")
        
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
        convert_webp_to_png()
    except ImportError:
        print("Error: PIL/Pillow is not installed.")
        print("Please install it using: pip install Pillow")
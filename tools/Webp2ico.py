import tkinter as tk
from tkinter import filedialog
from PIL import Image
import os

def convert_webp_to_ico():
    # Create a root window but keep it hidden
    root = tk.Tk()
    root.withdraw()
    
    # Open file dialog to select a WebP file
    file_path = filedialog.askopenfilename(
        title="Select WebP Image",
        filetypes=[("WebP files", "*.webp")]
    )
    
    if not file_path:
        print("No file selected. Exiting.")
        return
    
    try:
        # Open the WebP image
        image = Image.open(file_path)
        
        # ICO files work best with specific sizes
        # Including both standard and larger sizes for modern displays
        # You can customize this list based on your needs
        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Create resized versions for the ICO file
        icon_images = []
        for size in sizes:
            # Create a resized copy of the image with correct aspect ratio
            resized_img = image.copy()
            resized_img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # If the image has transparency (RGBA), preserve it
            # Otherwise, convert to RGBA to ensure compatibility with ICO format
            if resized_img.mode != 'RGBA':
                resized_img = resized_img.convert('RGBA')
            
            icon_images.append(resized_img)
        
        # Get the directory and filename without extension
        directory = os.path.dirname(file_path)
        filename = os.path.splitext(os.path.basename(file_path))[0]
        
        # Create output path with .ico extension
        output_path = os.path.join(directory, f"{filename}.ico")
        
        # Save as ICO with all sizes
        icon_images[0].save(
            output_path,
            format="ICO",
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        print(f"Successfully converted {file_path} to ICO!")
        print(f"Saved as: {output_path}")
        print(f"The ICO file contains the following sizes: {sizes}")
        
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
        convert_webp_to_ico()
    except ImportError:
        print("Error: PIL/Pillow is not installed.")
        print("Please install it using: pip install Pillow")
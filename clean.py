import os
import sys

def remove_png_files(target_path):
    # Check if the provided path is valid
    if not os.path.exists(target_path):
        print(f"Error: The path '{target_path}' does not exist.")
        return
    
    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.png'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Removed: {file_path}")
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")

if __name__ == "__main__":
    # Check if the user provided a path argument
    if len(sys.argv) != 2:
        print("Usage: python remove_png_files.py <target_path>")
    else:
        target_path = sys.argv[1]
        remove_png_files(target_path)

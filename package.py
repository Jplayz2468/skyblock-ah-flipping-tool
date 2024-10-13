import PyInstaller.__main__
import os

# Get the current directory
current_dir = os.getcwd()

# Path to your main.py file
main_script = os.path.join(current_dir, 'main.py')

# Run PyInstaller
PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--clean',
    '--name=AhFlippingApp'
])

print("Executable created successfully.")
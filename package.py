import os
import base64
import PyInstaller.__main__

# First, create and build the main program
main_program = """
import tkinter as tk
from tkinter import ttk

class AhFlippingTool:
    def __init__(self, root):
        self.root = root
        root.title("AhFlipping Tool")
        root.geometry("800x600")
        
        # Create main frame
        self.frame = ttk.Frame(root, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add title
        ttk.Label(self.frame, text="AhFlipping Tool", font=('Arial', 24)).grid(row=0, column=0, pady=20)
        
        # Add content here
        ttk.Label(self.frame, text="Your flipping tool content goes here").grid(row=1, column=0, pady=20)

def main():
    root = tk.Tk()
    app = AhFlippingTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
"""

# Create the installer script
installer_code = """
import os
import sys
import base64
import ctypes
from tkinter import Tk, Label, Button, messagebox

# The main program will be embedded here
EMBEDDED_EXE = '{}'

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

def install():
    try:
        if not is_admin():
            run_as_admin()
            return

        # Create program directory
        install_dir = os.path.join(os.getenv('PROGRAMFILES'), 'AhFlippingTool')
        os.makedirs(install_dir, exist_ok=True)
        
        # Extract and save the program
        exe_path = os.path.join(install_dir, 'AhFlippingTool.exe')
        with open(exe_path, 'wb') as f:
            f.write(base64.b64decode(EMBEDDED_EXE))

        # Create shortcut in Start Menu
        start_menu_path = os.path.join(
            os.getenv('PROGRAMDATA'),
            'Microsoft\\Windows\\Start Menu\\Programs',
            'AhFlippingTool.lnk'
        )
        with open(start_menu_path, 'w') as f:
            f.write(exe_path)

        messagebox.showinfo('Success', 'AhFlippingTool has been installed successfully!')
        
    except Exception as e:
        messagebox.showerror('Error', f'Installation failed: {{str(e)}}')

if __name__ == '__main__':
    root = Tk()
    root.title('AhFlippingTool Installer')
    root.geometry('300x150')
    
    Label(root, text='AhFlippingTool Installer').pack(pady=20)
    Button(root, text='Install', command=lambda: [install(), root.destroy()]).pack()
    Button(root, text='Cancel', command=root.destroy).pack(pady=10)
    
    root.mainloop()
"""

def build_program_and_installer():
    # First, create and build the main program
    print("Building main program...")
    with open('ahflipping.py', 'w') as f:
        f.write(main_program)
    
    PyInstaller.__main__.run([
        'ahflipping.py',
        '--onefile',
        '--noconsole',
        '--clean',
        '--name=AhFlippingTool'
    ])
    
    # Read the built program exe
    print("Reading program executable...")
    with open('dist/AhFlippingTool.exe', 'rb') as f:
        exe_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Create the installer with the embedded program
    print("Creating installer...")
    with open('installer.py', 'w') as f:
        f.write(installer_code.format(exe_data))
    
    # Build the installer
    PyInstaller.__main__.run([
        'installer.py',
        '--onefile',
        '--noconsole',
        '--clean',
        '--name=AhFlippingTool_Setup',
        '--uac-admin'
    ])
    
    # Clean up temporary files
    print("Cleaning up...")
    os.remove('ahflipping.py')
    os.remove('installer.py')
    if os.path.exists('AhFlippingTool.exe'):
        os.remove('AhFlippingTool.exe')
    
    print("Build complete! Your installer is in the dist folder.")

if __name__ == '__main__':
    build_program_and_installer()
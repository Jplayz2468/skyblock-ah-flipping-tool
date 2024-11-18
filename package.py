import os
import base64
import PyInstaller.__main__

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
    # First, build the main program from main.py
    print("Building main program...")
    PyInstaller.__main__.run([
        'main.py',
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
    os.remove('installer.py')
    
    print("Build complete! Your installer is in the dist folder.")

if __name__ == '__main__':
    build_program_and_installer()
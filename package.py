import os
import sys
import winreg
import shutil
from datetime import datetime
import PyInstaller.__main__

class InstallerBuilder:
    def __init__(self, main_script):
        self.app_name = 'AhFlippingTool'
        self.main_script = main_script
        self.install_dir = os.path.join(os.getenv('PROGRAMFILES'), 'AhFlippingTool')
        
    def create_installer(self):
        installer_script = f"""
import os
import sys
import winreg
import shutil
from tkinter import Tk, Label, Button, messagebox

def install():
    install_dir = r'{self.install_dir}'
    
    # Create installation directory
    os.makedirs(install_dir, exist_ok=True)
    
    # Copy program files
    shutil.copy(sys.argv[0], install_dir)
    shutil.copy('{self.main_script}', install_dir)
    
    # Create uninstaller
    create_uninstaller(install_dir)
    
    # Add to Windows registry for Programs and Features
    add_to_registry()
    
    # Create start menu shortcut
    create_shortcut()
    
    messagebox.showinfo('Success', 'AhFlippingTool has been installed successfully!')

def create_uninstaller(install_dir):
    uninstaller = os.path.join(install_dir, 'uninstall.exe')
    with open(uninstaller, 'w') as f:
        f.write('''
import os
import winreg
import shutil
import sys
from tkinter import messagebox

def uninstall():
    try:
        # Remove registry entries
        winreg.DeleteKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AhFlippingTool'
        )
        
        # Remove installation directory
        install_dir = os.path.dirname(sys.argv[0])
        shutil.rmtree(install_dir)
        
        # Remove start menu shortcut
        shortcut_path = os.path.join(
            os.getenv('PROGRAMDATA'),
            'Microsoft\\Windows\\Start Menu\\Programs',
            'AhFlippingTool.lnk'
        )
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            
        messagebox.showinfo('Success', 'AhFlippingTool has been uninstalled successfully!')
    except Exception as e:
        messagebox.showerror('Error', f'Failed to uninstall: {{str(e)}}')

if __name__ == '__main__':
    uninstall()
        ''')

def add_to_registry():
    key_path = r'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AhFlippingTool'
    
    try:
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, 'DisplayName', 0, winreg.REG_SZ, 'AhFlippingTool')
        winreg.SetValueEx(key, 'Publisher', 0, winreg.REG_SZ, 'AhFlippingTool')
        winreg.SetValueEx(key, 'UninstallString', 0, winreg.REG_SZ, 
                         os.path.join(r'{self.install_dir}', 'uninstall.exe'))
        winreg.CloseKey(key)
    except Exception as e:
        messagebox.showerror('Error', f'Failed to add registry entries: {{str(e)}}')

def create_shortcut():
    shortcut_path = os.path.join(
        os.getenv('PROGRAMDATA'),
        'Microsoft\\Windows\\Start Menu\\Programs',
        'AhFlippingTool.lnk'
    )
    with open(shortcut_path, 'w') as f:
        f.write(os.path.join(r'{self.install_dir}', '{self.main_script}'))

if __name__ == '__main__':
    root = Tk()
    root.title('AhFlippingTool Installer')
    root.geometry('300x150')
    
    Label(root, text='AhFlippingTool Installer').pack(pady=20)
    Button(root, text='Install', command=lambda: [install(), root.destroy()]).pack()
    Button(root, text='Cancel', command=root.destroy).pack(pady=10)
    
    root.mainloop()
"""
        
        # Create the installer script
        installer_path = 'AhFlippingTool_Setup.py'
        with open(installer_path, 'w') as f:
            f.write(installer_script)
        
        # Create the executable
        PyInstaller.__main__.run([
            installer_path,
            '--onefile',
            '--noconsole',
            '--clean',
            '--name=AhFlippingTool_Setup'
        ])
        
        # Clean up the temporary .py file
        os.remove(installer_path)
        
        return os.path.join('dist', 'AhFlippingTool_Setup.exe')

if __name__ == '__main__':
    # Example usage
    builder = InstallerBuilder(main_script='main.py')
    installer_path = builder.create_installer()
    print(f'Installer created: {installer_path}')
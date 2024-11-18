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
        self.install_dir = os.path.join(os.getenv('PROGRAMFILES'), 'AhFlippingTool').replace('\\', '\\\\')
        
    def create_installer(self):
        installer_script = f"""
import os
import sys
import winreg
import shutil
import ctypes
from tkinter import Tk, Label, Button, messagebox

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
        # Ensure we're running as admin
        if not is_admin():
            run_as_admin()
            return

        install_dir = r'{self.install_dir}'
        
        # Create installation directory
        os.makedirs(install_dir, exist_ok=True)
        
        # Get the path of the currently running executable
        if getattr(sys, 'frozen', False):
            current_exe = sys.executable
        else:
            current_exe = sys.argv[0]
            
        # Get the directory containing main.py (same as installer location)
        source_dir = os.path.dirname(os.path.abspath(current_exe))
        main_script_path = os.path.join(source_dir, '{self.main_script}')
        
        # Copy program files
        if os.path.exists(main_script_path):
            shutil.copy2(main_script_path, install_dir)
            shutil.copy2(current_exe, install_dir)
        else:
            raise FileNotFoundError(f"Could not find {self.main_script}")
        
        # Create uninstaller
        create_uninstaller(install_dir)
        
        # Add to Windows registry
        add_to_registry()
        
        # Create start menu shortcut
        create_shortcut()
        
        messagebox.showinfo('Success', 'AhFlippingTool has been installed successfully!')
    except Exception as e:
        messagebox.showerror('Error', f'Installation failed: {{str(e)}}')

def create_uninstaller(install_dir):
    uninstaller = os.path.join(install_dir, 'uninstall.exe')
    uninstall_code = r'''
import os
import sys
import winreg
import shutil
import ctypes
from tkinter import Tk, Label, Button, messagebox

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

def uninstall():
    try:
        if not is_admin():
            run_as_admin()
            return
            
        # Remove registry entries
        try:
            winreg.DeleteKey(
                winreg.HKEY_LOCAL_MACHINE,
                r'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AhFlippingTool'
            )
        except WindowsError:
            pass
        
        # Remove installation directory
        install_dir = os.path.dirname(os.path.abspath(sys.executable))
        os.chdir(os.path.dirname(install_dir))  # Move out of the directory before deleting
        shutil.rmtree(install_dir, ignore_errors=True)
        
        # Remove start menu shortcut
        shortcut_path = os.path.join(
            os.getenv('PROGRAMDATA'),
            'Microsoft\\Windows\\Start Menu\\Programs',
            'AhFlippingTool.lnk'
        )
        try:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
        except:
            pass
            
        messagebox.showinfo('Success', 'AhFlippingTool has been uninstalled successfully!')
        sys.exit(0)
    except Exception as e:
        messagebox.showerror('Error', f'Failed to uninstall: {{str(e)}}')

if __name__ == '__main__':
    root = Tk()
    root.withdraw()  # Hide the main window
    uninstall()
'''
    with open(uninstaller, 'w') as f:
        f.write(uninstall_code)

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
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut_path = os.path.join(
            os.getenv('PROGRAMDATA'),
            'Microsoft\\Windows\\Start Menu\\Programs',
            'AhFlippingTool.lnk'
        )
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = os.path.join(r'{self.install_dir}', '{self.main_script}')
        shortcut.save()
    except:
        # Fallback method if win32com is not available
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
            '--name=AhFlippingTool_Setup',
            '--uac-admin'  # Request admin privileges
        ])
        
        # Clean up the temporary .py file
        os.remove(installer_path)
        
        return os.path.join('dist', 'AhFlippingTool_Setup.exe')

if __name__ == '__main__':
    # Example usage
    builder = InstallerBuilder(main_script='main.py')
    installer_path = builder.create_installer()
    print(f'Installer created: {installer_path}')
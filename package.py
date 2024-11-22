import PyInstaller.__main__
import os
import shutil

def create_installer_script(exe_name):
    """Create the Windows installer batch script"""
    installer_content = f'''@echo off
setlocal enabledelayedexpansion

set "APPNAME={exe_name}"
set "INSTALLDIR=%PROGRAMFILES%\\%APPNAME%"
set "SHORTCUTDIR=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"

:: Create installation directory
if not exist "%INSTALLDIR%" mkdir "%INSTALLDIR%"

:: Copy executable and any additional files
echo Installing %APPNAME%...
copy "%APPNAME%.exe" "%INSTALLDIR%"
if exist "data" xcopy /E /I "data" "%INSTALLDIR%\\data"

:: Create Start Menu shortcut
echo Creating shortcuts...
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%SHORTCUTDIR%\\%APPNAME%.lnk'); $SC.TargetPath = '%INSTALLDIR%\\%APPNAME%.exe'; $SC.Save()"

:: Create Desktop shortcut
powershell -Command "$WS = New-Object -ComObject WScript.Shell; $SC = $WS.CreateShortcut('%USERPROFILE%\\Desktop\\%APPNAME%.lnk'); $SC.TargetPath = '%INSTALLDIR%\\%APPNAME%.exe'; $SC.Save()"

:: Create uninstaller
echo @echo off > "%INSTALLDIR%\\uninstall.bat"
echo rmdir /S /Q "%INSTALLDIR%" >> "%INSTALLDIR%\\uninstall.bat"
echo del "%SHORTCUTDIR%\\%APPNAME%.lnk" >> "%INSTALLDIR%\\uninstall.bat"
echo del "%USERPROFILE%\\Desktop\\%APPNAME%.lnk" >> "%INSTALLDIR%\\uninstall.bat"

echo Installation complete!
echo Your application has been installed to: %INSTALLDIR%
pause
'''
    with open('installer.bat', 'w') as f:
        f.write(installer_content)

def main():
    # App name configuration
    APP_NAME = "AhFlippingApp"
    
    # Get the current directory
    current_dir = os.getcwd()
    
    # Path to your main.py file
    main_script = os.path.join(current_dir, 'main.py')
    
    # Clean up previous builds
    dist_path = os.path.join(current_dir, 'dist')
    build_path = os.path.join(current_dir, 'build')
    spec_file = os.path.join(current_dir, f'{APP_NAME}.spec')
    
    for path in [dist_path, build_path, spec_file]:
        if os.path.exists(path):
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
    
    print("Building executable...")
    
    # Run PyInstaller
    PyInstaller.__main__.run([
        'main.py',
        '--onefile',
        '--clean',
        f'--name={APP_NAME}',
        '--noconsole'  # Remove this line if you want to show console
    ])
    
    print("Creating installer...")
    
    # Create installer script
    create_installer_script(APP_NAME)
    
    # Move executable and installer to a deployment folder
    deploy_dir = os.path.join(current_dir, 'deploy')
    if not os.path.exists(deploy_dir):
        os.makedirs(deploy_dir)
    
    # Move files to deployment directory
    shutil.copy(
        os.path.join(dist_path, f'{APP_NAME}.exe'),
        os.path.join(deploy_dir, f'{APP_NAME}.exe')
    )
    shutil.move('installer.bat', os.path.join(deploy_dir, 'installer.bat'))
    
    # Copy any additional data folders if they exist
    if os.path.exists('data'):
        shutil.copytree('data', os.path.join(deploy_dir, 'data'))
    
    print(f"""
Deployment package created successfully!
Location: {deploy_dir}

To distribute your application:
1. Share the entire 'deploy' folder
2. Users just need to run installer.bat as administrator

Contents:
- {APP_NAME}.exe (Your application)
- installer.bat (Installation script)
- data folder (if it exists)
""")

if __name__ == "__main__":
    main()

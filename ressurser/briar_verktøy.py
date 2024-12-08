# briar_utils.py
import subprocess

def start_briar(device_id):
    """
    Starter Briar-applikasjonen på enheten ved hjelp av adb.

    Args:
        device_id (str): ID-en til enheten.
    """
    package_name = "org.briarproject.briar.android"
    activity_name = ".splash.SplashScreenActivity"
    
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "start", "-n", f"{package_name}/{activity_name}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode != 0:
            print(f"Feil ved oppstart av Briar på enhet {device_id}: {result.stderr.decode('utf-8')}")
    except Exception as e:
        print(f"En feil oppstod ved oppstart av Briar på enhet {device_id}: {e}")
import subprocess
import sys
import platform


if __name__ == "__main__":
    subprocess.Popen("pylupdate5 ciu_net.pro", shell=True)
    subprocess.Popen("pyrcc5 resources.qrc > ciunet/resources.py", shell=True)
    print("done")
    sys.exit()

# crop_weili_manual.py
import os.path
import subprocess
projectpath=os.path.dirname(__file__)+os.sep

subprocess.check_output("pyinstaller -F imgServerFastApi.py",shell=True,
                        cwd=projectpath)


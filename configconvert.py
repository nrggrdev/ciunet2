version="0.0.0"
defalutDir="config_template"
configDir="config"
from configobj import ConfigObj
import os
import datetime
import shutil
import sys
d=datetime.datetime.now()
bd=(d.strftime("config_backup.Y%YM%mD%d_%H%M%S"))
shutil.copytree(configDir,bd)

def mergeConfig(newFile,oldFile=None):
    if oldFile is None:
        oldFile=newFile
    oldCiunet_default = ConfigObj(os.path.join(defalutDir,f"{oldFile}.ini"),encoding="utf8")
    newCiunet_default = ConfigObj(os.path.join(configDir,f"{newFile}.ini"),encoding="utf8")
#    oldCiunet_default.merge(newCiunet_default)
    oldCiunet_default.merge(newCiunet_default)
    oldCiunet_default.filename=os.path.join(configDir,f"{newFile}.ini")
    oldCiunet_default.write()
    print (f"{oldFile}.ini merged with {newFile}.ini")
mergeConfig("config_defaults")
mergeConfig("config")
def mergeScanner():
    newCiunet_config = ConfigObj(os.path.join(configDir,"config.ini"),encoding="utf8")
    print(newCiunet_config)
    print(newCiunet_config.keys())
    scanners=newCiunet_config['kiln']['scanners']
    if  type(scanners)==str:
        scanners=(scanners,)
    for scanner in list(scanners):
        mergeConfig(scanner.split(".")[0],"scanner1")
        scanner_config = ConfigObj(os.path.join(configDir, scanner), encoding="utf8")
        pass


mergeScanner()
mergeConfig('tireslip')
__author__ = 'Junghwan Kim'
__copyright__ = 'Copyright 2016-2018 Junghwan Kim. All Rights Reserved.'
__version__ = '1.0.1'

import os
import pydicom
from cryptography.fernet import Fernet

path = raw_input("Enter Full Path: ")
try:
    ds = pydicom.dcmread(path)
    if ds.PatientID:
        pass
except:
    print "[ERROR] Cannot load dicom file."
    exit(1)

print '\n[SUCCESS] Dicom file loaded:', os.path.basename(path)
print '[INFO] Encrypted Patient ID:', ds.PatientID[0:25] + '...'

pkey = raw_input("\nEnter PKEY: ")
try:
    fernet = Fernet(pkey)
    patientid = fernet.decrypt(str(ds.PatientID))
    if patientid:
        print '\n[SUCCESS] Patient ID:', patientid
except:
    print "\n[ERROR] Incorrect PKEY."
    exit(1)

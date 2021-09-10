__author__ = 'Junghwan Kim'
__copyright__ = 'Copyright 2016-2018 Junghwan Kim. All Rights Reserved.'
__version__ = '1.0.2'

import base64
import logging
import os
import pydicom
import shutil
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def main():

    # Set path
    path = '/home/jkim/NAS/temp_dicom/ifac/New_Cerebral_Infarction/LDE2'
    path_parent = os.path.abspath(os.path.join(path, '..'))
    folder_name = os.path.basename(path)
    print '\n----------------------------------------------------------------------------------------------------' \
          '\nDICOM Anonymizer %s' \
          '\n----------------------------------------------------------------------------------------------------' \
          '\nYou set path: %s' % (__version__, path)
    answer = raw_input('Are you sure to start right now (y/n)? ')
    if answer != 'y':
        print '\n[ERROR] Cancelled by user.'
        exit(0)

    # Log file
    name_log = 'log.log'
    path_log = path_parent + '/1_LOG/' + folder_name
    if not os.path.exists(path_log):
        os.makedirs(path_log)
    else:
        shutil.rmtree(path_log)
        os.makedirs(path_log)
    logging.basicConfig(filename=os.path.join(path_log, name_log), filemode='w', level=logging.INFO)

    # PKEY file
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=os.urandom(16), iterations=100000,
                     backend=default_backend())
    pkey = base64.urlsafe_b64encode(kdf.derive('aksdjlasdjlasjdlas'))
    fernet = Fernet(pkey)
    path_pkey = path_parent + '/2_PKEY/' + folder_name
    if not os.path.exists(path_pkey):
        os.makedirs(path_pkey)
    else:
        shutil.rmtree(path_pkey)
        os.makedirs(path_pkey)

    # Recur load folder function
    i = 0
    result = [0, 0, 0]    # Total, Success, Error
    folder_patient = sorted(os.listdir(path))
    while i < len(folder_patient):
        j = 0
        folder_patient_modality = sorted(os.listdir(path + '/' + folder_patient[i]))
        while j < len(folder_patient_modality):
            path_patient_modality = path + '/' + folder_patient[i] + '/' + folder_patient_modality[j]
            anonymize(path_patient_modality, fernet, result)
            j += 1
        if folder_patient[i] != 'LOG' and folder_patient[i] != 'PKEY':
            file_pkey = open(path_pkey + '/pkey.log', 'a')
            file_pkey.write('[' + path + '/' + folder_patient[i] + ']\t' + pkey + '\n')
        i += 1

    # Print result
    print '\n----------------------------------------------------------------------------------------------------' \
          '\nResult' \
          '\n----------------------------------------------------------------------------------------------------' \
          '\nTotal:   ', result[0], 'Files' \
          '\nSuccess: ', result[1], 'Files' \
          '\nError:   ', result[2], 'Files' \
          '\nLOG:     ', path_log + '/log.log' \
          '\nPKEY:    ', path_pkey + '/pkey.log'

    if result[2] != 0:
        print '\n####################################################################################################' \
              '\n[WARNING] Error files MUST BE moved to another folder because it has sensitive personal information.' \
              '\n####################################################################################################'


def anonymize(path, fernet, result):

    # Ignore log files
    if path.endswith('/pkey.log'):
        return None
    if path.endswith('/log.log'):
        return None

    # Record log
    logging.info('[INFO] Folder loaded: %s', path)
    print '[INFO] Folder loaded:', path

    # Initialize accession number
    global accessionNumber
    accessionNumber = ''

    # Recur load file
    for paths, dirs, files in os.walk(path):
        for name in sorted(files):

            # Read only dicom file
            if not name.endswith('.dcm'):
                continue

            # Get dicom data set
            ds = pydicom.dcmread(os.path.join(paths, name))

            # Check SpecificCharacterSet
            if 'SpecificCharacterSet' in ds:
                if ds.SpecificCharacterSet == 'ISO IR 149':
                    error = True
                    logging.info('[ERROR] LookupError: unknown encoding: ISO IR 149: %s', os.path.join(paths, name))
                    print '[ERROR] LookupError: unknown encoding: ISO IR 149:', os.path.join(paths, name)
                    result[2] += 1
                    continue

            # Initiate basic information
            patientid = fernet.encrypt(str(ds.PatientID))
            error = False

            # Check AcquisitionTime
            if 'AcquisitionTime' in ds:
                acquisitionTime = ds.AcquisitionTime[0:6]
            else:
                acquisitionTime = '000000'

            # Generate accession number
            if 'AcquisitionDate' in ds:
                year = ds.AcquisitionDate[0:4]
                if not accessionNumber:
                    accessionNumber = '%8s%0.6s%6s' % (ds.AcquisitionDate, acquisitionTime,
                                                       str(uuid.uuid4().int >> 64)[0:6])
            elif 'StudyDate' in ds:
                year = ds.StudyDate[0:4]
                if not accessionNumber:
                    accessionNumber = '%8s%0.6s%6s' % (ds.StudyDate, acquisitionTime,
                                                       str(uuid.uuid4().int >> 64)[0:6])
            else:
                error = True
                logging.info('[ERROR] Not exists ds.AcquisitionDate and ds.StudyDate: %s', os.path.join(paths, name))
                print '[ERROR] Not exists ds.AcquisitionDate and ds.StudyDate:', os.path.join(paths, name)
                raw_input('Press Enter to skip this file... ')

            # Generate dicom file name
            if 'InstanceNumber' in ds:
                number = '{:03d}'.format(ds.InstanceNumber)
                name_encrypted = accessionNumber + '_' + number + '.dcm'
            else:
                error = True
                logging.info('[ERROR] Not exists ds.InstanceNumber: %s', os.path.join(paths, name))
                print '[ERROR] Not exists ds.InstanceNumber:', os.path.join(paths, name)
                raw_input('Press Enter to skip this file... ')

            # Calculate patient age
            try:
                if ds.PatientAge == '000Y':
                    age = '{:03d}Y'.format(int(year) - int(ds.PatientBirthDate[0:4]) - 1)
                    ds.PatientAge = age
            except AttributeError:
                age = '{:03d}Y'.format(int(year) - int(ds.PatientBirthDate[0:4]) - 1)
                ds.add_new(0x00101010, 'AS', age)
            except TypeError:
                error = True
                logging.info('[ERROR] Incorrect ds.PatientAge type: %s', os.path.join(paths, name))
                print '[ERROR] Incorrect ds.PatientAge type:', os.path.join(paths, name)
                raw_input('Press Enter to skip this file... ')
            except ValueError:
                ds.PatientAge = '000Y'
                logging.info('[WARNING] Overwrite ds.PatientAge value = 000Y: %s', os.path.join(paths, name))
                print '[WARNING] Overwrite ds.PatientAge value = 000Y:', os.path.join(paths, name)

            # Write dicom data
            def write(element, value):
                try:
                    attribute = getattr(ds, element)
                    if attribute:
                        setattr(ds, element, value)
                except AttributeError:
                    pass
                except TypeError:
                    error = True
                    logging.info('[ERROR] Incorrect %s type: %s', element, os.path.join(paths, name))
                    print '[ERROR] Incorrect ' + element + ' type:', os.path.join(paths, name)
                    raw_input('Press Enter to skip this file... ')
                except ValueError:
                    error = True
                    logging.info('[ERROR] Incorrect %s value: %s', element, os.path.join(paths, name))
                    print '[ERROR] Incorrect ' + element + ' value:', os.path.join(paths, name)
                    raw_input('Press Enter to skip this file... ')

            # Overwrite element
            write('AccessionNumber', accessionNumber)
            write('PatientID', patientid)

            # Clear element
            write('ContentDate', '19010101')
            write('ContentTime', '000000')
            write('DeviceSerialNumber', '0')
            write('InstitutionName', 'institution')
            write('InstitutionalDepartmentName', 'department')
            write('Manufacturer', 'manufacturer')
            write('ManufacturerModelName', 'model')
            write('OperatorsName', 'operator')
            write('PatientBirthDate', '19010101')
            write('OtherPatientIDs', '00000000')
            write('PatientName', 'Anonymous')
            write('ReferringPhysicianName', 'physician')
            write('SeriesDate', '19010101')
            write('SeriesTime', '000000')
            write('SoftwareVersions', '1.0')
            write('StationName', 'station')
            write('StudyDate', '19010101')
            write('StudyDescription', '00000000')
            write('StudyID', '1')
            write('StudyTime', '000000')
            write('InstitutionAddress', 'address')
            write('OtherPatientNames', 'Anonymous')
            write('InstanceCreationDate', '19010101')
            write('InstanceCreationTime', '000000')
            write('PerformingPhysicianName', 'phycian')
            write('NameofPhysiciansReadingStudy', 'physician')
            write('PhysiciansofRecord', 'physician')
            write('PatientWeight', '0')
            write('PatientSize', '0')
            write('PatientAddress', 'address')
            write('AdditionalPatientHistory', '')
            write('EthnicGroup', 'ethnicity')
            write('ReviewDate', '19010101')
            write('ReviewTime', '000000')
            write('ReviewerName', 'anonymous')

            result[0] += 1
            if error is False:
                ds.save_as(os.path.join(paths, name))
                os.rename(os.path.join(paths, name), os.path.join(paths, name_encrypted))
                logging.info('[SUCCESS] File processed: %s', os.path.join(paths, name_encrypted))
                print '[SUCCESS] File processed:', os.path.join(paths, name_encrypted)
                result[1] += 1
            elif error is True:
                result[2] += 1

    return None


if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-


import json
import os
import shutil
from tempfile import TemporaryDirectory

from bids import BIDSLayout

from dcm2bids.dcm2bids_gen import Dcm2BidsGen
from dcm2bids.utils.utils import DEFAULT
from dcm2bids.utils.io import load_json

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def test_help_option(script_runner):
    ret = script_runner.run(['dcm2bids', '--help'])
    assert ret.success


def compare_json(original_file, converted_file):
    with open(original_file) as f:
        original_json = json.load(f)

    with open(converted_file) as f:
        converted_json = json.load(f)

    converted_json.pop('Dcm2bidsVersion', None)

    return original_json == converted_json


def test_dcm2bids():
    # tmpBase = os.path.join(TEST_DATA_DIR, "tmp")
    # bidsDir = TemporaryDirectory(dir=tmpBase)
    bidsDir = TemporaryDirectory()

    tmpSubDir = os.path.join(bidsDir.name, DEFAULT.tmpDirName, "sub-01")
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(TEST_DATA_DIR, "01",
                      os.path.join(TEST_DATA_DIR, "config_test.json"),
                      bidsDir.name)
    app.run()

    layout = BIDSLayout(bidsDir.name, validate=False)

    assert layout.get_subjects() == ["01"]
    assert layout.get_sessions() == []
    assert layout.get_tasks() == ["rest"]
    assert layout.get_runs() == [1, 2, 3]

    app = Dcm2BidsGen(TEST_DATA_DIR, "01",
                      os.path.join(TEST_DATA_DIR, "config_test.json"),
                      bidsDir.name)
    app.run()

    fmapFile = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_echo-492_fmap.json")
    data = load_json(fmapFile)
    assert data["IntendedFor"] == [os.path.join("dwi", "sub-01_dwi.nii.gz"),
                                   os.path.join("anat", "sub-01_T1w.nii")]

    fmapFile = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_echo-738_fmap.json")
    data = load_json(fmapFile)
    fmapMtime = os.stat(fmapFile).st_mtime
    assert data["IntendedFor"] == os.path.join("dwi", "sub-01_dwi.nii.gz")

    data = load_json(
        os.path.join(
            bidsDir.name, "sub-01", "localizer", "sub-01_run-01_localizer.json"
        )
    )
    assert data["ProcedureStepDescription"] == "Modify by dcm2bids"

    # rerun
    shutil.rmtree(tmpSubDir)
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(
        [TEST_DATA_DIR],
        "01",
        os.path.join(TEST_DATA_DIR, "config_test.json"),
        bidsDir.name,
    )
    app.run()

    fmapMtimeRerun = os.stat(fmapFile).st_mtime
    assert fmapMtime == fmapMtimeRerun


def test_caseSensitive_false():
    # Validate caseSensitive false
    bidsDir = TemporaryDirectory()

    tmpSubDir = os.path.join(bidsDir.name, DEFAULT.tmpDirName, "sub-01")
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(TEST_DATA_DIR, "01",
                      os.path.join(TEST_DATA_DIR,
                                   "config_test_not_case_sensitive_option.json"),
                      bidsDir.name)
    app.run()

    layout = BIDSLayout(bidsDir.name,
                        validate=False)

    path_dwi = os.path.join(bidsDir.name,
                            "sub-01",
                            "dwi",
                            "sub-01_dwi.json")

    path_t1 = os.path.join(bidsDir.name,
                           "sub-01",
                           "anat",
                           "sub-01_T1w.json")

    path_localizer = os.path.join(bidsDir.name,
                                  "sub-01",
                                  "localizer",
                                  "sub-01_run-01_localizer.json")

    original_01_localizer = os.path.join(TEST_DATA_DIR,
                                         "sidecars",
                                         "001_localizer_20100603125600_i00001.json")

    original_02_localizer = os.path.join(TEST_DATA_DIR,
                                         "sidecars",
                                         "001_localizer_20100603125600_i00002.json")

    original_03_localizer = os.path.join(TEST_DATA_DIR,
                                         "sidecars",
                                         "001_localizer_20100603125600_i00003.json")

    # Input T1 is UPPER CASE (json)
    json_t1 = layout.get(subject='01',
                         datatype='anat',
                         extension='json',
                         suffix='T1w')

    # Input localizer is lowercase (json)
    json_01_localizer = layout.get(subject='01',
                                   extension='json',
                                   suffix='localizer',
                                   run='01')

    json_02_localizer = layout.get(subject='01',
                                   extension='json',
                                   suffix='localizer',
                                   run='02')

    json_03_localizer = layout.get(subject='01',
                                   extension='json',
                                   suffix='localizer',
                                   run='03')

    # Asking for something with low and up cases (config file)
    json_dwi = layout.get(subject='01',
                          datatype='dwi',
                          extension='json',
                          suffix='dwi')

    assert set(os.listdir(os.path.join(bidsDir.name,
                                       'sub-01'))) == {'anat',
                                                       'dwi',
                                                       'localizer'}
    assert json_t1[0].path == path_t1
    assert json_01_localizer[0].path == path_localizer
    assert json_dwi[0].path == path_dwi

    # Check order runs when same number
    # i00001 no AcquisitionTime
    # i00002 AcquisitionTime after i00003
    assert compare_json(original_01_localizer,
                        json_01_localizer[0].path)
    assert compare_json(original_02_localizer,
                        json_03_localizer[0].path)
    assert compare_json(original_03_localizer,
                        json_02_localizer[0].path)

    bidsDir = TemporaryDirectory()

    tmpSubDir = os.path.join(bidsDir.name, DEFAULT.tmpDirName, "sub-01")
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(TEST_DATA_DIR, "01",
                      os.path.join(TEST_DATA_DIR, "config_test.json"),
                      bidsDir.name)
    app.run()

    layout = BIDSLayout(bidsDir.name, validate=False)

    assert layout.get_subjects() == ["01"]
    assert layout.get_sessions() == []
    assert layout.get_tasks() == ["rest"]
    assert layout.get_runs() == [1, 2, 3]

    fmapFile = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_echo-492_fmap.json")
    data = load_json(fmapFile)
    assert data["IntendedFor"] == [os.path.join("dwi", "sub-01_dwi.nii.gz"),
                                   os.path.join("anat", "sub-01_T1w.nii")]

    fmapFile = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_echo-738_fmap.json")
    data = load_json(fmapFile)
    fmapMtime = os.stat(fmapFile).st_mtime
    assert data["IntendedFor"] == os.path.join("dwi", "sub-01_dwi.nii.gz")

    data = load_json(
        os.path.join(
            bidsDir.name, "sub-01", "localizer", "sub-01_run-01_localizer.json"
        )
    )
    assert data["ProcedureStepDescription"] == "Modify by dcm2bids"

    # rerun
    shutil.rmtree(tmpSubDir)
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(
        [TEST_DATA_DIR],
        "01",
        os.path.join(TEST_DATA_DIR, "config_test.json"),
        bidsDir.name,
    )
    app.run()

    fmapMtimeRerun = os.stat(fmapFile).st_mtime
    assert fmapMtime == fmapMtimeRerun


def test_dcm2bids_auto_extract():
    bidsDir = TemporaryDirectory()

    tmpSubDir = os.path.join(bidsDir.name, DEFAULT.tmpDirName, "sub-01")
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(TEST_DATA_DIR, "01",
                      os.path.join(TEST_DATA_DIR, "config_test_auto_extract.json"),
                      bidsDir.name,
                      auto_extract_entities=True)
    app.run()

    layout = BIDSLayout(bidsDir.name, validate=False)

    assert layout.get_subjects() == ["01"]
    assert layout.get_sessions() == []
    assert layout.get_tasks() == ["rest"]
    assert layout.get_runs() == [1, 2]

    epi_file = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_dir-AP_epi.json")
    data = load_json(epi_file)

    assert os.path.exists(epi_file)
    assert data["IntendedFor"] == [os.path.join("dwi", "sub-01_dwi.nii.gz"),
                                   os.path.join("anat", "sub-01_T1w.nii")]

    func_task = os.path.join(bidsDir.name, "sub-01",
                             "func",
                             "sub-01_task-rest_acq-highres_bold.json")
    data = load_json(func_task)

    assert os.path.exists(func_task)
    assert data['TaskName'] == "rest"


def test_dcm2bids_complex():
    bidsDir = TemporaryDirectory()

    tmpSubDir = os.path.join(bidsDir.name, DEFAULT.tmpDirName, "sub-01")
    shutil.copytree(os.path.join(TEST_DATA_DIR, "sidecars"), tmpSubDir)

    app = Dcm2BidsGen(TEST_DATA_DIR, "01",
                      os.path.join(TEST_DATA_DIR, "config_test_complex.json"),
                      bidsDir.name)
    app.run()

    layout = BIDSLayout(bidsDir.name, validate=False)

    assert layout.get_subjects() == ["01"]
    assert layout.get_sessions() == []
    assert layout.get_runs() == [1, 2, 3]

    fmap_file_1 = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_run-01_fmap.json")
    fmap_file_2 = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_run-02_fmap.json")
    fmap_file_3 = os.path.join(bidsDir.name, "sub-01", "fmap", "sub-01_run-03_fmap.json")
    assert os.path.exists(fmap_file_1)
    assert os.path.exists(fmap_file_2)
    assert os.path.exists(fmap_file_3)

    localizer_file_1 = os.path.join(bidsDir.name, "sub-01", "localizer", "sub-01_run-01_localizer.json")
    localizer_file_2 = os.path.join(bidsDir.name, "sub-01", "localizer", "sub-01_run-02_localizer.json")
    assert os.path.exists(localizer_file_1)
    assert os.path.exists(localizer_file_2)

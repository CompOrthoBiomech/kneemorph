import json
from pathlib import Path

import vtkmodules.all as vtk


def read_stl(filepath: Path | str):
    reader = vtk.vtkSTLReader()
    reader.SetFileName(Path(filepath).as_posix())
    reader.Update()
    return reader.GetOutput()


def read_vtp(filepath: Path | str):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(Path(filepath).as_posix())
    reader.Update()
    return reader.GetOutput()


def save_vtp(poly: vtk.vtkPolyData, filepath: Path | str):
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(Path(filepath).as_posix())
    writer.SetInputData(poly)
    writer.Write()


def save_json(data: dict, filepath: Path | str):
    with open(Path(filepath).as_posix(), "w") as f:
        json.dump(data, f, indent=4)

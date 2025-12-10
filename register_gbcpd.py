import argparse
import json
import platform
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from config import GBCPDConfig
from utils import read_vtp, save_vtp

if platform.system() == "Windows":
    bcpd = "bcpd.exe"
else:
    bcpd = "bcpd"

CLI_LUT = {
    "omega": "-w",
    "lambda_": "-l",
    "beta": "-b",
    "gamma": "-g",
    "kappa": "-k",
    "K": "-K",
    "J": "-J",
    "r": "-r",
    "c": "-c",
    "n_max": "-n",
    "n_min": "-N",
}


def convert_mesh_points_to_text(mesh: vtk.vtkPolyData) -> str:
    points = vtk_to_numpy(mesh.GetPoints().GetData())
    with NamedTemporaryFile(suffix=".txt", mode="wt", delete=False, delete_on_close=True) as fid:
        np.savetxt(fid, points, fmt="%f")
    return fid.name


def convert_mesh_tris_to_text(mesh: vtk.vtkPolyData) -> str:
    tris = vtk_to_numpy(mesh.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    with NamedTemporaryFile(suffix=".txt", mode="wt", delete=False, delete_on_close=True) as fid:
        np.savetxt(fid, tris, fmt="%d")
    return fid.name


def map_source_mesh(mesh: vtk.vtkPolyData) -> vtk.vtkPolyData:
    points = np.loadtxt("output_y.txt", dtype=np.float32)
    vtk_array = numpy_to_vtk(points, deep=True, array_type=vtk.VTK_FLOAT)
    mesh.GetPoints().SetData(vtk_array)
    return mesh


def extract_insertion_points(mesh: vtk.vtkPolyData) -> vtk.vtkPolyData:
    points = vtk_to_numpy(mesh.GetPoints().GetData())
    point_ids = mesh.GetPointData().GetArray("InsertionID")
    unique_ids = sorted(list(np.unique(vtk_to_numpy(point_ids))))
    appended_polydata = vtk.vtkAppendPolyData()
    for id in unique_ids[1:]:
        coords = points[point_ids == id]
        id_array = numpy_to_vtk(np.full(coords.shape[0], id, dtype=int), deep=True, array_type=vtk.VTK_ID_TYPE)
        id_array.SetName("InsertionID")
        poly = vtk.vtkPolyData()
        poly_points = vtk.vtkPoints()
        poly_cells = vtk.vtkCellArray()
        for i in range(coords.shape[0]):
            poly_points.InsertNextPoint(coords[i])
            poly_cells.InsertNextCell(1, [i])
        poly.SetPoints(poly_points)
        poly.SetVerts(poly_cells)
        poly.GetPointData().AddArray(id_array)
        appended_polydata.AddInputData(poly)
    appended_polydata.Update()
    return appended_polydata.GetOutput()


def create_pretransform(config: GBCPDConfig) -> vtk.vtkTransform:
    if config.pretransform_file is not None:
        pretransform_file = Path(config.pretransform_file)
        if pretransform_file.is_file():
            pretransform_matrix = np.load(pretransform_file)
        else:
            raise FileNotFoundError(f"File not found: {pretransform_file}")
    else:
        pretransform_matrix = np.eye(4)
    pretransform = vtk.vtkTransform()
    pretransform.SetMatrix(pretransform_matrix.ravel())
    pretransform.Inverse()
    return pretransform


def transform_polydata(polydata: vtk.vtkPolyData, tx: vtk.vtkTransform) -> vtk.vtkPolyData:
    transform_filter = vtk.vtkTransformPolyDataFilter()
    transform_filter.SetInputData(polydata)
    transform_filter.SetTransform(tx)
    transform_filter.Update()
    return transform_filter.GetOutput()


def main(config: GBCPDConfig):
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target_mesh_path = Path(config.target_mesh_path)
    target_meshes = []
    if target_mesh_path.is_file() and target_mesh_path.suffix == ".vtp":
        target_meshes.append((target_mesh_path, read_vtp(target_mesh_path.as_posix())))
    elif target_mesh_path.is_dir():
        target_meshes = [(path, read_vtp(path.as_posix())) for path in target_mesh_path.glob("*.vtp")]
    else:
        raise FileNotFoundError(f"File not found: {target_mesh_path}")
    source_mesh = read_vtp(config.source_mesh_file)
    source_points_file = convert_mesh_points_to_text(source_mesh)

    pretransform = create_pretransform(config)
    for target_mesh_filename, target_mesh in target_meshes:
        target_point_file = convert_mesh_points_to_text(target_mesh)
        target_tri_file = convert_mesh_tris_to_text(target_mesh)

        cli_args = [
            f"./{bcpd}",
            f"-x{target_point_file}",
            f"-y{source_points_file}",
            f"-u{config.nrm}",
            f"-Ggeodesic,{config.tau},{target_tri_file}",
            "-p",
            "-h",
        ]
        for key, value in CLI_LUT.items():
            param = getattr(config, key)
            if param is not None:
                cli_args.append(f"{value}{param}")

        # Run the command
        subprocess.run(" ".join(cli_args), shell=True)

        mapped_mesh = map_source_mesh(source_mesh)
        mapped_mesh = transform_polydata(mapped_mesh, pretransform)
        mapped_mesh_path = output_dir.joinpath(f"mapped_{target_mesh_filename.stem}.vtp")
        save_vtp(mapped_mesh, mapped_mesh_path)

        if config.extract_insertions:
            insertion_points = extract_insertion_points(mapped_mesh)
            insertion_points_path = output_dir.joinpath("insertions_points.vtp")
            save_vtp(insertion_points, insertion_points_path)

        for f in ("output_info.txt", "output_comptime.txt", "output_y.txt"):
            filepath = Path(f)
            if filepath.exists() and filepath.is_file():
                filepath.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Processes polygon surfaces -- subdivision, mapping insertion points (from text files) to refined mesh, mirroring, and centering."
    )

    parser.add_argument("config", type=str, help="JSON configuration file")
    args = parser.parse_args()
    with open(args.config, "r") as f:
        config = GBCPDConfig(**json.load(f))
    main(config)

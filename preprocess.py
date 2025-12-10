import argparse
import json
from pathlib import Path
from typing import Literal

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import numpy_to_vtk

from config import PreprocessConfig
from utils import read_stl, read_vtp, save_json, save_vtp


def refine_mesh(poly: vtk.vtkPolyData, subdivisions: int) -> vtk.vtkPolyData:
    refine = vtk.vtkLoopSubdivisionFilter()
    refine.SetInputData(poly)
    refine.SetNumberOfSubdivisions(subdivisions)
    refine.Update()
    return refine.GetOutput()


def get_mirror_transform(axis: Literal["x", "y", "z"]) -> vtk.vtkTransform:
    mirror = vtk.vtkTransform()
    mirror.Scale(-1 if axis == "x" else 1, -1 if axis == "y" else 1, -1 if axis == "z" else 1)
    return mirror


def get_center_transform(poly: vtk.vtkPolyData) -> vtk.vtkTransform:
    center = vtk.vtkCenterOfMass()
    center.SetInputData(poly)
    center.Update()
    center_point = center.GetCenter()
    translate = vtk.vtkTransform()
    translate.Translate(-center_point[0], -center_point[1], -center_point[2])
    return translate


def apply_transform(poly: vtk.vtkPolyData, transform: vtk.vtkTransform) -> vtk.vtkPolyData:
    transform_filter = vtk.vtkTransformPolyDataFilter()
    transform_filter.SetInputData(poly)
    transform_filter.SetTransform(transform)
    transform_filter.Update()
    return transform_filter.GetOutput()


def save_transform(transform: vtk.vtkTransform, filename: Path):
    tx_mat = transform.GetMatrix()
    tx_numpy = np.zeros((4, 4), dtype=np.float64)
    for i in range(4):
        for j in range(4):
            tx_numpy[i, j] = tx_mat.GetElement(i, j)
    np.save(filename, tx_numpy)


def project_points(points: np.ndarray, locator: vtk.vtkStaticPointLocator) -> np.ndarray:
    point_ids = np.zeros(points.shape[0], dtype=int)
    for i in range(points.shape[0]):
        point_ids[i] = locator.FindClosestPoint(list(points[i, :]))
    return point_ids


def define_ligament_insertions(bone_poly: vtk.vtkPolyData, ligament_insertions: dict[str, str]) -> dict[int, str]:
    """
    Define ligament insertions on the bone polydata by projecting points specified in text files.

    :param bone_poly: The bone polydata.
    :type bone_poly: vtk.vtkPolyData
    :param ligament_insertions: A dictionary mapping ligament names to text filepaths.
    :type ligament_insertions: dict[str, str]

    :return:
        A dictionary mapping insertion IDs to ligament names. InsertionID array is
        added to the bone_poly inplace.
    :rtype: dict[int, str]
    """
    locator = vtk.vtkStaticPointLocator()
    locator.SetDataSet(bone_poly)
    locator.BuildLocator()
    insertion_ids = np.zeros(bone_poly.GetNumberOfPoints(), dtype=int)
    ligament_lut = {}
    for i, ligament in enumerate(sorted(ligament_insertions.keys())):
        insertions = np.genfromtxt(Path(ligament_insertions[ligament]).as_posix(), delimiter=",", usecols=[1, 2, 3])
        point_ids = project_points(insertions, locator)
        insertion_ids[point_ids] = i + 1
        ligament_lut[i + 1] = ligament
    if ligament_lut:
        insertion_id_array = numpy_to_vtk(insertion_ids, deep=True, array_type=vtk.VTK_ID_TYPE)
        insertion_id_array.SetName("InsertionID")
        insertion_id_array.SetNumberOfComponents(1)
        bone_poly.GetPointData().AddArray(insertion_id_array)
    return ligament_lut


def main(config: PreprocessConfig):
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if Path(config.bone).suffix == ".stl":
        bone_poly = read_stl(Path(config.bone))
    elif Path(config.bone).suffix == ".vtp":
        bone_poly = read_vtp(Path(config.bone))
    else:
        raise ValueError(f"Unsupported file format: {Path(config.bone).suffix}")
    if config.subdivisions > 0:
        bone_poly = refine_mesh(bone_poly, config.subdivisions)
    ligament_lut = {}
    if config.ligament_insertions is not None:
        ligament_lut = define_ligament_insertions(bone_poly, config.ligament_insertions)
    transform_list = []
    if config.mirror:
        transform_list.append(get_mirror_transform(config.mirror_axis))
    transform_list.append(get_center_transform(bone_poly))
    composite_transform = vtk.vtkTransform()
    for transform in transform_list:
        composite_transform.Concatenate(transform)
    bone_poly = apply_transform(bone_poly, composite_transform)
    save_transform(composite_transform, output_dir.joinpath("transform.npy"))

    # Save the refined mesh with insertion IDs
    save_vtp(bone_poly, output_dir.joinpath("mesh.vtp"))
    if ligament_lut:
        # Save the ligament ID lookup table as json
        save_json(ligament_lut, output_dir.joinpath("ligament_ids.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Processes polygon surfaces -- subdivision, mapping insertion points (from text files) to refined mesh, mirroring, and centering."
    )

    parser.add_argument("config", type=str, help="JSON configuration file")
    args = parser.parse_args()
    with open(args.config, "r") as f:
        config = PreprocessConfig(**json.load(f))

    main(config)

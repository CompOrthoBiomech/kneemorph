import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util import numpy_support


@dataclass
class AugmentConfig:
    base_mesh_file: str
    output_dir: str | None = None
    control_point_perturbation: float = 0.1
    num_perturbations: int = 10
    seed: int = 42


def read_mesh(file_path: str) -> vtk.vtkPolyData:
    assert file_path.endswith(".vtp"), "Only VTK XML polydata (.vtp) files are supported"
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(file_path)
    reader.Update()
    return reader.GetOutput()


def center_mesh(poly: vtk.vtkPolyData) -> vtk.vtkPolyData:
    center = vtk.vtkCenterOfMass()
    center.SetInputData(poly)
    center.Update()
    center_point = center.GetCenter()
    translate = vtk.vtkTransform()
    translate.Translate(-center_point[0], -center_point[1], -center_point[2])
    transform = vtk.vtkTransformPolyDataFilter()
    transform.SetInputData(poly)
    transform.SetTransform(translate)
    transform.Update()
    return transform.GetOutput()


def elastic_deformation(mesh: vtk.vtkPolyData, control_point_perturbation: float, num_perturbations: int, seed: int):
    obb = vtk.vtkOBBTree()
    obb.SetDataSet(mesh)
    obb.BuildLocator()

    corner = [0.0, 0.0, 0.0]
    max = [0.0, 0.0, 0.0]
    mid = [0.0, 0.0, 0.0]
    min = [0.0, 0.0, 0.0]
    size = [0.0, 0.0, 0.0]
    obb.ComputeOBB(mesh, corner, max, mid, min, size)
    control_point_perturbation = control_point_perturbation * size[2]

    poly = vtk.vtkPolyData()
    obb.GenerateRepresentation(0, poly)

    source_landmarks = poly.GetPoints()
    source_array = numpy_support.vtk_to_numpy(source_landmarks.GetData())
    new_meshes = []
    for i in range(num_perturbations):
        rand_normals = np.random.uniform(low=0, high=1, size=(8, 3))
        rand_normals /= np.linalg.norm(rand_normals, axis=1, keepdims=True)
        scale = np.random.uniform(0.0, control_point_perturbation, size=(8, 1))
        perturbation = rand_normals * scale
        target_array = source_array + perturbation
        target_landmarks = vtk.vtkPoints()
        target_landmarks.SetData(numpy_support.numpy_to_vtk(target_array, deep=True, array_type=vtk.VTK_DOUBLE))

        tps = vtk.vtkThinPlateSplineTransform()
        tps.SetSourceLandmarks(source_landmarks)
        tps.SetTargetLandmarks(target_landmarks)
        tps.SetBasisToR()
        tps.Update()

        txp = vtk.vtkTransformPolyDataFilter()
        txp.SetInputData(mesh)
        txp.SetTransform(tps)
        txp.Update()

        new_meshes.append(center_mesh(txp.GetOutput()))

    return new_meshes


def main(config):
    if config.output_dir is None:
        output_dir = Path(config.base_mesh_file).parent.joinpath("augmented_meshes")
    else:
        output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assert Path(config.base_mesh_file).exists(), f"Base mesh file {config.base_mesh_file} does not exist"
    mesh = read_mesh(config.base_mesh_file)
    augmented_meshes = elastic_deformation(mesh, config.control_point_perturbation, config.num_perturbations, config.seed)
    padding = int(np.log10(config.num_perturbations))
    for i, augmented_mesh in enumerate(augmented_meshes):
        output_path = output_dir.joinpath(f"mesh_{i:0{padding}d}.vtp")
        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetFileName(output_path.as_posix())
        writer.SetInputData(augmented_mesh)
        writer.Write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Elastically deforms provided base mesh into provided number of augmented meshes.")

    parser.add_argument("config", type=str, help="JSON configuration file")
    args = parser.parse_args()
    with open(args.config, "r") as f:
        config = AugmentConfig(**json.load(f))

    main(config)

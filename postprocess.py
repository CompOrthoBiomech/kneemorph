import argparse
import json
from pathlib import Path

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from config import PostValidationConfig


def read_mesh(file_path: Path) -> vtk.vtkPolyData:
    assert file_path.suffix == (".vtp"), "Only VTK XML polydata (.vtp) files are supported"
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(file_path.as_posix())
    reader.Update()
    return reader.GetOutput()


def _get_insertion_lut(mesh: vtk.vtkPolyData) -> dict[int, np.ndarray]:
    insertion_ids = mesh.GetPointData().GetArray("InsertionID")
    insertion_ids = vtk_to_numpy(insertion_ids)
    unique_ids = sorted(list(np.unique(insertion_ids)))
    insertion_lut = {}
    for id in unique_ids[1:]:
        insertion_lut[id] = np.argwhere(insertion_ids == id).ravel()
    return insertion_lut


def _get_displacement_error(
    truth_mesh: vtk.vtkPolyData, result_mesh: vtk.vtkPolyData, insertion_lut: dict[int, np.ndarray]
) -> dict[int, np.ndarray]:
    truth_points = vtk_to_numpy(truth_mesh.GetPoints().GetData())
    result_points = vtk_to_numpy(result_mesh.GetPoints().GetData())
    errors = {}
    for ligament_id, node_ids in insertion_lut.items():
        errors[ligament_id] = np.linalg.norm(truth_points[node_ids] - result_points[node_ids], axis=1).reshape(1, -1)
    return errors


def _get_pointwise_stats(errors: dict[int, np.ndarray]):
    pointwise_stats = []
    for ligament_id, error in errors.items():
        pointwise_stats.append(
            [ligament_id, np.mean(error, axis=0), np.std(error, axis=0), np.std(error, axis=0) / np.sqrt(error.shape[0]) * 1.96]
        )
    return pointwise_stats


def _get_aggregate_stats(errors: dict[int, np.ndarray]):
    aggregate_stats = []
    for ligament_id, error in errors.items():
        flattened_error = error.ravel()
        aggregate_stats.append(
            [ligament_id, np.mean(flattened_error), np.std(flattened_error), np.std(flattened_error) / np.sqrt(error.shape[0]) * 1.96]
        )
    return aggregate_stats


def visualize_error(mesh: vtk.vtkPolyData, summary_stats: list[list[np.ndarray]]) -> vtk.vtkPolyData:
    points = vtk_to_numpy(mesh.GetPoints().GetData())
    point_ids = mesh.GetPointData().GetArray("InsertionID")
    appended_polydata = vtk.vtkAppendPolyData()
    for stat in summary_stats:
        id, mean, _, std_err = stat
        coords = points[point_ids == id]
        id_array = numpy_to_vtk(np.full(coords.shape[0], id, dtype=int), deep=True, array_type=vtk.VTK_ID_TYPE)
        id_array.SetName("InsertionID")
        mean_array = numpy_to_vtk(mean, deep=True, array_type=vtk.VTK_FLOAT)
        mean_array.SetName("Mean")
        ci_array = numpy_to_vtk(mean + std_err, deep=True, array_type=vtk.VTK_FLOAT)
        ci_array.SetName("Upper Confidence Interval Bound")
        poly = vtk.vtkPolyData()
        poly_points = vtk.vtkPoints()
        poly_cells = vtk.vtkCellArray()
        for i in range(coords.shape[0]):
            poly_points.InsertNextPoint(coords[i])
            poly_cells.InsertNextCell(1, [i])
        poly.SetPoints(poly_points)
        poly.SetVerts(poly_cells)
        poly.GetPointData().AddArray(id_array)
        poly.GetPointData().AddArray(mean_array)
        poly.GetPointData().AddArray(ci_array)
        appended_polydata.AddInputData(poly)
    appended_polydata.Update()

    return appended_polydata.GetOutput()


def main(config: PostValidationConfig):
    output_dir = Path(config.output_dir)
    template_mesh_path = Path(config.template_mesh_file)
    ground_truth_path = Path(config.ground_truth_path)
    result_path = Path(config.result_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    truth_mesh_paths = sorted(list(ground_truth_path.glob("*.vtp")))
    result_mesh_paths = sorted(list(result_path.glob("*.vtp")))
    assert len(truth_mesh_paths) == len(result_mesh_paths), "Number of ground truth and result meshes must match"
    all_displacement_errors = {}
    for i, (truth_mesh_path, result_mesh_path) in enumerate(zip(truth_mesh_paths, result_mesh_paths)):
        truth_mesh = read_mesh(truth_mesh_path)
        result_mesh = read_mesh(result_mesh_path)
        if i == 0:
            insertion_lut = _get_insertion_lut(truth_mesh)
        displacement_errors = _get_displacement_error(truth_mesh, result_mesh, insertion_lut)  # pyright: ignore[reportPossiblyUnboundVariable]
        for key, value in displacement_errors.items():
            try:
                all_displacement_errors[key].append(value)
            except KeyError:
                all_displacement_errors[key] = [value]
    all_displacement_errors = {key: np.concatenate(value, axis=0) for key, value in all_displacement_errors.items()}
    pointwise_stats = _get_pointwise_stats(all_displacement_errors)
    aggregate_stats = _get_aggregate_stats(all_displacement_errors)
    np.savetxt(str(output_dir / "displacement_errors.csv"), aggregate_stats, delimiter=",", header="ID, Mean, STD, CI Upper Bound")
    template_mesh = read_mesh(template_mesh_path)
    stats_polydata = visualize_error(template_mesh, pointwise_stats)
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(str(output_dir / "error_visualization.vtp"))
    writer.SetInputData(stats_polydata)
    writer.Write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post-process validation set to assess error.")
    parser.add_argument("config", type=str, help="Path to the configuration file.")
    args = parser.parse_args()
    with open(args.config, "r") as f:
        config = PostValidationConfig(**json.load(f))
    main(config)

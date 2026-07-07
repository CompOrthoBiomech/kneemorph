import argparse
from pathlib import Path

import numpy as np
import vtkmodules.all as vtk
from vtkmodules.util import numpy_support


def main(points_path: Path, tris_path: Path, output_path: Path):
    points = np.loadtxt(points_path, dtype=np.float32)
    tris = np.loadtxt(tris_path, dtype=np.int32)
    if np.min(tris, axis=0).min() == 1:
        tris -= 1

    points_vtk = vtk.vtkPoints()
    points_vtk.SetData(numpy_support.numpy_to_vtk(points, deep=True, array_type=vtk.VTK_FLOAT))

    tris_array = np.hstack([np.full((tris.shape[0], 1), 3, dtype=int), tris]).ravel()
    vtk_tris = vtk.vtkCellArray()
    vtk_tris.SetCells(
        tris_array.size // 4,
        numpy_support.numpy_to_vtk(tris_array, deep=True, array_type=vtk.VTK_ID_TYPE),
    )

    poly = vtk.vtkPolyData()
    poly.SetPoints(points_vtk)
    poly.SetPolys(vtk_tris)

    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(output_path.as_posix())
    writer.SetInputData(poly)
    writer.Write()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-points", type=str, help="Path to the points file")
    parser.add_argument("-tris", type=str, help="Path to the triangles file")
    parser.add_argument("-output", type=str, help="Path to the output file")
    args = parser.parse_args()
    points_path = Path(args.points)
    tris_path = Path(args.tris)
    output_path = Path(args.output)
    main(points_path, tris_path, output_path)

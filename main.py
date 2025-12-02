import numpy as np
import SimpleITK as sitk
import vtkmodules.all as vtk
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy


def read_stl(filename) -> vtk.vtkPolyData:
    reader = vtk.vtkSTLReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()


def vtk_to_sitk_image(image: vtk.vtkImageData, reference_image: sitk.Image) -> sitk.Image:
    spacing = image.GetSpacing()
    origin = image.GetOrigin()
    size = image.GetDimensions()
    data = vtk_to_numpy(image.GetPointData().GetScalars())
    data = data.reshape(size[2], size[1], size[0])
    sitk_image = sitk.GetImageFromArray(data)
    sitk_image.SetSpacing(spacing)
    sitk_image.SetOrigin([-origin[0], -origin[1], origin[2]])
    return sitk_image


def polydata_to_stencil(poly: vtk.vtkPolyData, image: sitk.Image) -> vtk.vtkImageData:
    bounds = poly.GetBounds()
    origin = [bounds[0], bounds[2], bounds[4]]
    spacing = image.GetSpacing()
    size = [int((bounds[2 * i + 1] - bounds[2 * i]) / spacing[i] + 0.5) for i in range(3)]

    white_image = vtk.vtkImageData()
    white_image.SetOrigin(origin)
    white_image.SetSpacing(spacing)
    white_image.SetDimensions(size)
    white_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

    scalars = numpy_to_vtk(np.full(white_image.GetNumberOfPoints(), 255, dtype=np.uint8), deep=True)
    white_image.GetPointData().SetScalars(scalars)

    poly2stencil = vtk.vtkPolyDataToImageStencil()
    poly2stencil.SetInputData(poly)
    poly2stencil.SetOutputSpacing(spacing)
    poly2stencil.SetOutputOrigin(origin)
    poly2stencil.SetOutputWholeExtent(0, size[0], 0, size[1], 0, size[2])
    poly2stencil.Update()

    img_stencil = vtk.vtkImageStencil()
    img_stencil.SetInputData(white_image)
    img_stencil.SetStencilConnection(poly2stencil.GetOutputPort())
    img_stencil.ReverseStencilOff()
    img_stencil.SetBackgroundValue(0)
    img_stencil.Update()
    return img_stencil.GetOutput()


def main():
    reader = sitk.ImageSeriesReader()
    filenames = reader.GetGDCMSeriesFileNames("DU02/DU02_fs_SAG")
    reader.SetFileNames(filenames)
    image = reader.Execute()
    image = sitk.CurvatureAnisotropicDiffusion(sitk.Cast(image, sitk.sitkFloat32), timeStep=0.01, numberOfIterations=20)
    direction = image.GetDirection()
    origin = image.GetOrigin()

    femur = read_stl("DU02/DU02_probes_3D_recons/DU02_Fem_Bone.stl")

    tibia = read_stl("DU02/DU02_probes_3D_recons/DU02_Tib_Bone.stl")

    tx = np.eye(4)
    tx[0:3, 0:3] = np.array(direction).reshape(3, 3)
    tx[0:3, 3] = np.array(origin)
    tx = np.linalg.inv(tx)
    tx[0:3, 3] += np.array([-origin[0], -origin[1], origin[2]])

    mask = sitk.Image(image)
    for bone, name in zip([femur, tibia], ["femur", "tibia"]):
        transform = vtk.vtkTransform()
        transform.SetMatrix(tx.ravel())
        tx_stl = vtk.vtkTransformPolyDataFilter()
        tx_stl.SetInputData(bone)
        tx_stl.SetTransform(transform)
        tx_stl.Update()

        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetFileName(f"{name}.vtp")
        writer.SetInputData(tx_stl.GetOutput())
        writer.Write()

        stencil = vtk_to_sitk_image(polydata_to_stencil(tx_stl.GetOutput(), image), image)
        sitk.WriteImage(stencil, f"{name}_stencil.nii")

    sitk.WriteImage(image, "output.nii")


if __name__ == "__main__":
    main()

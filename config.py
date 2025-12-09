from dataclasses import dataclass
from typing import Literal


@dataclass
class AugmentConfig:
    base_mesh_file: str
    output_dir: str | None = None
    control_point_perturbation: float = 0.1
    num_perturbations: int = 10
    seed: int = 42


@dataclass
class PostValidationConfig:
    template_mesh_file: str
    ground_truth_path: str
    result_path: str
    output_dir: str


@dataclass
class PreprocessConfig:
    bone: str
    ligament_insertions: dict[str, str]
    output_dir: str
    subdivisions: int = 0
    mirror: bool = False
    mirror_axis: Literal["x", "y", "z"] = "x"


@dataclass
class GBCPDConfig:
    """
    :param source_mesh_file: Path to source mesh file
    :type source_mesh_file: str
    :param target_mesh_path: Path to target mesh file or directory containing multiple target meshes
    :type target_mesh_path: str
    :param output_dir: Path to output directory
    :type output_dir: str
    :param extract_insertions: Whether to extract ligament insertion points as a separate file
    :type extract_insertions: bool
    :param omega: Outlier probability (0,1)
    :type omega: float
    :param lambda_: Controls expected length of deformation vectors. Smaller is longer.
    :type lambda_: float
    :param beta: Weight of the regularization term
    :type beta: float
    :param gamma: Weight controlling bias towards initial alignment
    :type gamma: float
    :param kappa: Weight controlling randomness of mixing coefficients (if None all mixing coefficients are equal)
    :type kappa: float | None
    :param nrm: Normalization method for deformation vectors: "x" (target) or "y" (source)
    :type nrm: Literal["x", "y"]
    :param K: Number of samples for computing G in Nystrom method
    :type K: int
    :param J: Number of samples for computing P in Nystrom method
    :type J: int
    :param r: Random seed for Nystrom method. Reproducibility is guaranteed if r has same value.
    :type r: int | None

    :param c: Convergence tolerance
    :type c: float
    :param n_max: Maximum number of VB loops
    :type n_max: int
    :param n_min: Minimum number of VB loops
    :type n_min: int

    :param tau: Weight controlling balance between geodesic and Gaussian kernels
    :type tau: float

    """

    source_mesh_file: str
    target_mesh_path: str
    output_dir: str
    pretransform_file: str | None = None
    extract_insertions: bool = True
    omega: float = 0.0
    beta: float = 1.2
    lambda_: float = 50
    gamma: float = 0.1
    kappa: float | None = None
    nrm: Literal["x", "y"] = "x"
    K: int = 300
    J: int = 300
    r: int | None = 42
    c: float = 1e-6
    n_max: int = 500
    n_min: int = 30
    tau: float = 0.5

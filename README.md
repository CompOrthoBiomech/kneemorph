## Description
kneemorph contains CLI applications for registering a template mesh to target mesh(es) for the purpose of
automatic ligament insertion point assignment.

## Installation

### Python Package

If `uv` is not installed, install with:

**On Linux or macOS:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

From the kneemorph directory, run:

```bash
uv sync
```

This will fetch the required Python (or create a symlink if you have already) and dependencies and create a virtual environment.

### geodesic-based Bayesian coherent point drift binary

**On Windows:**

A statically linked binary can be downloaded from [here](https://raw.githubusercontent.com/CompOrthoBiomech/bcpd/master/win/bcpd.exe).

**On Linux:**

A binary will need to be built from source:

Ensure you have the GCC compiler installed:

On Debian-based systems:

```bash
sudo apt install build-essential
```

You may also need the `OpenMP` header files:

```bash
sudo apt install libomp-dev
```

and/or the `OpenBLAS` header files:

```bash
sudo apt install libopenblas-dev
```

Clone the repository into a reasonable directory above `kneemorph`:

```bash
git clone https://github.com/CompOrthoBiomech/bpcd.git
cd bpcd
make
```

which will create a binary `bpcd` in the top-level directory

Move this to the top-level of the kneemorph repository:

```bash
mv bpcd /path/to/kneemorph
```

**On macOS:**

A binary will need to be built from source:

Install `Xcode`, `Xcode command line tools` from the App Store.

Install `Homebrew`:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install `OpenMP` and `OpenBLAS` with `Homebrew`:

```bash
brew install libomp openblas
```

Clone the repository into a reasonable directory above `kneemorph`:

```bash
git clone https://github.com/CompOrthoBiomech/bpcd.git
cd bpcd
make
```

which will create a binary `bpcd` in the top-level directory

Move this to the top-level of the kneemorph repository:

```bash
mv bpcd /path/to/kneemorph
```

## Usage

### Data for studies

The provided configuration files in the `studies/` directory utilize the Natural Knee Data from
the University of Denver. Download the zipped data from:

[DU02](https://digitalcommons.du.edu/cgi/viewcontent.cgi?filename=3&article=1001&context=natural_knee_data&type=additional)

[DU03](https://digitalcommons.du.edu/cgi/viewcontent.cgi?filename=3&article=1002&context=natural_knee_data&type=additional)

[DU04](https://digitalcommons.du.edu/cgi/viewcontent.cgi?filename=2&article=1003&context=natural_knee_data&type=additional)

[DU05](https://digitalcommons.du.edu/cgi/viewcontent.cgi?filename=2&article=1004&context=natural_knee_data&type=additional)

To utilize the configuration files without modification,

create a `dat/` directory in the top-level of the kneemorph repository:

```bash
mkdir dat
```

and unzip each downloaded dataset into the `dat/` directory:

```bash
unzip DU02.zip -d dat/
unzip DU03.zip -d dat/
unzip DU04.zip -d dat/
unzip DU05.zip -d dat/
```

### preprocess.py

This script preprocesses a mesh and insertion point text files (if provided) for later registration.
It takes a single command-line argument: the path to a configuration file in JSON defining a PreprocessConfig object.

The `PreprocessConfig` class:

```python
@dataclass
class PreprocessConfig:
    bone: str
    ligament_insertions: dict[str, str] | None = None
    output_dir: str
    subdivisions: int = 0
    mirror: bool = False
    mirror_axis: Literal["x", "y", "z"] = "x"
```

Example JSON configuration file [here](studies/du02_to_du03/du03_preprocess.json) 

### register.py

This script registers the template mesh to the target mesh using the geodesic-based Bayesian coherent point drift (GBCPD) algorithm. It takes a single command-line argument: the path to a configuration file in JSON defining a `GBCPDConfig` object.

The `GBCPDConfig` class:

```python
@dataclass
class GBCPDConfig:
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
```

Example JSON configuration file [here](studies/du02_to_du03/du03_register.json)

## Validation

### augment.py

This script creates a validation set of N target meshes by deforming a template mesh with random thin-plate spline transforms. It takes a single command-line argument: the path to a configuration file in JSON defining an `AugmentConfig` object.

The `AugmentConfig` class:

```python
@dataclass
class AugmentConfig:
    base_mesh_file: str
    output_dir: str | None = None
    control_point_perturbation: float = 0.1
    num_perturbations: int = 10
    seed: int = 42
```

Example JSON configuration file [here](studies/du02_validation/du02_augment.json)

### postprocess.py

This script evaluates the validation set by comparing the registered meshes to the ground truth augmented meshes. It takes a single command-line argument: the path to a configuration file in JSON defining an `PostValidationConfig` object.

The `PostValidationConfig` class:

```python
@dataclass
class PostValidationConfig:
    template_mesh_file: str
    ground_truth_path: str
    result_path: str
    output_dir: str
```

## An Example Validation Study

The following steps are executed in a validation study:

1. Run `preprocess.py` to preprocess the template mesh.
2. Run `augment.py` to create a validation set of N specified target meshes.
3. Run `register.py` to register the template mesh to the target meshes.
4. Run `postprocess.py` to evaluate the registration results.

### 1. Preprocess

```bash
uv run studies/du02_validation/du02_preprocess.json
```

This will create `dat/processed/DU02/femur` as indicated in the configuration file, and
save:

- `mesh.vtp` - The preprocessed mesh file.
- `ligament_insertions.json` - Dictionary mapping ligament integer labels to user-indicated string names.
- `transform.npy` - The transformation matrix used to center (and mirror if `mirror=True`) the raw mesh.

### 2. Augment

```bash
uv run studies/du02_validation/du02_augment.json
```

This will create `dat/augmented/DU02/femur` as indicated in the configuration file, and
save:

- `mesh00.vtp` .. `mesh99.vtp` - 100 augmented meshes as indicated in configuration.

### 3. Register

```bash
uv run studies/du02_validation/du02_register.json
```

This will create `sol/DU02_validation/mapped` as indicated in the configuration file, and
save:

- `mapped_mesh_00.vtp` .. `mapped_mesh_99.vtp` - The template mesh registered 100 augmented target mesh files.

### 4. Postprocess

```bash
uv run studies/du02_validation/du02_postprocess.json
```

This will create `sol/DU02_validation/postprocessed` as indicated in the configuration file, and
save:

- `error_visualization.vtp` - A point cloud represented as VTK polydata with the `LigamentID`, `Mean` distance error (mm), and  `Upper Confidence Interval Bound` distance error (mm) for visualization.
- `distance_errors.csv` - CSV file containing the `LigamentID`, `Mean` distance error (mm), `Standard Deviation` of distance error (mm), and `Upper Confidence Interval Bound` distance error (mm) aggregated per ligament.

## An Example Template to Target Registration

The process for template to target registration is as follows:

1. Preprocess the template mesh (if not already done).
2. Preprocess the target mesh.
4. Perform the registration.

### 1. Preprocess Template Mesh

```bash
uv run studies/du02_validation/du02_preprocess.json
```

### 2. Preprocess Target Mesh

```bash
uv run studies/du02_to_du03/du03_preprocess.json
```

### 3. Register

```bash
uv run studies/du02_to_du03/du03_register.json
```

The results will be saved in `sol/DU02_to_DU03` as indicated in the configuration file with the following files:

- `mapped_mesh.vtp` - The mapped template mesh. The triangles will likely be degenerate for this. Inspecting the point cloud is recommended.
- `insertion_points.vtp` - The insertion points as a point cloud with `LigamentID` stored.

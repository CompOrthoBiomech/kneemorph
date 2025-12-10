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

### preprocess.py

This script preprocesses a mesh and insertion point text files (if provided) for later registration.
It takes a single command-line argument: the path to a configuration file in JSON defining a PreprocessConfig object.

The `PreprocessConfig` class:

```python
@dataclass
class PreprocessConfig:
    bone: str
    ligament_insertions: dict[str, str]
    output_dir: str
    subdivisions: int = 0
    mirror: bool = False
    mirror_axis: Literal["x", "y", "z"] = "x"
```

Example JSON configuration file [here](studies/du02_validation/du02_preprocess.json) 

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

Example JSON configuration file [here](studies/du02_validation/du02_register.json)

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

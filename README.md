## Description
kneemorph contains CLI applications for registering a template mesh to target mesh(es) for the purpose of
automatic ligament insertion point assignment.

## Installation

### Python Package

If `uv` is not installed, install with:

On Linux or macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

From the kneemorph directory, run:

```bash
uv sync
```

This will fetch the required Python (or create a symlink if you have already) and dependencies and create a virtual environment.

### geodesic-based Bayesian coherent point drift binary

On Windows:

A statically linked binary can be downloaded from [here](https://raw.githubusercontent.com/CompOrthoBiomech/bpcd/master/win/bpcd.exe).

On Linux:

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

## Usage

### preprocess.py

This script preprocesses a mesh for later registration.

### register.py

This script registers the template mesh to the target mesh using the geodesic-based Bayesian coherent point drift (GBCPD) algorithm.

## Validation

### augment.py

This script creates a validation set of N target meshes by deforming a template mesh with random thin-plate spline transforms.

### postprocess.py

This script evaluates the validation set by comparing the registered meshes to the ground truth augmented meshes.

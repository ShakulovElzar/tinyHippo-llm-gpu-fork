"""Simulator backend layer (S0 shim).

Model code calls the simulator only through this module:

    import simbackend as sim
    pop = sim.Create("izhikevich", 100, params=p)
    sim.Connect(pop, pop, conn_spec, syn_spec)

The one backend today is "nest" (CPU NEST, the reference). Every function
passes its arguments unchanged to PyNEST, so a run at a fixed seed and thread
count gives a bit-identical HDF5 file (S0 gate). A "nestgpu" backend (S1)
adds a second implementation of the same names.

Each function looks up the NEST function at call time, not at import time.
reconstruct_connectivity.py replaces nest.Simulate at runtime and needs this.

Objects that NEST returns (NodeCollection, SynapseCollection) are passed back
unchanged, so their own methods (.get, .set, .tolist, slicing) still go to
NEST directly. The NEST GPU backend must give the same behaviour.
"""

import nest as _nest

BACKENDS = ("nest",)
backend = "nest"


def use(name):
    """Select the backend. Only "nest" exists until S1."""
    global backend
    if name not in BACKENDS:
        raise ValueError(f"unknown backend {name!r}; choose from {BACKENDS}")
    backend = name


def version():
    return _nest.__version__


# Classes and parameter modules, passed through unchanged so that
# isinstance() checks and NEST parameter expressions (sim.random.uniform,
# sim.math.max) work exactly as before.
NodeCollection = _nest.NodeCollection
SynapseCollection = _nest.SynapseCollection
random = _nest.random
math = _nest.math


# Kernel
def ResetKernel(*args, **kwargs):
    return _nest.ResetKernel(*args, **kwargs)


def SetKernelStatus(*args, **kwargs):
    return _nest.SetKernelStatus(*args, **kwargs)


def GetKernelStatus(*args, **kwargs):
    return _nest.GetKernelStatus(*args, **kwargs)


def Models(*args, **kwargs):
    return _nest.Models(*args, **kwargs)


def node_models():
    """List of node models. Raises AttributeError on NEST versions without it."""
    return _nest.node_models


# Network construction
def Create(*args, **kwargs):
    return _nest.Create(*args, **kwargs)


def Connect(*args, **kwargs):
    return _nest.Connect(*args, **kwargs)


def GetConnections(*args, **kwargs):
    return _nest.GetConnections(*args, **kwargs)


# Parameters and state
def SetStatus(*args, **kwargs):
    return _nest.SetStatus(*args, **kwargs)


def GetStatus(*args, **kwargs):
    return _nest.GetStatus(*args, **kwargs)


# Simulation
def Simulate(*args, **kwargs):
    return _nest.Simulate(*args, **kwargs)

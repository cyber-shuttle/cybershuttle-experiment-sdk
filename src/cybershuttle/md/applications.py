from ..base import Experiment, ExperimentApp, GUIApp


class NAMD(ExperimentApp):
    """
    Nanoscale Molecular Dynamics (NAMD, formerly Not Another Molecular Dynamics Program)
    is a computer software for molecular dynamics simulation, written using the Charm++
    parallel programming model (not to be confused with CHARMM).
    It is noted for its parallel efficiency and is often used to simulate large systems
    (millions of atoms). It has been developed by the collaboration of the Theoretical
    and Computational Biophysics Group (TCB) and the Parallel Programming Laboratory (PPL)
    at the University of Illinois Urbana–Champaign.

    """

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__(name, app_id="namd")

    @classmethod
    def initialize(
        cls,
        name: str,
        config_file: str,
        pdb_file: str,
        psf_file: str,
        other_files: list[str] = [],
    ) -> Experiment:
        app = cls(name)
        return Experiment(app).with_inputs(
            config_file=config_file,
            pdb_file=pdb_file,
            psf_file=psf_file,
            other_files=other_files,
        )


class VMD(GUIApp):
    """
    Visual Molecular Dynamics (VMD) is a molecular visualization and analysis program
    designed for biological systems such as proteins, nucleic acids, lipid bilayer assemblies,
    etc. It also includes tools for working with volumetric data, sequence data, and arbitrary
    graphics objects. VMD can be used to animate and analyze the trajectory of molecular dynamics
    simulations, and can interactively manipulate molecules being simulated on remote computers
    (Interactive MD).

    """

    def __init__(
        self,
        name: str,
    ) -> None:
        super().__init__(name, app_id="vmd")

    @classmethod
    def initialize(
        cls,
        name: str,
    ) -> GUIApp:
        app = cls(name)
        return app

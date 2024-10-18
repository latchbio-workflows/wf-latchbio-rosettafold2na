from typing import List

from latch.resources.launch_plan import LaunchPlan
from latch.resources.workflow import workflow
from latch.types.directory import LatchOutputDir
from latch.types.file import LatchFile
from latch.types.metadata import (
    LatchAuthor,
    LatchMetadata,
    LatchParameter,
    LatchRule,
    Params,
    Section,
    Text,
)

from wf.task import ChainType, SequenceTable, rosettafold2na_task

flow = [
    Section(
        "Inputs",
        Params(
            "sequence_table",
        ),
        Text("Input files for individual chains in the structure:"),
        Text("- Use 'Protein' for protein sequences"),
        Text("- Use 'RNA' for RNA sequences"),
        Text(
            "- Use 'Double stranded DNA' for double-stranded DNA (complementary strand will be automatically generated)"
        ),
        Text("- Use 'Single stranded DNA' for single-stranded DNA"),
        Text("- Use 'Paired Protein/RNA' for paired protein/RNA sequences"),
        Text("Each chain should be provided as a separate FASTA file."),
    ),
    Section(
        "Output",
        Params("run_name"),
        Text("Directory for outputs"),
        Params("output_directory"),
    ),
]


metadata = LatchMetadata(
    display_name="RosettaFold2NA",
    author=LatchAuthor(
        name="Minkyung Baek et al.",
    ),
    repository="https://github.com/latchbio-workflows/wf-latchbio-rosettafold2na",
    license="MIT",
    tags=["Protein Engineering"],
    parameters={
        "run_name": LatchParameter(
            display_name="Run Name",
            description="Name of run",
            batch_table_column=True,
            rules=[
                LatchRule(
                    regex=r"^[a-zA-Z0-9_-]+$",
                    message="Run name must contain only letters, digits, underscores, and dashes. No spaces are allowed.",
                )
            ],
        ),
        "sequence_table": LatchParameter(
            display_name="Chain Table",
            samplesheet=True,
            batch_table_column=True,
        ),
        "output_directory": LatchParameter(
            display_name="Output Directory",
            batch_table_column=True,
        ),
    },
    flow=flow,
)


@workflow(metadata)
def rosettafold2na_workflow(
    run_name: str,
    sequence_table: List[SequenceTable],
    output_directory: LatchOutputDir = LatchOutputDir("latch:///RosettaFold2NA"),
) -> LatchOutputDir:
    """
    RosettaFold2NA: Protein-Nucleic Acid Complex Structure Prediction

    <p align="center">
        <img src="https://media.springernature.com/lw1200/springer-static/image/art%3A10.1038%2Fs41592-023-02086-5/MediaObjects/41592_2023_2086_Fig1_HTML.png" width="800px"/>
    </p>

    <p align="center">
    <img src="https://user-images.githubusercontent.com/31255434/182289305-4cc620e3-86ae-480f-9b61-6ca83283caa5.jpg" alt="Latch Verified" width="100">
    </p>

    <p align="center">
    <strong>
    Latch Verified
    </strong>
    </p>

    ## Overview

    RosettaFold2NA is a state-of-the-art neural network that rapidly produces 3D structure models with confidence estimates for protein-DNA and protein-RNA complexes, as well as RNA tertiary structures.

    ## Key Features

    - Single trained network for multiple types of complexes
    - Rapid 3D structure model generation
    - Confidence estimates for predictions
    - Higher accuracy than current state-of-the-art methods for confident predictions
    - Capable of modeling protein-DNA complexes, protein-RNA complexes, and RNA tertiary structures

    ## Workflow Inputs

    Run Name: Name for the prediction run

    Sequence Table: List of chain types and corresponding input files
    - Protein sequences
    - RNA sequences
    - Double-stranded DNA sequences
    - Single-stranded DNA sequences
    - Paired protein/RNA sequences

    ## Workflow Outputs
    RosettaFold2NA generates the following output files:

    - PDB file with the predicted structure
    - B-factors represent estimated per-residue LDDT (local distance difference test)
    - Numpy .npz file containing confidence metrics

    ## Confidence Metrics

    - dist: Predicted distogram (L x L x 37, where L is the complex length)
    - lddt: Per-residue predicted LDDT
    - pae: Per-residue pair predicted error

    ## Credits
    Baek, M., McHugh, R., Anishchenko, I. et al.
    Accurate prediction of protein–nucleic acid complexes using RoseTTAFoldNA.
    Nat Methods 21, 117–121 (2024).
    https://doi.org/10.1038/s41592-023-02086-5

    """
    return rosettafold2na_task(
        run_name=run_name,
        sequence_table=sequence_table,
        output_directory=output_directory,
    )


LaunchPlan(
    rosettafold2na_workflow,
    "DNA Protein Example",
    {
        "run_name": "dna_protein_complex",
        "sequence_table": [
            SequenceTable(
                type=ChainType.protein,
                file=LatchFile(
                    "s3://latch-public/proteinengineering/rosettafold2na/protein_test.fa"
                ),
            ),
            SequenceTable(
                type=ChainType.doublestrand_dna,
                file=LatchFile(
                    "s3://latch-public/proteinengineering/rosettafold2na/dna_test.fa"
                ),
            ),
        ],
    },
)

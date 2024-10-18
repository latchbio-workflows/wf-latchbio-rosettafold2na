# RosettaFold2NA: Protein-Nucleic Acid Complex Structure Prediction

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

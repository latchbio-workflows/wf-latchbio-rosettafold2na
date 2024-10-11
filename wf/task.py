import functools
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List

from flytekit import task
from flytekitplugins.pod import Pod
from kubernetes.client.models import (
    V1Container,
    V1SecurityContext,
)
from latch.executions import rename_current_execution
from latch.functions.messages import message
from latch.resources.tasks import (
    _get_large_gpu_pod,
    get_v100_x1_pod,
)
from latch.types.directory import LatchOutputDir
from latch.types.file import LatchFile

sys.stdout.reconfigure(line_buffering=True)


def _add_privileged(x: Pod):
    containers = x.pod_spec.containers
    assert containers is not None
    assert len(containers) > 0
    container: V1Container = containers[0]

    container.security_context = V1SecurityContext(privileged=True)

    return x


privileged_large_gpu_task = functools.partial(
    task, task_config=_add_privileged(_get_large_gpu_pod())
)

privileged_v100_x1_gpu_task = functools.partial(
    task, task_config=_add_privileged(get_v100_x1_pod())
)


class ChainType(Enum):
    protein = "Protein"
    rna = "RNA"
    doublestrand_dna = "Double stranded DNA"
    singlestrand_dna_fasta = "Single stranded DNA"
    paired_protein_RNA = "Paired Protein/RNA"


@dataclass
class SequenceTable:
    type: ChainType
    file: LatchFile


@privileged_v100_x1_gpu_task(cache=True)
def rosettafold2na_task(
    run_name: str,
    sequence_table: List[SequenceTable],
    output_directory: LatchOutputDir = LatchOutputDir("latch:///RosettaFold2NA"),
) -> LatchOutputDir:
    rename_current_execution(str(run_name))

    print("-" * 60)
    print("Creating local directories")
    local_output_dir = Path(f"/root/outputs/{run_name}")
    local_output_dir.mkdir(parents=True, exist_ok=True)

    print("-" * 60)
    subprocess.run(["nvidia-smi"], check=True)
    subprocess.run(["nvcc", "--version"], check=True)

    print("-" * 60)
    print("Mounting ObjectiveFS")
    ofs_p = Path("ofs").resolve()
    ofs_p.mkdir(parents=True, exist_ok=True)

    mount_command = [
        "mount.objectivefs",
        "-o",
        "mtplus,noatime,nodiratime,noratelimit,freebw,hpc",
        "s3://objectivefs-proteintools/rosettafoldaa",
        str(ofs_p),
    ]

    subprocess.run(mount_command, check=True)

    max_wait_time = 15
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        if any(ofs_p.iterdir()):
            print("ObjectiveFS mounted successfully")
            break
        time.sleep(1)
    else:
        message("error", {"title": "ObjectiveFS Mount failed", "body": "Failed mount"})
        sys.exit(1)

    subprocess.run(f"ls -l {ofs_p}", shell=True, check=True)

    print("-" * 60)
    print("Linking databases")
    rosetta_dir = Path("/tmp/docker-build/work/RoseTTAFold2NA")
    symlinks = [
        ("RF2NA_weights/RF2NA_apr23.pt", "network/weights/RF2NA_apr23.pt"),
        ("UniRef30_2020_06", "UniRef30_2020_06"),
        ("bfd", "bfd"),
        ("pdb100_2021Mar03", "pdb100_2021Mar03"),
        ("RNA", "RNA"),
    ]

    print("Creating symlinks...")
    for source, target in symlinks:
        source_path = ofs_p / source
        target_path = rosetta_dir / target

        if not target_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.symlink_to(source_path)
            print(f"  Created: {target_path} -> {source_path}")

    print("Symlink creation complete.")

    subprocess.run(f"ls -l {rosetta_dir}", shell=True, check=True)

    print("-" * 60)
    print("Running RosettaFold2NA")

    command = [
        f"{rosetta_dir}/run_RF2NA.sh",
        f"{local_output_dir}",
    ]

    for seq in sequence_table:
        if seq.type == ChainType.protein:
            command.append(f"P:{seq.file.local_path}")
        elif seq.type == ChainType.rna:
            command.append(f"R:{seq.file.local_path}")
        elif seq.type == ChainType.doublestrand_dna:
            command.append(f"D:{seq.file.local_path}")
        elif seq.type == ChainType.singlestrand_dna_fasta:
            command.append(f"S:{seq.file.local_path}")
        elif seq.type == ChainType.paired_protein_RNA:
            command.append(f"PR:{seq.file.local_path}")

    print(f"Running command: {command}")

    # command = f"""
    #     source /opt/conda/bin/activate RF2NA && \
    #     {rosetta_dir}/run_RF2NA.sh {local_output_dir} P:/root/test/protein.fa D:/root/test/dna.fa
    # """

    try:
        subprocess.run(command, check=True)
        print("Done")
    except Exception as e:
        print("FAILED")
        message("error", {"title": "RosettaFold2NA failed", "body": f"{e}"})
        time.sleep(6000)

    print("Returning results")
    return LatchOutputDir(str("/root/outputs"), output_directory.remote_path)

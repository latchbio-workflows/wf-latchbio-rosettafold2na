import functools
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent
from typing import Optional

from flytekit import task
from flytekitplugins.pod import Pod
from kubernetes.client.models import (
    V1Container,
    V1SecurityContext,
)
from latch.executions import rename_current_execution
from latch.resources.tasks import (
    _get_large_gpu_pod,
    _get_small_gpu_pod,
    get_v100_x1_pod,
    small_gpu_task,
    v100_x1_task,
)
from latch.types.directory import LatchDir, LatchOutputDir
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

privileged_small_gpu_task = functools.partial(
    task, task_config=_add_privileged(_get_small_gpu_pod())
)

privileged_v100_x1_gpu_task = functools.partial(
    task, task_config=_add_privileged(get_v100_x1_pod())
)


@privileged_large_gpu_task(cache=True)
def task(
    run_name: str, input_file: LatchFile, output_directory: LatchOutputDir
) -> LatchOutputDir:
    rename_current_execution(str(run_name))

    print("-" * 60)
    print("Creating local directories")
    local_output_dir = Path(f"/root/outputs/{run_name}")
    local_output_dir.mkdir(parents=True, exist_ok=True)

    print("-" * 60)
    subprocess.run(["nvidia-smi"], check=True)
    subprocess.run(["nvcc", "--version"], check=True)

    print("Mounting ObjectiveFS")
    ofs_p = Path("ofs").resolve()
    ofs_p.mkdir(parents=True, exist_ok=True)

    passphrase_file = Path("/etc/objectivefs.env/PASSPHRASE")
    with passphrase_file.open() as f:
        passphrase = f.read().strip()

    mount_command = [
        "mount.objectivefs",
        "-o",
        "mtplus,noatime,nodiratime,noratelimit,freebw,hpc",
        "s3://objectivefs-proteintools/rosettafoldaa",
        str(ofs_p),
    ]

    subprocess.run(mount_command, check=True)

    # # Start the mount process in the background
    # process = subprocess.Popen(
    #     mount_command,
    #     stdin=subprocess.PIPE,
    #     stdout=subprocess.PIPE,
    #     stderr=subprocess.PIPE,
    #     text=True,
    # )

    # # Send the passphrase to the process
    # process.stdin.write(passphrase + "\n")
    # process.stdin.flush()

    # Wait for the mount to be established
    max_wait_time = 60  # Maximum wait time in seconds
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        if any(ofs_p.iterdir()):
            print("ObjectiveFS mounted successfully")
            break
        time.sleep(1)
    else:
        print("Error: ObjectiveFS mount timed out")
        sys.exit(1)

    subprocess.run(f"ls -l {ofs_p}", shell=True, check=True)

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

    print("Running RosettaFold2NA")
    # command = [
    #     "/root/miniconda/bin/conda",
    #     "run",
    #     "-n",
    #     "RF2NA",
    #     f"{rosetta_dir}/run_RF2NA.sh",
    #     f"{local_output_dir}",
    #     f"P:{rosetta_dir}/example/rna_binding_protein.fa",
    #     f"R:{rosetta_dir}/example/RNA.fa",
    # ]
    # source /opt/conda/bin/activate RF2NA
    command = [
        "conda",
        "run",
        "-n",
        "RF2NA",
        f"{rosetta_dir}/run_RF2NA.sh",
        f"{local_output_dir}",
        "P:/root/test/protein.fa",
        "D:/root/test/dna.fa",
    ]
    print(" ".join(command))

    command = f"""
        source /opt/conda/bin/activate RF2NA && \
        {rosetta_dir}/run_RF2NA.sh {local_output_dir} P:/root/test/protein.fa D:/root/test/dna.fa
    """

    subprocess.run(command, shell=True, executable="/bin/bash")

    try:
        # subprocess.run(command, check=True, cwd=local_output_dir)
        print("Done")
    except Exception as e:
        print("FAILED")
        print(e)
        # time.sleep(6000)

    print("Returning results")
    return LatchOutputDir(str("/root/outputs"), output_directory.remote_path)

import subprocess
from typing import List, Tuple


def run_git_command(command: str) -> str:
    """
    Run git command and return output as a
    decoded string

    :param command: Command to run
    :return: Command output decoded
    """
    output = subprocess.check_output(
        command, shell=True
    )

    return output.decode('UTF-8')


def get_merge_hashes() -> Tuple[str, str]:
    """
    Get the last two merge commit hashes
    :return: head, prev
    """
    # Get the two commit hashes for last two merge commits

    git_command = "git log --merges -n 2 --pretty=format:'%h'"

    git_refs = run_git_command(git_command)

    # Split to get hea and prev merge
    head, prev = git_refs.split('\n')

    return head, prev


def get_changed_files() -> List:
    head, prev = get_merge_hashes()

    git_command = f"git log --name-only --pretty=oneline --full-index {prev}..{head} | grep -vE '^[0-9a-f]{{40}} ' | sort | uniq"

    changed_files = run_git_command(git_command)

    changed_files = changed_files.split('\n')

    return changed_files

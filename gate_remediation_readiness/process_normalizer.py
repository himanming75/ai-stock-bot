from __future__ import annotations


def normalize_controller_processes(processes: list[dict]) -> dict:
    matching = [
        item for item in processes
        if "run_paper_automation_controller.py"
        in str(item.get("CommandLine", ""))
    ]
    ids = {
        int(item.get("ProcessId", 0)): item
        for item in matching
        if item.get("ProcessId")
    }
    roots = []
    children = []
    for item in matching:
        parent = int(item.get("ParentProcessId", 0) or 0)
        if parent in ids:
            children.append(item)
        else:
            roots.append(item)

    command_groups = {}
    for root in roots:
        command = " ".join(
            str(root.get("CommandLine", "")).split()
        )
        command_groups.setdefault(command, []).append(root)

    return {
        "matching_process_count": len(matching),
        "normalized_controller_instance_count": len(roots),
        "child_interpreter_count": len(children),
        "duplicate_controller_confirmed": len(roots) > 1,
        "root_processes": roots,
        "child_processes": children,
        "command_group_count": len(command_groups),
    }

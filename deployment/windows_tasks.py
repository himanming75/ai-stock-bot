from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


TASK_NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
ET.register_namespace("", TASK_NS)


@dataclass(frozen=True)
class TaskDefinition:
    name: str
    description: str
    command: str
    arguments: str
    start_boundary: str
    enabled: bool
    execution_time_limit: str
    restart_count: int
    restart_interval: str

    def to_xml(self) -> str:
        task = ET.Element(f"{{{TASK_NS}}}Task", {"version": "1.4"})

        registration = ET.SubElement(
            task, f"{{{TASK_NS}}}RegistrationInfo"
        )
        ET.SubElement(
            registration, f"{{{TASK_NS}}}Description"
        ).text = self.description

        triggers = ET.SubElement(task, f"{{{TASK_NS}}}Triggers")
        calendar = ET.SubElement(
            triggers,
            f"{{{TASK_NS}}}CalendarTrigger",
        )
        ET.SubElement(
            calendar, f"{{{TASK_NS}}}StartBoundary"
        ).text = self.start_boundary
        ET.SubElement(
            calendar, f"{{{TASK_NS}}}Enabled"
        ).text = str(self.enabled).lower()
        schedule = ET.SubElement(
            calendar, f"{{{TASK_NS}}}ScheduleByDay"
        )
        ET.SubElement(
            schedule, f"{{{TASK_NS}}}DaysInterval"
        ).text = "1"

        principals = ET.SubElement(
            task, f"{{{TASK_NS}}}Principals"
        )
        principal = ET.SubElement(
            principals,
            f"{{{TASK_NS}}}Principal",
            {"id": "Author"},
        )
        ET.SubElement(
            principal, f"{{{TASK_NS}}}LogonType"
        ).text = "InteractiveToken"
        ET.SubElement(
            principal, f"{{{TASK_NS}}}RunLevel"
        ).text = "LeastPrivilege"

        settings = ET.SubElement(
            task, f"{{{TASK_NS}}}Settings"
        )
        ET.SubElement(
            settings, f"{{{TASK_NS}}}MultipleInstancesPolicy"
        ).text = "IgnoreNew"
        ET.SubElement(
            settings, f"{{{TASK_NS}}}DisallowStartIfOnBatteries"
        ).text = "false"
        ET.SubElement(
            settings, f"{{{TASK_NS}}}StopIfGoingOnBatteries"
        ).text = "false"
        ET.SubElement(
            settings, f"{{{TASK_NS}}}AllowHardTerminate"
        ).text = "false"
        ET.SubElement(
            settings, f"{{{TASK_NS}}}StartWhenAvailable"
        ).text = "false"
        ET.SubElement(
            settings, f"{{{TASK_NS}}}RunOnlyIfNetworkAvailable"
        ).text = "false"
        ET.SubElement(
            settings, f"{{{TASK_NS}}}Enabled"
        ).text = str(self.enabled).lower()
        ET.SubElement(
            settings, f"{{{TASK_NS}}}ExecutionTimeLimit"
        ).text = self.execution_time_limit

        restart = ET.SubElement(
            settings, f"{{{TASK_NS}}}RestartOnFailure"
        )
        ET.SubElement(
            restart, f"{{{TASK_NS}}}Interval"
        ).text = self.restart_interval
        ET.SubElement(
            restart, f"{{{TASK_NS}}}Count"
        ).text = str(self.restart_count)

        actions = ET.SubElement(
            task,
            f"{{{TASK_NS}}}Actions",
            {"Context": "Author"},
        )
        execute = ET.SubElement(
            actions, f"{{{TASK_NS}}}Exec"
        )
        ET.SubElement(
            execute, f"{{{TASK_NS}}}Command"
        ).text = self.command
        ET.SubElement(
            execute, f"{{{TASK_NS}}}Arguments"
        ).text = self.arguments

        return ET.tostring(
            task,
            encoding="unicode",
            xml_declaration=False,
        )


def build_default_tasks(root: Path) -> list[TaskDefinition]:
    powershell = "powershell.exe"
    project = str(root)
    return [
        TaskDefinition(
            name="AIStockBot-Runtime-DISABLED",
            description=(
                "Disabled production runtime task. "
                "Requires Actual validation and operator activation."
            ),
            command=powershell,
            arguments=(
                f'-NoProfile -ExecutionPolicy Bypass '
                f'-File "{project}\\RUN_R2_RUNTIME_WRAPPER.ps1"'
            ),
            start_boundary="2099-01-01T09:25:00",
            enabled=False,
            execution_time_limit="PT8H",
            restart_count=0,
            restart_interval="PT5M",
        ),
        TaskDefinition(
            name="AIStockBot-HealthMonitor-DISABLED",
            description=(
                "Disabled read-only health monitor task."
            ),
            command=powershell,
            arguments=(
                f'-NoProfile -ExecutionPolicy Bypass '
                f'-File "{project}\\RUN_OPERATIONS_MONITOR.ps1"'
            ),
            start_boundary="2099-01-01T08:00:00",
            enabled=False,
            execution_time_limit="PT10M",
            restart_count=0,
            restart_interval="PT5M",
        ),
        TaskDefinition(
            name="AIStockBot-DailyReport-DISABLED",
            description=(
                "Disabled daily reporting task."
            ),
            command=powershell,
            arguments=(
                f'-NoProfile -ExecutionPolicy Bypass '
                f'-File "{project}\\RUN_O4_DAILY_REPORT.ps1"'
            ),
            start_boundary="2099-01-01T17:00:00",
            enabled=False,
            execution_time_limit="PT30M",
            restart_count=0,
            restart_interval="PT5M",
        ),
    ]


def export_task_xml(root: Path, output: Path) -> list[dict[str, Any]]:
    output.mkdir(parents=True, exist_ok=True)
    values = []
    for task in build_default_tasks(root):
        path = output / f"{task.name}.xml"
        path.write_text(task.to_xml() + "\n", encoding="utf-8")
        values.append({
            "name": task.name,
            "path": str(path),
            "enabled": task.enabled,
            "restart_count": task.restart_count,
        })
    return values

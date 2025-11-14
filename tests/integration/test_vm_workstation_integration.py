"""Integration test for VM Workstation creation and validation.

This test replicates the bash workflow from scripts/run-vm-test-workflow.sh
but uses vmws CLI commands instead of raw gcloud commands.

Features:
    - TRUE cost calculation based on actual resource usage during test
    - Customizable machine type and disk size
    - Automatic Cloud Workstation cost calculation (same VM + $0.20/hour always-on fee)
    - Automatic resource cleanup
    - Detailed Markdown report with cost breakdown

Usage:
    # Run as pytest (requires VMWS_INTEGRATION_TESTS=1)
    VMWS_INTEGRATION_TESTS=1 pytest tests/integration/test_vm_workstation_integration.py -v -s

    # Run as standalone script with defaults
    python tests/integration/test_vm_workstation_integration.py --workstation-disk disk-name

    # Run with custom VM specs
    python tests/integration/test_vm_workstation_integration.py \
      --workstation-disk disk-name \
      --machine-type n2-standard-4 \
      --disk-size 500

Environment Variables:
    VMWS_INTEGRATION_TESTS - Must be set to "1" to run integration tests (pytest only)
    VMWS_WORKSTATION_DISK - Workstation disk to snapshot
    VMWS_REGION - GCP region (default: northamerica-northeast1)
    VMWS_ZONE - GCP zone (default: northamerica-northeast1-b)
    VMWS_PROJECT - GCP project ID (uses gcloud default if not set)
    VMWS_MACHINE_TYPE - VM machine type (default: e2-standard-2)
    VMWS_DISK_SIZE_GB - Data disk size in GB (default: 200)
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest


class VMWorkstationIntegrationTest:
    """Integration test for VM Workstation workflow."""

    def __init__(
        self,
        workstation_disk: str,
        zone: str = "northamerica-northeast1-b",
        region: str = "northamerica-northeast1",
        project: str | None = None,
        machine_type: str = "e2-standard-2",
        disk_size_gb: int = 200,
    ) -> None:
        """Initialize integration test.

        Args:
            workstation_disk: Name of workstation disk to snapshot
            zone: GCP zone
            region: GCP region
            project: GCP project ID (uses gcloud default if None)
            machine_type: VM machine type (e.g., e2-standard-2, n2-standard-4)
            disk_size_gb: Data disk size in GB
        """
        self.workstation_disk = workstation_disk
        self.zone = zone
        self.region = region
        self.project = project or self._get_gcloud_project()
        self.machine_type = machine_type
        self.disk_size_gb = disk_size_gb

        # Generate unique test VM name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.vm_name = f"test-vm-{timestamp}"
        self.snapshot_name = f"{self.vm_name}-snapshot"
        self.disk_name = f"{self.vm_name}-disk"

        # Report data
        self.report_data: dict[str, Any] = {
            "start_time": datetime.now(),
            "steps": [],
            "validation_results": [],
            "resources": [],
        }

        # Track created resources for cleanup
        self.created_resources = {
            "vm": False,
            "disk": False,
            "snapshot": False,
        }

        # Track resource creation times for accurate cost calculation
        self.resource_creation_times: dict[str, datetime] = {}
        self.resource_deletion_times: dict[str, datetime] = {}

    def _get_gcloud_project(self) -> str:
        """Get default gcloud project."""
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=False,
        )
        project = result.stdout.strip()
        if not project or project == "(unset)":
            raise ValueError("No GCP project configured. Set VMWS_PROJECT or run 'gcloud config set project PROJECT_ID'")
        return project

    def _run_command(self, cmd: list[str], description: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run command and log result."""
        print(f"\n🔵 {description}")
        print(f"   Command: {' '.join(cmd)}")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"   ✅ Success ({duration:.1f}s)")
        else:
            print(f"   ❌ Failed ({duration:.1f}s)")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")

        self.report_data["steps"].append({
            "description": description,
            "success": result.returncode == 0,
            "duration": duration,
            "command": " ".join(cmd),
        })

        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed: {description}\n{result.stderr}")

        return result

    def step1_create_snapshot(self) -> None:
        """Step 1: Create snapshot from workstation disk."""
        print("\n" + "="*80)
        print("STEP 1: Create Snapshot from Workstation Disk")
        print("="*80)

        self._run_command(
            [
                "gcloud", "compute", "disks", "snapshot",
                self.workstation_disk,
                f"--snapshot-names={self.snapshot_name}",
                f"--region={self.region}",
                f"--project={self.project}",
                f"--storage-location={self.region}",
            ],
            f"Creating snapshot {self.snapshot_name}",
        )

        self.created_resources["snapshot"] = True
        self.resource_creation_times["snapshot"] = datetime.now()
        self.report_data["resources"].append({
            "type": "Snapshot",
            "name": self.snapshot_name,
            "location": self.region,
        })

    def step2_create_disk(self) -> None:
        """Step 2: Create disk from snapshot."""
        print("\n" + "="*80)
        print("STEP 2: Create Disk from Snapshot")
        print("="*80)

        self._run_command(
            [
                "gcloud", "compute", "disks", "create",
                self.disk_name,
                f"--source-snapshot={self.snapshot_name}",
                f"--size={self.disk_size_gb}GB",
                "--type=pd-standard",
                f"--zone={self.zone}",
                f"--project={self.project}",
            ],
            f"Creating disk {self.disk_name}",
        )

        self.created_resources["disk"] = True
        self.resource_creation_times["disk"] = datetime.now()
        self.report_data["resources"].append({
            "type": "Disk",
            "name": self.disk_name,
            "size": f"{self.disk_size_gb}GB",
            "zone": self.zone,
        })

    def step3_create_vm(self) -> None:
        """Step 3: Create VM instance."""
        print("\n" + "="*80)
        print("STEP 3: Create VM Instance")
        print("="*80)

        # Get startup script path
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        startup_script = scripts_dir / "vm-startup-script.sh"

        if not startup_script.exists():
            print(f"   ⚠️  Warning: Startup script not found at {startup_script}")
            startup_script_args = []
        else:
            startup_script_args = [f"--metadata-from-file=startup-script={startup_script}"]

        self._run_command(
            [
                "gcloud", "compute", "instances", "create",
                self.vm_name,
                f"--machine-type={self.machine_type}",
                f"--zone={self.zone}",
                f"--project={self.project}",
                "--image-family=debian-12",
                "--image-project=debian-cloud",
                "--boot-disk-size=50GB",
                "--boot-disk-type=pd-standard",
                f"--disk=name={self.disk_name},mode=rw",
                "--scopes=cloud-platform",
                "--metadata=enable-oslogin=TRUE",
            ] + startup_script_args,
            f"Creating VM {self.vm_name}",
        )

        self.created_resources["vm"] = True
        self.resource_creation_times["vm"] = datetime.now()

        # Configure vmws to use this VM
        self._run_command(
            ["vmws", "config", f"--vm-name={self.vm_name}", f"--zone={self.zone}", f"--project={self.project}"],
            "Configuring vmws",
        )

        self.report_data["resources"].append({
            "type": "VM Instance",
            "name": self.vm_name,
            "machine_type": self.machine_type,
            "zone": self.zone,
        })

    def step4_wait_for_ssh(self, max_retries: int = 12, retry_delay: int = 10) -> None:
        """Step 4: Wait for SSH to be ready."""
        print("\n" + "="*80)
        print("STEP 4: Wait for SSH Connectivity")
        print("="*80)

        for attempt in range(1, max_retries + 1):
            print(f"\n   Attempt {attempt}/{max_retries}...")
            result = self._run_command(
                ["vmws", "ssh", "echo 'SSH ready'"],
                f"Testing SSH connectivity (attempt {attempt})",
                check=False,
            )

            if result.returncode == 0:
                print("   ✅ SSH is ready!")
                return

            if attempt < max_retries:
                print(f"   Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)

        raise RuntimeError("SSH failed to become ready after all retries")

    def step5_fix_permissions(self, username: str = "ben_getmensio_com") -> None:
        """Step 5: Fix file permissions on mounted disk."""
        print("\n" + "="*80)
        print("STEP 5: Fix File Permissions")
        print("="*80)

        self._run_command(
            ["vmws", "ssh", f"sudo chown -R {username}:{username} /mnt/home/user"],
            "Fixing ownership of /mnt/home/user",
        )

        # Write a test file for validation
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._run_command(
            ["vmws", "ssh", f"echo 'VM setup completed at {timestamp}' > /mnt/home/user/vm-setup-log.md"],
            "Writing test file for validation",
        )

    def step6_install_dev_environment(self) -> None:
        """Step 6: Install development environment."""
        print("\n" + "="*80)
        print("STEP 6: Install Development Environment")
        print("="*80)

        # Copy and run setup script
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        setup_script = scripts_dir / "setup-vm-environment.sh"

        if not setup_script.exists():
            print(f"   ⚠️  Warning: Setup script not found at {setup_script}")
            return

        # Copy script to VM
        self._run_command(
            [
                "gcloud", "compute", "scp",
                str(setup_script),
                f"{self.vm_name}:/tmp/setup-vm-environment.sh",
                f"--zone={self.zone}",
                f"--project={self.project}",
                "--tunnel-through-iap",
            ],
            "Copying setup script to VM",
        )

        # Run setup script
        self._run_command(
            ["vmws", "ssh", "bash /tmp/setup-vm-environment.sh"],
            "Installing Docker, code-server, and neovim",
        )

    def step7_install_auto_shutdown(self) -> None:
        """Step 7: Install auto-shutdown service."""
        print("\n" + "="*80)
        print("STEP 7: Install Auto-Shutdown Service")
        print("="*80)

        scripts_dir = Path(__file__).parent.parent.parent / "scripts"

        # Copy auto-shutdown scripts
        for script_file in ["vm-auto-shutdown.sh", "install-auto-shutdown.sh"]:
            script_path = scripts_dir / script_file
            if script_path.exists():
                self._run_command(
                    [
                        "gcloud", "compute", "scp",
                        str(script_path),
                        f"{self.vm_name}:/tmp/{script_file}",
                        f"--zone={self.zone}",
                        f"--project={self.project}",
                        "--tunnel-through-iap",
                    ],
                    f"Copying {script_file} to VM",
                )

        # Run install script
        self._run_command(
            ["vmws", "ssh", "bash /tmp/install-auto-shutdown.sh"],
            "Installing auto-shutdown service",
        )

    def step8_run_validation_tests(self) -> None:
        """Step 8: Run validation tests."""
        print("\n" + "="*80)
        print("STEP 8: Run Validation Tests")
        print("="*80)

        tests = [
            ("Disk mounted", "mountpoint -q /mnt/home && echo 'PASS' || echo 'FAIL'"),
            ("Files accessible", "ls -1 /mnt/home/user/ | wc -l"),
            ("File write/read access", "cat /mnt/home/user/vm-setup-log.md > /dev/null 2>&1 && echo 'PASS' || echo 'FAIL'"),
            ("Docker running", "docker ps > /dev/null 2>&1 && echo 'PASS' || echo 'FAIL'"),
            ("code-server running", "systemctl is-active code-server && echo 'PASS' || echo 'FAIL'"),
        ]

        for test_name, test_command in tests:
            # Use raw gcloud ssh for clean output (vmws ssh prints connection messages)
            result = self._run_command(
                [
                    "gcloud", "compute", "ssh",
                    self.vm_name,
                    f"--zone={self.zone}",
                    f"--project={self.project}",
                    "--tunnel-through-iap",
                    "--command", test_command,
                ],
                f"Testing: {test_name}",
                check=False,
            )

            output = result.stdout.strip()
            passed = "PASS" in output or (test_name == "Files accessible" and output.isdigit() and int(output) > 0)

            self.report_data["validation_results"].append({
                "test": test_name,
                "passed": passed,
                "details": output,
            })

            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test_name}: {status} - {output}")

    def generate_report(self, output_path: Path) -> None:
        """Generate Markdown report."""
        print("\n" + "="*80)
        print("Generating Report")
        print("="*80)

        end_time = datetime.now()
        duration = (end_time - self.report_data["start_time"]).total_seconds()

        # Calculate TRUE costs based on actual resource usage
        costs = self._calculate_actual_costs()

        report = f"""# VM Workstation Integration Test Report

**Generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {duration:.1f}s ({duration/60:.1f} minutes)
**VM Name:** `{self.vm_name}`
**Machine Type:** `{self.machine_type}`
**Disk Size:** `{self.disk_size_gb}GB`
**Zone:** `{self.zone}`
**Project:** `{self.project}`

## Executive Summary

✅ **Test Status:** {'PASSED' if all(v['passed'] for v in self.report_data['validation_results']) else 'FAILED'}
📊 **Validation Tests:** {sum(1 for v in self.report_data['validation_results'] if v['passed'])}/{len(self.report_data['validation_results'])} passed
💵 **Test Cost:** ${costs['test_cost']:.4f} (actual resources used)
💰 **Monthly Cost (24/7):** ${costs['monthly_24x7']['total']:.2f} vs ${costs['comparison']['workstation_cost']:.2f} Cloud Workstation
💵 **Savings:** {costs['comparison']['savings_24x7_percent']:.0f}% (${costs['comparison']['savings_24x7']:.2f}/month)

---

## Resources Created

| Resource Type | Name | Location | Details |
|--------------|------|----------|---------|
"""
        for resource in self.report_data["resources"]:
            details = resource.get("size", "") or resource.get("machine_type", "")
            report += f"| {resource['type']} | `{resource['name']}` | {resource.get('zone') or resource.get('location', '')} | {details} |\n"

        report += """
---

## Workflow Steps

| Step | Description | Status | Duration |
|------|-------------|--------|----------|
"""
        for i, step in enumerate(self.report_data["steps"], 1):
            status = "✅" if step["success"] else "❌"
            report += f"| {i} | {step['description']} | {status} | {step['duration']:.1f}s |\n"

        report += """
---

## Validation Tests

| Test | Status | Details |
|------|--------|---------|
"""
        for test in self.report_data["validation_results"]:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            report += f"| {test['test']} | {status} | `{test['details']}` |\n"

        report += f"""
---

## Cost Analysis

### Actual Test Cost Breakdown

**Total Test Cost:** ${costs['test_cost']:.4f}

| Resource | Duration | Cost |
|----------|----------|------|
| VM ({self.machine_type}) | {costs['durations'].get('vm', 0):.2f} hours | ${costs['cost_breakdown'].get('vm', 0):.4f} |
| Data Disk ({self.disk_size_gb}GB) | {costs['durations'].get('disk', 0):.2f} hours | ${costs['cost_breakdown'].get('disk', 0):.4f} |
| Boot Disk (50GB) | {costs['durations'].get('disk', 0):.2f} hours | ${costs['cost_breakdown'].get('boot_disk', 0):.4f} |
| Snapshot ({self.disk_size_gb}GB) | {costs['durations'].get('snapshot', 0):.2f} hours | ${costs['cost_breakdown'].get('snapshot', 0):.4f} |

*Note: Test costs are based on actual resource creation-to-deletion time.*

### Monthly Cost Breakdown

#### Self-Managed VM (24/7 usage)

- **VM ({self.machine_type}):** ${costs['monthly_24x7']['vm']:.2f}/month
- **Data disk ({self.disk_size_gb}GB pd-standard):** ${costs['monthly_24x7']['disk']:.2f}/month
- **Boot disk (50GB pd-standard):** ${costs['monthly_24x7']['boot_disk']:.2f}/month
- **Total:** ${costs['monthly_24x7']['total']:.2f}/month

#### Cloud Workstation (equivalent specs)

- **VM ({self.machine_type}):** ${costs['workstation']['vm']:.2f}/month
- **Data disk ({self.disk_size_gb}GB pd-standard):** ${costs['workstation']['disk']:.2f}/month
- **Boot disk (50GB pd-standard):** ${costs['workstation']['boot_disk']:.2f}/month
- **Always-on fee ($0.20/hour):** ${costs['workstation']['always_on_fee']:.2f}/month
- **Total:** ${costs['workstation']['total']:.2f}/month

### Comparison: Cloud Workstation vs Self-Managed VM

| Scenario | Cloud Workstation | Self-Managed VM | Savings |
|----------|-------------------|-----------------|---------|
| 24/7 Usage | ${costs['comparison']['workstation_cost']:.2f}/month | ${costs['monthly_24x7']['total']:.2f}/month | ${costs['comparison']['savings_24x7']:.2f}/month ({costs['comparison']['savings_24x7_percent']:.0f}%) |
| 8hr/day (auto-shutdown) | ${costs['comparison']['workstation_cost']:.2f}/month | ${costs['monthly_8hr']['total']:.2f}/month | ${costs['comparison']['savings_8hr']:.2f}/month ({costs['comparison']['savings_8hr_percent']:.0f}%) |

*Assumptions: 730 hrs/month for 24/7, 8 hrs/day × 22 working days for 8hr/day scenario.*

---

## Access Instructions

### SSH Access
```bash
vmws ssh
```

### code-server Access
```bash
# Option 1: Using vmws
vmws tunnel

# Option 2: Direct gcloud
gcloud compute start-iap-tunnel {self.vm_name} 8080 --local-host-port=localhost:8080 --zone={self.zone}
```

Then open: http://localhost:8080

### File Access
- User files: `/mnt/home/user/`
- Projects: `/mnt/home/user/life-cockpit/`

---

## Cleanup Instructions

### Using vmws
```bash
vmws delete --yes
gcloud compute snapshots delete {self.snapshot_name} --quiet
```

### Manual cleanup
```bash
gcloud compute instances delete {self.vm_name} --zone={self.zone} --quiet
gcloud compute disks delete {self.disk_name} --zone={self.zone} --quiet
gcloud compute snapshots delete {self.snapshot_name} --quiet
```

---

## Summary

- **Total execution time:** {duration:.1f}s ({duration/60:.1f} minutes)
- **Report generated:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}
- **All resources created in:** {self.zone}

🤖 Generated by vmws integration test
"""

        output_path.write_text(report)
        print(f"   📄 Report saved to: {output_path}")

    def _calculate_actual_costs(self) -> dict[str, Any]:
        """Calculate TRUE costs based on actual resource usage during the test.

        Returns:
            Dictionary with cost breakdown and comparison
        """
        # GCP pricing (as of 2025, subject to change - check cloud.google.com/compute/pricing)
        # Prices are per hour
        pricing = {
            "e2-standard-2": 0.067,      # $0.067/hour
            "e2-standard-4": 0.134,      # $0.134/hour
            "n2-standard-2": 0.097,      # $0.097/hour
            "n2-standard-4": 0.194,      # $0.194/hour
            "pd-standard-gb": 0.04 / 730,  # $0.04/GB/month = ~$0.0000548/GB/hour
            "pd-ssd-gb": 0.17 / 730,       # $0.17/GB/month = ~$0.0002329/GB/hour
            "snapshot-gb": 0.026 / 730,    # $0.026/GB/month = ~$0.0000356/GB/hour
        }

        # Get machine type pricing (default to e2-standard-2 if not found)
        vm_hourly_rate = pricing.get(self.machine_type, pricing["e2-standard-2"])

        # Calculate duration for each resource (in hours)
        costs: dict[str, float] = {}
        durations: dict[str, float] = {}

        for resource in ["vm", "disk", "snapshot"]:
            if resource in self.resource_creation_times and resource in self.resource_deletion_times:
                duration_seconds = (
                    self.resource_deletion_times[resource] - self.resource_creation_times[resource]
                ).total_seconds()
                durations[resource] = duration_seconds / 3600.0  # Convert to hours

        # Calculate costs
        if "vm" in durations:
            costs["vm"] = durations["vm"] * vm_hourly_rate

        if "disk" in durations:
            costs["disk"] = durations["disk"] * self.disk_size_gb * pricing["pd-standard-gb"]
            costs["boot_disk"] = durations["disk"] * 50 * pricing["pd-standard-gb"]  # 50GB boot disk

        if "snapshot" in durations:
            costs["snapshot"] = durations["snapshot"] * self.disk_size_gb * pricing["snapshot-gb"]

        # Calculate total test cost
        total_test_cost = sum(costs.values())

        # Calculate monthly costs (for comparison)
        vm_monthly = vm_hourly_rate * 730  # 730 hours/month average
        disk_monthly = self.disk_size_gb * 0.04  # $0.04/GB/month
        boot_disk_monthly = 50 * 0.04
        total_monthly = vm_monthly + disk_monthly + boot_disk_monthly

        # Calculate Cloud Workstation cost (same VM + $0.20/hour always-on fee)
        workstation_always_on_fee = 0.20 * 730  # $0.20/hour * 730 hours/month = $146/month
        workstation_monthly_cost = vm_monthly + disk_monthly + boot_disk_monthly + workstation_always_on_fee

        # Calculate savings vs Cloud Workstation
        savings_monthly = workstation_monthly_cost - total_monthly
        savings_percent = (savings_monthly / workstation_monthly_cost) * 100

        # Calculate 8hr/day scenario (auto-shutdown)
        vm_8hr_monthly = vm_hourly_rate * 8 * 22  # 8 hours/day, 22 working days/month
        total_8hr_monthly = vm_8hr_monthly + disk_monthly + boot_disk_monthly
        savings_8hr_monthly = workstation_monthly_cost - total_8hr_monthly
        savings_8hr_percent = (savings_8hr_monthly / workstation_monthly_cost) * 100

        return {
            "test_cost": total_test_cost,
            "test_duration_hours": sum(durations.values()) / len(durations) if durations else 0,
            "cost_breakdown": costs,
            "durations": durations,
            "monthly_24x7": {
                "vm": vm_monthly,
                "disk": disk_monthly,
                "boot_disk": boot_disk_monthly,
                "total": total_monthly,
            },
            "monthly_8hr": {
                "vm": vm_8hr_monthly,
                "disk": disk_monthly,
                "boot_disk": boot_disk_monthly,
                "total": total_8hr_monthly,
            },
            "workstation": {
                "vm": vm_monthly,
                "disk": disk_monthly,
                "boot_disk": boot_disk_monthly,
                "always_on_fee": workstation_always_on_fee,
                "total": workstation_monthly_cost,
            },
            "comparison": {
                "workstation_cost": workstation_monthly_cost,
                "savings_24x7": savings_monthly,
                "savings_24x7_percent": savings_percent,
                "savings_8hr": savings_8hr_monthly,
                "savings_8hr_percent": savings_8hr_percent,
            },
        }

    def cleanup(self) -> None:
        """Clean up all created resources."""
        print("\n" + "="*80)
        print("CLEANUP: Deleting Resources")
        print("="*80)

        # Delete VM
        if self.created_resources["vm"]:
            self._run_command(
                ["vmws", "delete", "--yes"],
                f"Deleting VM {self.vm_name}",
                check=False,
            )
            self.resource_deletion_times["vm"] = datetime.now()

        # Delete disk
        if self.created_resources["disk"]:
            self._run_command(
                [
                    "gcloud", "compute", "disks", "delete",
                    self.disk_name,
                    f"--zone={self.zone}",
                    f"--project={self.project}",
                    "--quiet",
                ],
                f"Deleting disk {self.disk_name}",
                check=False,
            )
            self.resource_deletion_times["disk"] = datetime.now()

        # Delete snapshot
        if self.created_resources["snapshot"]:
            self._run_command(
                [
                    "gcloud", "compute", "snapshots", "delete",
                    self.snapshot_name,
                    f"--project={self.project}",
                    "--quiet",
                ],
                f"Deleting snapshot {self.snapshot_name}",
                check=False,
            )
            self.resource_deletion_times["snapshot"] = datetime.now()

    def run(self, cleanup_on_completion: bool = True) -> Path:
        """Run the complete integration test workflow.

        Args:
            cleanup_on_completion: Whether to cleanup resources after test

        Returns:
            Path to generated report
        """
        report_path = Path(f"/home/user/vm-integration-test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md")

        try:
            self.step1_create_snapshot()
            self.step2_create_disk()
            self.step3_create_vm()
            self.step4_wait_for_ssh()
            self.step5_fix_permissions()
            self.step6_install_dev_environment()
            self.step7_install_auto_shutdown()
            self.step8_run_validation_tests()

            self.generate_report(report_path)

            print("\n" + "="*80)
            print("✅ Integration Test Complete!")
            print("="*80)
            print(f"📄 Report: {report_path}")

            if cleanup_on_completion:
                self.cleanup()
            else:
                print("\n⚠️  Resources NOT cleaned up (--no-cleanup flag used)")
                print(f"   Run cleanup manually: vmws delete --yes && gcloud compute snapshots delete {self.snapshot_name}")

            return report_path

        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            self.generate_report(report_path)

            # Cleanup on failure
            try:
                self.cleanup()
            except Exception as cleanup_error:
                print(f"⚠️  Cleanup failed: {cleanup_error}")

            raise


@pytest.mark.integration
def test_vm_workstation_integration() -> None:
    """Integration test for VM workstation creation and validation."""
    # Get configuration from environment
    workstation_disk = os.getenv("VMWS_WORKSTATION_DISK")
    if not workstation_disk:
        pytest.skip("VMWS_WORKSTATION_DISK not set")

    zone = os.getenv("VMWS_ZONE", "northamerica-northeast1-b")
    region = os.getenv("VMWS_REGION", "northamerica-northeast1")
    project = os.getenv("VMWS_PROJECT")

    # Get customizable test parameters
    machine_type = os.getenv("VMWS_MACHINE_TYPE", "e2-standard-2")
    disk_size_gb = int(os.getenv("VMWS_DISK_SIZE_GB", "200"))

    # Run integration test
    test = VMWorkstationIntegrationTest(
        workstation_disk=workstation_disk,
        zone=zone,
        region=region,
        project=project,
        machine_type=machine_type,
        disk_size_gb=disk_size_gb,
    )

    report_path = test.run(cleanup_on_completion=True)

    # Verify report was created
    assert report_path.exists(), "Report was not generated"

    # Verify all validation tests passed
    all_passed = all(v["passed"] for v in test.report_data["validation_results"])
    assert all_passed, "Some validation tests failed"


def main() -> int:
    """Run as standalone script."""
    parser = argparse.ArgumentParser(
        description="VM Workstation Integration Test - Create, validate, and cost-compare self-managed VMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test with defaults (e2-standard-2, 200GB)
  python test_vm_workstation_integration.py --workstation-disk workstations-DISK-ID

  # Test with larger VM and disk
  python test_vm_workstation_integration.py \\
    --workstation-disk workstations-DISK-ID \\
    --machine-type n2-standard-4 \\
    --disk-size 500

Environment variables can also be used:
  VMWS_WORKSTATION_DISK, VMWS_ZONE, VMWS_REGION, VMWS_PROJECT,
  VMWS_MACHINE_TYPE, VMWS_DISK_SIZE_GB

Note: Cloud Workstation cost is calculated automatically based on VM specs
      (same compute + $0.20/hour always-on fee = $146/month extra).
        """,
    )

    parser.add_argument(
        "--workstation-disk",
        required=True,
        help="Workstation disk to snapshot (e.g., workstations-4f92986b-...)",
    )
    parser.add_argument(
        "--zone",
        default="northamerica-northeast1-b",
        help="GCP zone (default: northamerica-northeast1-b)",
    )
    parser.add_argument(
        "--region",
        default="northamerica-northeast1",
        help="GCP region (default: northamerica-northeast1)",
    )
    parser.add_argument(
        "--project",
        help="GCP project ID (uses gcloud default if not set)",
    )
    parser.add_argument(
        "--machine-type",
        default="e2-standard-2",
        help="VM machine type (default: e2-standard-2). Examples: e2-standard-4, n2-standard-2, n2-standard-4",
    )
    parser.add_argument(
        "--disk-size",
        type=int,
        default=200,
        help="Data disk size in GB (default: 200)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Don't cleanup resources after test (for inspection/debugging)",
    )

    args = parser.parse_args()

    test = VMWorkstationIntegrationTest(
        workstation_disk=args.workstation_disk,
        zone=args.zone,
        region=args.region,
        project=args.project,
        machine_type=args.machine_type,
        disk_size_gb=args.disk_size,
    )

    try:
        test.run(cleanup_on_completion=not args.no_cleanup)
        return 0
    except Exception as e:
        print(f"\n❌ Test failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

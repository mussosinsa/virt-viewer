#!/usr/bin/env python3

import pathlib
import sys
import xml.etree.ElementTree as ET


def main():
    source_root = pathlib.Path(sys.argv[1])
    manifest_path = source_root / "src" / "virt-viewer.manifest"
    resource = (source_root / "src" / "virt-viewer.rc.in").read_text(encoding="utf-8")
    meson = (source_root / "src" / "meson.build").read_text(encoding="utf-8")
    data_meson = (source_root / "data" / "meson.build").read_text(encoding="utf-8")
    util = (source_root / "src" / "virt-viewer-util.c").read_text(encoding="utf-8")
    installer = (source_root / "data" / "install-rdp-control.ps1").read_text(encoding="utf-8")
    wix = (source_root / "data" / "virt-viewer.wxs.in").read_text(encoding="utf-8")
    manifest = ET.parse(manifest_path)
    level = manifest.find(
        ".//{urn:schemas-microsoft-com:asm.v2}requestedExecutionLevel"
    )

    assert level is not None
    assert level.attrib["level"] == "asInvoker"
    assert '1 RT_MANIFEST MANIFESTDIR "/virt-viewer.manifest"' in resource
    assert '3 RT_MANIFEST MANIFESTDIR "/virt-viewer.manifest"' not in resource
    assert 'Minimum="$(var.Version)" IncludeMinimum="no"' in wix
    assert 'Maximum="$(var.Version)" IncludeMinimum="yes" IncludeMaximum="yes"' in wix
    assert "virt_viewer_sources += [rcobj]" in meson
    assert "remote_viewer_sources += [rcobj]" in meson
    assert "install-rdp-control.ps1" in data_meson
    assert '"schtasks.exe"' in util
    assert 'virt_viewer_run_rdp_control_task("RDP-Block"' in util
    assert 'virt_viewer_run_rdp_control_task("RDP-Unblock"' in util
    assert "ShellExecuteExW" not in util
    assert "CoCreateInstance" not in util
    assert "Set-Service" not in util
    assert '#Requires -RunAsAdministrator' in installer
    assert 'CreateFolder("ovworksViewer", $null)' in installer
    assert 'New-ScheduledTaskPrincipal' in installer
    assert '-UserId "SYSTEM"' in installer
    assert 'SetSecurityDescriptor($taskSddl, 0)' in installer
    assert '$taskFolder.SetSecurityDescriptor($taskSddl, 0)' in installer
    assert 'GRGX;;;$AllowedSid' in installer
    assert 'Managed-RDP-3389-Block' in installer
    assert 'g_utf8_to_utf16(message' in util
    assert 'MessageBoxA' not in util

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

import pathlib
import sys
import xml.etree.ElementTree as ET


def main():
    source_root = pathlib.Path(sys.argv[1])
    manifest_path = source_root / "src" / "virt-viewer.manifest"
    resource = (source_root / "src" / "virt-viewer.rc.in").read_text(encoding="utf-8")
    meson = (source_root / "src" / "meson.build").read_text(encoding="utf-8")
    util = (source_root / "src" / "virt-viewer-util.c").read_text(encoding="utf-8")
    manifest = ET.parse(manifest_path)
    level = manifest.find(
        ".//{urn:schemas-microsoft-com:asm.v2}requestedExecutionLevel"
    )

    assert level is not None
    assert level.attrib["level"] == "requireAdministrator"
    assert '1 RT_MANIFEST MANIFESTDIR "/virt-viewer.manifest"' in resource
    assert '3 RT_MANIFEST MANIFESTDIR "/virt-viewer.manifest"' not in resource
    assert "virt_viewer_sources += [rcobj]" in meson
    assert "remote_viewer_sources += [rcobj]" in meson
    assert "could not block TCP/UDP 3389 or stop" not in util
    assert "remote_desktop_firewall_applied = TRUE" in util
    assert "MB_OK | MB_ICONWARNING" in util
    assert "CoCreateInstance(&virt_viewer_clsid_net_fw_policy2" in util
    assert "CoCreateInstance(&virt_viewer_clsid_net_fw_rule" in util
    assert "&CLSID_NetFwPolicy2" not in util
    assert "&IID_INetFwPolicy2" not in util
    assert "&CLSID_NetFwRule" not in util
    assert "&IID_INetFwRule" not in util
    assert '"netsh.exe"' in util
    assert "virt_viewer_is_elevated()" in util
    assert "PowerShell security command failed" in util

    return 0


if __name__ == "__main__":
    sys.exit(main())

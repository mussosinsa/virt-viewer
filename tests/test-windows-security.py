#!/usr/bin/env python3

import pathlib
import sys
import xml.etree.ElementTree as ET


def main():
    source_root = pathlib.Path(sys.argv[1])
    manifest_path = source_root / "src" / "virt-viewer.manifest"
    meson = (source_root / "src" / "meson.build").read_text(encoding="utf-8")
    util = (source_root / "src" / "virt-viewer-util.c").read_text(encoding="utf-8")
    manifest = ET.parse(manifest_path)
    level = manifest.find(
        ".//{urn:schemas-microsoft-com:asm.v2}requestedExecutionLevel"
    )

    assert level is not None
    assert level.attrib["level"] == "requireAdministrator"
    assert "virt_viewer_sources += [rcobj]" in meson
    assert "remote_viewer_sources += [rcobj]" in meson
    assert "could not block TCP/UDP 3389 or stop" not in util
    assert "remote_desktop_firewall_applied = TRUE" in util
    assert "MB_OK | MB_ICONWARNING" in util
    assert "CoCreateInstance(&CLSID_NetFwPolicy2" in util
    assert "CoCreateInstance(&CLSID_NetFwRule" in util
    assert '"netsh.exe"' in util
    assert "virt_viewer_is_elevated()" in util
    assert "PowerShell security command failed" in util

    return 0


if __name__ == "__main__":
    sys.exit(main())

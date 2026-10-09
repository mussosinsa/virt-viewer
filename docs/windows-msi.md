# Building a Windows MSI

Virt Viewer is cross-compiled for Windows with MinGW-w64. The MSI is then
created on the Linux build host with `wixl` and `wixl-heat` from msitools. The
commands below build a 64-bit installer on Fedora; substitute `mingw32` and the
32-bit cross file to produce an x86 installer.

## 1. Install build dependencies

Install the native build tools and their MinGW-w64 counterparts:

```sh
sudo dnf install \
  gcc git meson ninja-build msitools perl-podlators python3 \
  mingw64-gcc mingw64-binutils mingw64-pkg-config \
  mingw64-glib2 mingw64-glib-networking mingw64-gtk3 \
  mingw64-libxml2 mingw64-libvirt mingw64-libvirt-glib \
  mingw64-gtk-vnc2 mingw64-spice-gtk3 mingw64-libgovirt \
  mingw64-rest mingw64-usbredir
```

Package names can vary between Fedora releases. If an optional protocol
package is unavailable, omit both that package and its Meson feature. At least
one of SPICE (`spice-gtk`) or VNC (`gtk-vnc`) should remain enabled.

Confirm that the MSI tools and cross file are present before configuring:

```sh
command -v wixl wixl-heat
test -f /usr/share/mingw/toolchain-mingw64.meson
```

## 2. Configure and compile

The install prefix must be the MinGW sysroot prefix. `build-id` must be numeric
because it becomes the fourth component of the Windows product version.

```sh
meson setup build-win64 \
  --cross-file=/usr/share/mingw/toolchain-mingw64.meson \
  --prefix=/usr/x86_64-w64-mingw32/sys-root/mingw \
  -Dbuild-id=1
ninja -C build-win64
```

Check Meson's configure output. It must report both `wixl` and `wixl-heat` as
found; otherwise the `msi` target is not generated.

## 3. Stage the installation and create the MSI

The MSI generator packages the staged install tree, not files directly from
the compilation directory. Use the same absolute `DESTDIR` for both commands:

```sh
export DESTDIR="$PWD/build-win64/stage"
rm -rf "$DESTDIR"
DESTDIR="$DESTDIR" ninja -C build-win64 install
DESTDIR="$DESTDIR" ninja -C build-win64 msi
```

The resulting file is placed under `build-win64/data/` and is named like
`virt-viewer-x64-11.0.msi`.

### Customizing the MSI file name

Set `msi-name` during initial configuration to change only the MSI output file's
base name. For example, the following produces
`build-win64/data/ovworks-viewer-x64-11.0.msi`:

```sh
meson setup build-win64 \
  --cross-file=/usr/share/mingw/toolchain-mingw64.meson \
  --prefix=/usr/x86_64-w64-mingw32/sys-root/mingw \
  -Dbuild-id=1 \
  -Dmsi-name=ovworks-viewer
ninja -C build-win64

export DESTDIR="$PWD/build-win64/stage"
rm -rf "$DESTDIR"
DESTDIR="$DESTDIR" ninja -C build-win64 install
DESTDIR="$DESTDIR" ninja -C build-win64 msi
```

For an existing configured build directory, update the option and rebuild the
MSI instead:

```sh
meson configure build-win64 -Dmsi-name=ovworks-viewer
DESTDIR="$PWD/build-win64/stage" ninja -C build-win64 msi
```

This setting changes the output file name only. It does not change the MSI
product name, installation directory, executable names, icons, or publisher.
Those values are defined separately in `data/virt-viewer.wxs.in` and the Windows
resource files.

To build a 32-bit installer instead, use
`/usr/share/mingw/toolchain-mingw32.meson`, the prefix
`/usr/i686-w64-mingw32/sys-root/mingw`, and a separate build directory. Its
output is named `virt-viewer-x86-<version>.msi`.

## 4. Verify the package

Inspect the package metadata and contents before distributing it:

```sh
msiinfo export build-win64/data/virt-viewer-x64-*.msi Property
msiinfo export build-win64/data/virt-viewer-x64-*.msi File
```

Finally, install the MSI on every supported Windows version and test VNC/SPICE
connections, USB redirection (if enabled), shortcuts, uninstall, and upgrades.
For public distribution, sign the final MSI with your organization's code-
signing certificate; signing and certificate management are intentionally
outside this build system.

The Windows executables contain a `requireAdministrator` manifest, so Windows
shows a UAC consent or credentials prompt at launch. After elevation, the viewer
disables and stops the Windows `TermService` service and installs inbound block
rules for TCP and UDP port 3389 on all firewall profiles. An orderly shutdown
removes only those application-owned rules, sets the service to Manual, and
starts it again. The viewer fails closed if the mandatory firewall rules cannot
be installed. If Windows policy refuses to stop `TermService`, it shows a
warning and continues with port and display protection. If the viewer crashes
or is forcibly terminated, an administrator must perform the recovery steps in
`docs/display-security.md`.

The manifest is embedded with Windows resource ID 1
(`CREATEPROCESS_MANIFEST_RESOURCE_ID`). Windows requires this ID to apply
`requestedExecutionLevel` and automatically show the UAC prompt before any
application security code runs.

As a defense against an old, stripped, or ignored manifest, startup also checks
the process elevation token. If it is not elevated, the viewer calls
`ShellExecuteExW` with the `runas` verb, preserves the original command-line
arguments, and exits the unelevated parent after Windows starts the approved
administrator child. Cancelling UAC cancels viewer startup without applying a
partial firewall or service policy. The long executable-path buffer used by
this fallback is heap allocated so hardened MinGW builds using
`-Wframe-larger-than=4096 -Werror` can compile it without creating a 64 KiB
stack frame.

## Troubleshooting

* **`could not block TCP/UDP 3389`**: confirm the UAC prompt was accepted and
  that Windows Defender Firewall is enabled. This means both the native
  `INetFwPolicy2` COM path and the `netsh advfirewall` fallback failed; it is not
  caused by PowerShell execution policy, Constrained Language Mode, or a missing
  NetSecurity module.
* **`needs administrator permission` without a preceding UAC prompt**: the
  executable is older than both elevation fixes. Current source embeds
  `requireAdministrator` as `RT_MANIFEST` resource ID 1 and also has a `runas`
  relaunch fallback. Current MSI metadata permits a security rebuild to replace
  an installed package with the same product version (for example, 11.0 with
  another 11.0 build). Delete the build and staging directories, rebuild the
  MSI, run it, and verify the installed executable timestamp changed. Older MSI
  packages incorrectly classified an equal-version rebuild as a newer installed
  product, so they could leave the old executable in place; uninstall that old
  package manually once if Windows Installer still refuses the replacement.
* **`TCP/UDP 3389 is blocked, but ... could not stop TermService`**: this is a
  non-fatal warning. Windows or domain service policy refused the additional
  service shutdown, but the mandatory firewall rules and in-viewer RDP/display
  protections remain active.
* **`could not block TCP/UDP 3389 or stop ... Approve the UAC prompt`**: this
  exact combined error belongs to an older binary. The current source separates
  mandatory firewall failure from the non-fatal service warning. Delete the
  previous build and staging directories, rebuild the MSI, uninstall the old
  package, and verify the installed `remote-viewer.exe` was replaced.
* **Undefined references to `CLSID_NetFwPolicy2`, `IID_INetFwPolicy2`,
  `CLSID_NetFwRule`, or `IID_INetFwRule`**: some mingw-w64 distributions do not
  export these newer Firewall COM GUIDs from `libuuid`. Current source carries
  private copies of the Windows SDK values and does not link against those
  exports. Update the source and rerun `meson setup --reconfigure build-win64`
  before rebuilding.

* **`unknown target 'msi'`**: the build is not targeting Windows, or `wixl` /
  `wixl-heat` was missing when `meson setup` ran. Install msitools and run
  `meson setup --reconfigure build-win64`.
* **`$DESTDIR environment variable missing`**: export `DESTDIR`, stage with
  `meson install`, then pass the same value to the `ninja ... msi` command.
* **Missing DLLs in the installed application**: install the corresponding
  MinGW dependency before configuration, then recreate the build directory and
  staging directory. Do not copy arbitrary DLLs from the build host.
* **Only `remote-viewer.exe` is present**: the `virt-viewer.exe` target requires
  the MinGW libvirt and libvirt-glib dependencies.

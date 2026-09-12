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

## Troubleshooting

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

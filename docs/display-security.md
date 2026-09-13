# Display and input security boundaries

## What the viewer enforces

When a guest display becomes ready, virt-viewer disables its built-in
screenshot action. On Windows it also sets `WDA_EXCLUDEFROMCAPTURE` on the
top-level guest viewer window. On Windows versions that do not support that
affinity value, it falls back to `WDA_MONITOR`, which normally substitutes a
blank window in supported capture paths. The affinity is removed when the guest
display is removed, so connection and authentication screens are unaffected.

The viewer also avoids writing individual key symbols to its debug log. The
SPICE and VNC keyboard grabs continue to route focused keyboard input to the
guest.

## Remote desktop and remote-support software

`SetWindowDisplayAffinity` is not a DRM or data-loss-prevention boundary. It is
a request to Windows that supported, public capture paths exclude a top-level
window. It does not provide a contract that every display driver, mirror
driver, service, privileged process, or third-party capture implementation will
honor the request.

Consequently, capture blocking **cannot be guaranteed** after connecting with
Microsoft Remote Desktop, TeamViewer, or similar remote-support products:

| Capture path | Expected result | Security guarantee |
| --- | --- | --- |
| Virt-viewer's screenshot action | Disabled while the guest display is ready | Enforced by this application |
| Windows Snipping Tool / Windows Graphics Capture | Viewer should be omitted on supported Windows versions | Subject to Windows version and composition state |
| Microsoft Remote Desktop | May be blank or omitted, but behavior can vary by host/session configuration | Not guaranteed |
| TeamViewer and similar tools | May be blank or omitted if the tool honors Windows affinity | Not guaranteed |
| Administrator/SYSTEM service, display or kernel driver | May capture the content | Not protected |
| Camera, HDMI capture, or compromised host | Can capture the content | Not protected |

The same limitation applies to keylogging. A GTK/SPICE/VNC keyboard grab
controls event routing; it cannot stop an administrator-level hook, service,
filter driver, kernel component, hardware keylogger, or compromised input DLL.

## Deployment guidance

If remote-session capture must be prevented rather than merely discouraged,
enforce that requirement outside the viewer:

1. Do not allow remote desktop or remote-support software on the endpoint while
   protected guest sessions are in use.
2. Use Windows Defender Application Control or AppLocker to allow only approved
   applications and services.
3. Prevent non-administrators from installing services and device/filter
   drivers, and protect administrator credentials.
4. Disable clipboard, file transfer, printing, drive redirection, and remote
   session recording where the selected protocol or product permits it.
5. Use a dedicated, managed kiosk endpoint when the content requires a strict
   data-loss-prevention boundary.

## Acceptance test

Test every supported Windows build and every approved remote-access product;
do not infer TeamViewer behavior from a successful local Snipping Tool test.

1. Open a guest and wait until the guest framebuffer is visible.
2. Test Print Screen, Snipping Tool, and Windows Graphics Capture locally.
3. Connect with Microsoft Remote Desktop and repeat the capture tests from both
   the RDP client and host session.
4. Connect with the exact deployed TeamViewer version and repeat the tests,
   including any session-recording feature.
5. Disconnect the guest and confirm that connection/authentication windows are
   capturable as intended.
6. Repeat after Windows, graphics-driver, Remote Desktop, and TeamViewer
   updates, because these components own capture behavior outside virt-viewer.

Treat any remote tool that still shows the guest framebuffer as incompatible
with the protected deployment. There is no safe application-side change that
can force an arbitrary privileged remote-control product to honor display
affinity.

## Reference

Microsoft documents both the supported affinity values and the explicit
limitation that `SetWindowDisplayAffinity` is not DRM:
[SetWindowDisplayAffinity function](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity).

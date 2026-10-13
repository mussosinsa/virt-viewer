# 소스 코드 메커니즘

이 문서는 virt-viewer/ovworksViewer 저장소를 처음 접하는 개발자가 전체
구조, 연결 흐름, 화면 렌더링, Windows 보안 정책 및 MSI 생성 과정을 빠르게
이해할 수 있도록 작성한 구현 안내서다. 사용자 보안 보장 범위는
`docs/display-security.md`, Windows 빌드 명령은 `docs/windows-msi.md`를 함께
참조한다.

## 1. 프로그램의 역할과 실행 파일

이 프로젝트는 GTK3 기반의 SPICE/VNC 가상 머신 콘솔 클라이언트다. 빌드
조건에 따라 다음 실행 파일을 만든다.

| 실행 파일 | 진입점 | 역할 |
| --- | --- | --- |
| `remote-viewer` | `src/remote-viewer-main.c` | URI 또는 `.vv` 연결 파일을 직접 열고 SPICE/VNC/oVirt 세션을 구성한다. |
| `virt-viewer` | `src/virt-viewer-main.c` | libvirt에서 VM의 그래픽 연결 정보를 조회한 뒤 공통 뷰어 계층을 사용한다. |
| `windows-cmdline-wrapper` | `src/windows-cmdline-wrapper.c` | Windows 명령행/URI 실행을 실제 뷰어 프로세스로 전달하는 보조 실행 파일이다. |

두 주 실행 파일은 동일한 순서를 사용한다.

1. `virt_viewer_util_init()`으로 플랫폼 초기화와 Windows 시작 정책을
   적용한다.
2. `remote_viewer_new()` 또는 `virt_viewer_new()`로 `GApplication` 객체를
   생성한다.
3. `g_application_run()`에서 GTK 이벤트 루프를 실행한다.
4. 객체를 해제한 뒤 `virt_viewer_util_cleanup()`으로 Windows 종료 정책을
   요청한다.

```text
main
 ├─ virt_viewer_util_init
 ├─ application constructor
 ├─ g_application_run
 │   ├─ connection/session lifecycle
 │   ├─ display/window lifecycle
 │   └─ GTK input and actions
 ├─ g_object_unref
 └─ virt_viewer_util_cleanup
```

## 2. 계층 구조

핵심 구현은 GObject 상속과 GLib signal을 이용해 UI, 프로토콜, 화면을
분리한다.

### 2.1 애플리케이션 계층

`VirtViewerApp`(`src/virt-viewer-app.c`)은 다음 공통 상태를 소유하는 중심
조정자다.

- 현재 `VirtViewerSession`
- 주 창과 추가 모니터 창 목록
- 연결 주소, 포트, TLS 및 인증 정보
- 전체 화면, 확대/축소, 키 조합, USB redirection 같은 사용자 설정
- 세션의 display 추가/삭제 및 연결/해제 signal 처리

`RemoteViewer`와 `VirtViewer`는 `VirtViewerApp`의 하위 타입이다.
`RemoteViewer`는 입력 URI와 `.vv` 파일을 해석하고, `VirtViewer`는 libvirt
도메인에서 그래픽 연결 정보를 얻는다. 연결 방법이 달라도 이후 창·세션·
display 처리는 공통 애플리케이션 계층으로 합류한다.

### 2.2 세션 계층

`VirtViewerSession`(`src/virt-viewer-session.c`)은 추상 GObject다. 프로토콜별
구현은 다음 파일에 있다.

- SPICE: `src/virt-viewer-session-spice.c`
- VNC: `src/virt-viewer-session-vnc.c`

세션은 연결 자체와 display 목록을 관리하며 `session-connected`,
`session-disconnected`, `session-display-added`, `session-display-removed`,
인증, USB, clipboard 등의 signal을 내보낸다. 애플리케이션은 구체적인
SPICE/VNC 위젯 API에 직접 의존하지 않고 이 signal을 통해 상태를 갱신한다.

### 2.3 Display 계층

`VirtViewerDisplay`(`src/virt-viewer-display.c`)는 하나의 게스트 화면을
표현하는 추상 GTK 위젯이다.

- `VirtViewerDisplaySpice`: SPICE-GTK display를 감싼다.
- `VirtViewerDisplayVnc`: GTK-VNC display를 감싼다.
- `VirtViewerDisplayVte`: 필요할 때 텍스트 터미널 채널을 표현한다.

display 객체는 화면 번호, 준비 상태, 모니터 위치, 확대/축소, 전체 화면,
키보드 grab 상태를 공통 속성과 signal로 제공한다. 다중 모니터 세션에서는
세션이 display를 여러 개 만들고 애플리케이션이 각각을 창에 배치한다.

### 2.4 창과 Notebook 계층

`VirtViewerWindow`(`src/virt-viewer-window.c`)는 메뉴, toolbar, GTK action,
fullscreen, screenshot, 키 입력 전달 및 최상위 창 상태를 관리한다.
`VirtViewerNotebook`(`src/virt-viewer-notebook.c`)은 연결 대기/오류/게스트
화면 같은 페이지 전환을 담당한다.

UI 정의는 `src/resources/ui/` 아래의 GtkBuilder 파일에 있고,
`src/resources/virt-viewer.gresource.xml`을 통해 실행 파일 리소스로
컴파일된다.

## 3. 연결부터 렌더링까지의 흐름

```text
URI / .vv / libvirt domain
          │
          ▼
RemoteViewer 또는 VirtViewer
          │ 연결 정보 정규화
          ▼
VirtViewerApp::create_session
          │ type = spice | vnc
          ▼
VirtViewerSessionSpice / VirtViewerSessionVnc
          │ 프로토콜 연결 및 채널 생성
          ▼
session-display-added
          │
          ▼
VirtViewerDisplaySpice / VirtViewerDisplayVnc
          │
          ▼
VirtViewerNotebook → VirtViewerWindow → GTK/GDK
```

1. 실행 파일별 하위 클래스가 URI, `.vv` 또는 libvirt 정보를 공통 연결
   속성으로 변환한다.
2. `VirtViewerApp`이 `spice` 또는 `vnc` 문자열에 맞는 세션 하위 객체를
   생성한다.
3. 프로토콜 라이브러리가 연결되면 세션 signal이 발생한다.
4. 그래픽 채널마다 display 객체가 세션에 추가되고
   `session-display-added`가 전달된다.
5. 애플리케이션이 display를 notebook/창에 넣는다.
6. display가 ready 상태가 되면 게스트 framebuffer를 표시하고 관련 UI
   action을 활성화한다.
7. 채널 종료 시 반대 순서로 display를 제거하고 연결 상태 페이지로
   돌아간다.

## 4. 입력과 사용자 동작

- 키보드와 포인터 이벤트의 실제 게스트 전송은 SPICE-GTK 또는 GTK-VNC가
  담당한다.
- `VirtViewerWindow`는 release-cursor, secure-attention, fullscreen 같은
  accelerator와 메뉴 action을 조정한다.
- clipboard, USB redirection, file transfer 기능은 빌드 시 활성화된
  프로토콜 라이브러리 기능을 세션 signal/action으로 연결한다.
- 입력 개인정보 보호를 위해 개별 keysym/keycode는 debug 로그에 남기지
  않는다. `tests/test-input-privacy.py`가 금지된 로그 패턴의 재도입을
  검사한다.
- 애플리케이션 내부 screenshot action은 게스트 display가 준비된 동안
  비활성화된다.

## 5. Windows 화면 보호 메커니즘

### 5.1 Capture exclusion

게스트 display가 준비되고 최상위 창의 native handle이 존재하면
`VirtViewerWindow`가 `SetWindowDisplayAffinity()`에
`WDA_EXCLUDEFROMCAPTURE`를 요청한다. 지원하지 않는 Windows에서는
`WDA_MONITOR`로 fallback한다. display가 제거되거나 준비되지 않으면 affinity를
해제한다. 따라서 인증/연결 창 전체가 아니라 실제 게스트 화면이 표시되는
기간에만 적용된다.

이 API는 지원되는 Windows capture 경로에 대한 요청이며 DRM 경계가 아니다.
관리자/SYSTEM 프로세스, display driver, 카메라 또는 affinity를 무시하는
원격 지원 제품까지 막는다고 보장하지 않는다.

### 5.2 RDP 세션 차단

Windows가 `SM_REMOTESESSION`을 반환하면 `VirtViewerNotebook`은 게스트
페이지 대신 차단 안내 페이지를 표시한다. 같은 상태에서 창의 키 이벤트도
게스트로 전달하지 않는다. 주기적인 상태 확인으로 로컬 console로 돌아오면
게스트 페이지를 복원한다.

### 5.3 SYSTEM 예약 작업

일반 사용자 실행 파일은 시스템 방화벽이나 HKLM을 직접 변경하지 않는다.
대신 시작 시 다음 명령과 동등한 요청을 보낸다.

```cmd
schtasks.exe /run /tn "\RDP-Block"
```

정상 종료 시에는 `\RDP-Unblock`을 요청한다. Block 작업 제출에 실패하면
게스트 연결 전에 오류를 표시하고 프로세스를 종료하는 fail-closed 동작을
사용한다.

예약 작업은 `data/install-rdp-control.ps1`이 MSI 설치 중 SYSTEM/Highest로
등록한다. 제어 스크립트는 다음 작업을 수행한다.

- TCP/UDP 3389 inbound block firewall rule 활성화/비활성화
- `TeamViewer.exe`, `vncserver.exe`, `vncviewer.exe`, `winvnc.exe`,
  `tvnserver.exe` 이름으로 실행 중인 프로세스 종료
- 위 image 이름의 IFEO `Debugger` 값을 임시 설정하여 재실행 차단
- `ovworksViewerManaged` 표시가 일치하는 IFEO 값만 종료 시 제거
- 기존 관리자/타사 IFEO 정책이 있으면 덮어쓰지 않고 Block 작업 실패

IFEO는 파일 이름 기반 방어이므로 이름 변경으로 우회할 수 있다. 강한 실행
제어가 필요하면 WDAC/AppLocker를 조직 정책으로 배포해야 한다. 비정상 종료
시 Unblock이 실행되지 않을 수 있으므로 운영 복구 절차도 필요하다.

## 6. MSI 설치 메커니즘

`data/virt-viewer.wxs.in`은 per-machine MSI를 정의한다. 설치 순서는 다음과
같다.

1. Windows Installer가 시스템 전체 설치에 필요한 관리자 승인을 받는다.
2. `InstallFiles`가 실행 파일, DLL, 리소스 및
   `share/virt-viewer/install-rdp-control.ps1`을 배치한다.
3. wixl 호환 type 51 action인 `SetPowerShellExe`가 PowerShell 경로를
   `POWERSHELLEXE` 속성에 저장한다.
4. type 50 `ProvisionRdpControl` action이 deferred/non-impersonated 방식으로
   PowerShell 스크립트를 실행한다.
5. 스크립트 실패 시 `Return="check"`에 의해 MSI 설치도 실패한다.

`build-aux/msitool.py`는 `DESTDIR` staging tree를 `wixl-heat`로 수집하고,
주 WXS 파일 및 의존성 WXI 파일과 함께 `wixl`에 전달한다. `data/meson.build`의
`msi` alias target이 이 과정을 호출한다.

## 7. 빌드 시스템

최상위 `meson.build`는 compiler option과 GTK/GLib/libvirt/SPICE/VNC/oVirt
의존성을 탐지한다. `src/meson.build`는 다음 정적 라이브러리와 실행 파일을
구성한다.

- `libvirt-viewer-util`: 플랫폼 공통/Windows utility
- `libvirt-viewer-common`: app/session/display/window 공통 구현
- `remote-viewer`, 조건부 `virt-viewer`, Windows wrapper

Windows에서는 `virt-viewer.rc.in`을 `windres`로 컴파일하고 두 뷰어 실행
파일에 포함한다. 리소스에는 icon, version 정보와 resource ID 1의
`asInvoker` manifest가 들어간다. 따라서 일반 실행은 UAC를 요구하지 않고,
관리자 변경은 MSI와 SYSTEM 예약 작업으로 분리된다.

## 8. 테스트와 회귀 방지

| 테스트 | 목적 |
| --- | --- |
| `tests/test-monitor-mapping.c` | 게스트 display와 host monitor 매핑 |
| `tests/test-monitor-alignment.c` | 다중 모니터 geometry 정렬 |
| `tests/test-hotkeys.c` | hotkey 문자열 파싱 |
| `tests/test-version-compare.c` | 버전 비교 |
| `tests/test-input-privacy.py` | keysym/keycode 로그 금지 정책 |
| `tests/test-windows-security.py` | manifest, MSI action, 예약 작업, firewall/IFEO 정책의 정적 연결 검사 |

Python 보안 테스트는 Windows API 자체를 실행하는 통합 테스트가 아니라
소스 회귀 검사다. 실제 릴리스 전에는 Windows VM에서 MSI 설치/UAC, 일반
사용자 task 실행, 방화벽, IFEO, RDP 전환, capture 도구와 비정상 종료 복구를
별도로 검증해야 한다.

## 9. 수정 시 확인해야 할 불변 조건

1. 프로토콜별 코드는 가능한 한 `VirtViewerSession`/`VirtViewerDisplay`
   추상 계층 뒤에 둔다.
2. display 생성/제거는 세션 signal 흐름과 GObject reference 수명을 함께
   유지한다.
3. 게스트가 보이지 않을 때 capture affinity를 제거한다.
4. key value 또는 keysym을 로그에 추가하지 않는다.
5. 일반 사용자 viewer에서 HKLM/firewall을 직접 수정하지 않는다.
6. 예약 작업은 SYSTEM/Highest로 유지하되 일반 사용자는 read/execute만
   위임받는다.
7. IFEO cleanup은 `ovworksViewerManaged` 소유 표시가 일치할 때만 수행한다.
8. wixl이 지원하지 않는 WiX 속성을 추가하지 않는다. 변경 후 생성된 MSI의
   `CustomAction`과 `InstallExecuteSequence` 테이블을 확인한다.
9. 보안 기능이 best-effort인지 강제 경계인지 문서에서 구분한다.

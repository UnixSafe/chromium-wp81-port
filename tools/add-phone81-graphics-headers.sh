#!/bin/bash
# Local, non-redistributed overlay step for the Windows Phone 8.1 port.
#
# Chromium's Windows GPU code (compiled, but disabled at run time on the
# phone: --disable-gpu, CPU compositor) needs DXGI 1.4-1.6, D3D11.3/11.4,
# D3D12 and DirectComposition declarations. Mixing those newer headers with
# the Phone 8.1 DXGI/D3D11 base headers is inconsistent (the Phone SDK keeps
# IDXGIFactory2/3 and the D3D11 video interfaces in the desktop partition).
# So the whole DXGI/D3D11/D3DCommon header set is replaced by the coherent
# Windows SDK set, which declares them in the application partition. Only COM
# declarations change; linking still uses the Phone d3d11.lib/dxgi imports.
# Desktop-only headers get a wrapper that lifts WINAPI_FAMILY for their own
# declarations. Phone originals are kept as *.phone-orig.
set -eu
if [ $# -ne 2 ]; then
  echo "usage: $0 <windows-sdk-include-dir> <phone81-overlay-include-um-dir>" >&2
  exit 2
fi
M=$(cd "$1" && pwd)
P=$(cd "$2" && pwd)
install_modern() {  # install_modern <relative-modern-path>
  local b; b=$(basename "$1")
  # The overlay file system is case-insensitive: find an existing variant.
  local existing; existing=$(ls "$P" | grep -ix "$b" || true)
  if [ -n "$existing" ] && [ ! -e "$P/$existing.phone-orig" ]; then
    cp -p "$P/$existing" "$P/$existing.phone-orig"
  fi
  cp "$M/$1" "$P/${existing:-$b}"
  # The Phone SDK rpcndr.h is version 500; these MIDL outputs ask for 501 but
  # use no 501-only feature in their declarations.
  perl -pi -e 's/^(#define __REQUIRED_RPCNDR_H_VERSION__) 501(\r?)$/$1 500$2/' "$P/${existing:-$b}"
}
# Newer MIDL outputs (DXGI, D3D11, and desktop headers such as shobjidl.h
# reached through the fallback SDK) need a newer rpcndr.h than the Phone SDK.
for h in um/rpcndr.h shared/rpcndr.h; do
  if [ -e "$M/$h" ]; then install_modern "$h"; break; fi
done
for h in shared/dxgi.h shared/dxgi1_2.h shared/dxgi1_3.h shared/dxgi1_4.h \
         shared/dxgi1_5.h shared/dxgi1_6.h shared/dxgicommon.h \
         shared/dxgiformat.h shared/dxgitype.h um/d3dcommon.h um/d3d11.h \
         um/d3d11_1.h um/d3d11_2.h um/d3d11_3.h um/d3d11_4.h \
         um/d3d11sdklayers.h shared/d3d9types.h um/d3d12.h \
         um/d3d12sdklayers.h shared/dcomptypes.h um/dcompanimation.h; do
  if [ -e "$M/$h" ]; then install_modern "$h"; fi
done
rm -f "$P/phone81_dxgi_color_space.h"
for h in dcomp.h shellscalingapi.h; do
  cat > "$P/$h" <<WRAP
// Local Phone 8.1 overlay wrapper (not redistributed): exposes the desktop
// declarations of the Windows SDK header $h to Chromium code that is
// compiled but disabled at run time on the phone (no GPU, no HWND windows).
#pragma once
#include <windows.h>
#pragma push_macro("WINAPI_FAMILY")
#undef WINAPI_FAMILY
#define WINAPI_FAMILY WINAPI_FAMILY_DESKTOP_APP
#include "$M/um/$h"
#pragma pop_macro("WINAPI_FAMILY")
WRAP
done
# dwmapi.h pulls uxtheme.h -> commctrl.h (whole desktop UI). It only needs
# MARGINS from uxtheme.h, so define that and stub uxtheme.h.
cat > "$P/dwmapi.h" <<WRAP
// Local Phone 8.1 overlay wrapper (not redistributed) for dwmapi.h. DWM does
// not exist on the phone and the code using it is disabled at run time.
#pragma once
#include <windows.h>
#ifndef _UXTHEME_H_
#define _UXTHEME_H_
typedef struct _MARGINS {
  int cxLeftWidth;
  int cxRightWidth;
  int cyTopHeight;
  int cyBottomHeight;
} MARGINS, *PMARGINS;
#endif
#pragma push_macro("WINAPI_FAMILY")
#undef WINAPI_FAMILY
#define WINAPI_FAMILY WINAPI_FAMILY_DESKTOP_APP
#include "$M/um/dwmapi.h"
#pragma pop_macro("WINAPI_FAMILY")
WRAP
[ -e "$P/uxtheme.h" ] || printf '%s\n' '// Local Phone 8.1 overlay stub (see dwmapi.h).' '#pragma once' > "$P/uxtheme.h"
echo "graphics headers installed in $P"

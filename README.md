# ps4_remote_pkg_installer-OOSDK

This is a OOSDK port of flat's ps4_remote_pkg_installer, all credit goes to them and their amazing work!

## Building

A visual studio project has been included for building on Windows. On Linux, a makefile has been included.

To build this project, the developer will need clang, which is provided in the [toolchain](https://github.com/OpenOrbis/OpenOrbis-PS4-Toolchain). The `OO_PS4_TOOLCHAIN` environment variable will also need to be set to the root directory of the SDK installation.

__Windows__
Open the Visual Studio project and build, or run the batch file from command prompt or powershell with the following command:

```bash
.\build.bat .\x64\Debug "RPI" "%OO_PS4_TOOLCHAIN%\\RPI"
```

__Linux__
Run the makefile.

```bash
make
```

__MacOS__
Run the makefile.

```bash
brew install llvm
sudo OO_PS4_TOOLCHAIN=/opt/OpenOrbis-PS4-Toolchain make
```

## NOTES

- The default port is 12801
- Some freeBSD net functions where giving issue with printing debug info out, so i swapped these to the sceNet* versions as they seemed to work.

## Thanks

- [OpenOrbis/OpenOrbis-PS4-Toolchain](https://github.com/OpenOrbis/OpenOrbis-PS4-Toolchain)
- [flatz/ps4_remote_pkg_installer](https://github.com/flatz/ps4_remote_pkg_installer)

## Changes in this fork (branch `improvements`)

Found while reading the code because RPI stopped answering after some hundred requests
(the PS4 log said `[ScePthread/System] Internal Memory for Pthread is running out.`). The same code is in flatz's
original, the port only copied it.

- **Thread leak (the cause of the above).** `sb_poll_server` created one thread for every connection and never
  detached or joined it. A thread that is not joined keeps its resources after it ended, so the console ran out of
  thread memory, then `pthread_create` failed and RPI closed every new connection at once. The threads are detached
  now. A failed `pthread_create` also leaked the stream, and closed its socket twice, both fixed.
- **Shared memory between connections.** 13 API handlers and `pkg_extract_piece_urls_from_ref_pkg_json` used a
  `static json_t* pool` that is allocated and freed per request. Every connection has its own thread, two requests at
  the same time (an install and a progress poll) freed and used the same pointer. It is a local variable now. The
  function in `pkg.c` also never freed the pool.
- **Limits.** At most 24 connections at the same time (more are refused). Send and receive timeout of 30 s on every
  connection, checked by reading the option back. Requests larger than 1 MB are dropped. The `timeout`, `max_lifetime`
  and `max_request_size` options were read but never used.
- **`send`** uses `MSG_NOSIGNAL` and `SO_NOSIGPIPE` (a write to a closed connection raised SIGPIPE), an interrupted
  `recv`/`send` is repeated, and a send that timed out ends the stream (it looped for ever).
- **No more busy loop.** The listening socket does not block and `server_listen` called `sb_poll_server` without a
  pause, RPI used a whole CPU core. It sleeps 5 ms between polls.
- **`assert` in the handlers** (an empty or missing request body aborted the whole app) is an HTTP 400 now.
- **`do_request` in `http.c`** overwrote its error code with the result of the clean up, a failed request was reported
  as success. The sceHttp calls have a 30 s timeout.
- `sb_close_server` destroyed the next stream instead of the current one (and NULL at the end).
- **A log line per request**, `[RPI] POST /api/get_task_progress ok in 3 ms, 2 connections open`, it appears in the
  klog when TTY redirect is on in GoldHEN.
- **A stats line once a minute** (when something happened), `[RPI] stats: up 3600 s, 412 connections served,
  1 open now (peak 3), 0 refused, 0 thread failures`. Every connection has a thread: "open now" must stay low, if it
  climbs the threads are not given back. A failed `pthread_create` and a refused connection are logged at once.

### Building on Windows with the current toolchain

`python tools/build.py --toolchain <OpenOrbis toolchain folder>` runs the steps of `RPI/build.bat` and puts everything in
`build/` (the package is `build/IV0000-KPBR01111_00-AAAAAAAAAAAAAAAA.pkg`). Tested with the OpenOrbis toolchain v0.5.4 and
the clang 19 / lld that come with Visual Studio 2022. Differences to `build.bat`:

- clang 16+ turns the use of an undeclared function into an error, the 2022 sources have a few (`strcpy` without
  `string.h`, ...). They stay warnings (`-Wno-error=implicit-function-declaration` and two similar flags).
- The headers of the newer toolchain do not include `stdint.h` themselves, so it is force-included.
- `-lSceJson` does not exist in the newer toolchain and nothing uses it (RPI has `tiny-json`), the build skips a library
  that is missing.
- `PkgTool.Core` is a .NET Core 3.0 program, `DOTNET_ROLL_FORWARD=Major` lets it run on a newer .NET (for that process only).

### Status

Reviewed and the changed `sandbird.c` passes a syntax/type check with clang (`tools\check-syntax.ps1`, stand-in
headers, no new warnings). **Builds with the OpenOrbis toolchain (see above), not run on a console yet.** The functions
added by the changes (`pthread_attr_*`, `clock_gettime`, `sceKernelUsleep`, the sceHttp timeouts) are declared in the real
headers and the program links. The default port is still 12801, so it can be installed
next to flatz's RPI (title id FLTZ00003), only one of them can run at a time.

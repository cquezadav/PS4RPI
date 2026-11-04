"""Builds RPI.pkg with the OpenOrbis toolchain on Windows (the same steps as RPI/build.bat, output in ./build).

    python tools/build.py [--toolchain <folder>] [--stage compile|link|eboot|pkg]

Needs: the OpenOrbis toolchain (OO_PS4_TOOLCHAIN or --toolchain), clang + ld.lld (the LLVM of Visual Studio 2022 is used
when they are not on PATH) and a .NET runtime for PkgTool.Core (it targets .NET Core 3.0, it runs on a newer runtime
because DOTNET_ROLL_FORWARD=Major is set for that process only).
"""
import argparse, glob, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'RPI')
BUILD = os.path.join(ROOT, 'build')
OBJ = os.path.join(BUILD, 'obj')

VS_LLVM = r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\x64\bin'

PKG_VERSION = '01.02'
PKG_TITLE = 'RPI'
PKG_TITLE_ID = 'KPBR01111'
PKG_CONTENT_ID = 'IV0000-KPBR01111_00-AAAAAAAAAAAAAAAA'
LIBS = ['-lc', '-lkernel', '-lc++', '-lSceUserService', '-lSceSystemService', '-lSceNet', '-lSceHttp', '-lSceBgft',
        '-lSceAppInstUtil', '-lSceSsl', '-lSceSysmodule', '-lSceNetCtl', '-lSceJson', '-lSceNpUtility', '-lSceNpCommon']


def find_tool(name):
    found = shutil.which(name)
    if found:
        return found
    candidate = os.path.join(VS_LLVM, name + '.exe')
    if os.path.exists(candidate):
        return candidate
    sys.exit('Tool not found: ' + name)


def run(cmd, cwd=None, env=None):
    print('>', ' '.join('"%s"' % c if ' ' in c else c for c in cmd)[:300])
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip())
    if result.returncode:
        sys.exit('FAILED (exit code %d)' % result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--toolchain', default=os.environ.get('OO_PS4_TOOLCHAIN'))
    parser.add_argument('--stage', default='pkg', choices=['compile', 'link', 'eboot', 'pkg'])
    args = parser.parse_args()
    if not args.toolchain or not os.path.isdir(args.toolchain):
        sys.exit('Set OO_PS4_TOOLCHAIN or pass --toolchain <folder of the OpenOrbis toolchain>')

    tc = os.path.abspath(args.toolchain)
    os.environ['OO_PS4_TOOLCHAIN'] = tc      # the tools read it, set for this process only
    tools = os.path.join(tc, 'bin', 'windows')
    clang = find_tool('clang')
    lld = find_tool('ld.lld')
    os.makedirs(OBJ, exist_ok=True)

    # 1. compile
    objects = []
    # The code is from 2022. clang 16+ turns the use of an undeclared function into an error, the sources have a few
    # (strcpy without string.h, ...). They stay warnings here, the right includes are a clean up for later.
    flags = ['--target=x86_64-pc-freebsd12-elf', '-fPIC', '-funwind-tables', '-c', '-isysroot', tc,
             '-isystem', os.path.join(tc, 'include'), '-isystem', os.path.join(tc, 'include', 'c++', 'v1'),
             '-Wno-error=implicit-function-declaration', '-Wno-error=int-conversion', '-Wno-error=incompatible-pointer-types',
             # the 2022 headers of the port expect the integer types to be known already
             '-include', 'stdint.h', '-include', 'stddef.h', '-include', 'stdbool.h']
    for source in sorted(glob.glob(os.path.join(SRC, '*.c'))):
        obj = os.path.join(OBJ, os.path.splitext(os.path.basename(source))[0] + '.o')
        run([clang] + flags + ['-o', obj, source], cwd=SRC)
        objects.append(obj)
    print('compiled %d files' % len(objects))
    if args.stage == 'compile':
        return

    # 2. link. A library the toolchain does not have is skipped (-lSceJson is not in newer toolchains, RPI uses tiny-json)
    libs = []
    for lib in LIBS:
        name = lib[2:]
        if os.path.exists(os.path.join(tc, 'lib', 'lib%s.so' % name)) or os.path.exists(os.path.join(tc, 'lib', 'lib%s.a' % name)):
            libs.append(lib)
        else:
            print('note: %s is not in this toolchain, skipped' % lib)
    elf = os.path.join(BUILD, 'RPI.elf')
    run([lld, '-m', 'elf_x86_64', '-pie', '--script', os.path.join(tc, 'link.x'), '--eh-frame-hdr', '-o', elf,
         '-L' + os.path.join(tc, 'lib')] + libs + [os.path.join(tc, 'lib', 'crt1.o')] + objects)
    if args.stage == 'link':
        return

    # 3. eboot
    oelf = os.path.join(BUILD, 'RPI.oelf')
    run([os.path.join(tools, 'create-fself.exe'), '-in', elf, '--out', oelf, '--eboot', os.path.join(ROOT, 'eboot.bin'),
         '--paid', '0x3800000000000011'])
    if args.stage == 'eboot':
        return

    # 4. param.sfo, gp4, pkg (run in the project folder, the paths in the gp4 are relative)
    env = dict(os.environ, DOTNET_ROLL_FORWARD='Major')
    pkgtool = os.path.join(tools, 'PkgTool.Core.exe')
    sfo = 'sce_sys/param.sfo'
    run([pkgtool, 'sfo_new', sfo], cwd=ROOT, env=env)
    for key, kind, size, value in [
        ('APP_TYPE', 'Integer', '4', '1'), ('APP_VER', 'Utf8', '8', PKG_VERSION), ('ATTRIBUTE', 'Integer', '4', '32'),
        ('CATEGORY', 'Utf8', '4', 'gde'), ('CONTENT_ID', 'Utf8', '48', PKG_CONTENT_ID),
        ('DOWNLOAD_DATA_SIZE', 'Integer', '4', '0'), ('SYSTEM_VER', 'Integer', '4', '0'), ('TITLE', 'Utf8', '128', PKG_TITLE),
        ('TITLE_ID', 'Utf8', '12', PKG_TITLE_ID), ('VERSION', 'Utf8', '8', PKG_VERSION)]:
        run([pkgtool, 'sfo_setentry', sfo, key, '--type', kind, '--maxsize', size, '--value', value], cwd=ROOT, env=env)

    modules = ['sce_module/' + f for f in sorted(os.listdir(os.path.join(ROOT, 'sce_module')))]
    files = ['eboot.bin', 'sce_sys/about/right.sprx', 'sce_sys/param.sfo', 'sce_sys/icon0.png', 'sce_sys/pic0.png', 'sce_sys/pic1.png'] + modules
    run([os.path.join(tools, 'create-gp4.exe'), '-out', 'pkg.gp4', '--content-id=' + PKG_CONTENT_ID, '--files', ' '.join(files)], cwd=ROOT)
    run([pkgtool, 'pkg_build', 'pkg.gp4', BUILD], cwd=ROOT, env=env)
    print('done, look in', BUILD)


if __name__ == '__main__':
    main()

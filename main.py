"""main"""
import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ZIG_VERSION = "zig-x86_64-linux-0.15.0-dev.643+dc6ffc28b"
GDB_VERSION = "gdb-12.1"

BUILD_PATH = Path.cwd().joinpath("build-dir")

GDB_SRC_PATH = BUILD_PATH.joinpath("gdb-src")
ZIG_PATH = BUILD_PATH.joinpath("zig")
BUILD_RESULT_PATH = BUILD_PATH.joinpath("result")
BUILD_RESULT_PATH.mkdir(exist_ok=True)


async def run_cmd(
    *cmd: str, env: Optional[dict[str, str]] = None, cwd: Optional[Path] = None
) -> None:
    """异步运行命令"""
    print(f"run {cmd}")
    proc = await asyncio.create_subprocess_exec(*cmd, env=env, cwd=cwd)
    ret_code = await proc.wait()

    if ret_code != 0:
        msg = f"run {cmd} failed, exit code: {ret_code}"
        raise RuntimeError(msg)


async def run_shell(cmd: str, cwd: Optional[Path]) -> None:
    """异步在 shell 中运行命令"""
    print(f"run {cmd} in shell")
    proc = await asyncio.create_subprocess_shell(cmd, cwd=cwd)
    ret_code = await proc.wait()

    if ret_code != 0:
        msg = f"run {cmd} in shell failed, exit code: {ret_code}"
        raise RuntimeError(msg)


async def init_gdb_src() -> None:
    """初始化 gdb 源码"""
    await run_cmd(
        "wget",
        f"https://sourceware.org/pub/gdb/releases/{GDB_VERSION}.tar.gz",
        "-O",
        "gdb.tar.gz",
        cwd=BUILD_PATH,
    )
    await run_cmd("tar", "xvf", "gdb.tar.gz", cwd=BUILD_PATH)
    shutil.move(BUILD_PATH.joinpath(GDB_VERSION), GDB_SRC_PATH)
    await run_shell("cat ../../patch/*.diff|patch -p1", cwd=GDB_SRC_PATH)


async def init_zig() -> None:
    """初始化 zig"""
    await run_cmd(
        "wget",
        f"https://ziglang.org/builds/{ZIG_VERSION}.tar.xz",
        "-O",
        "zig.tar.gz",
        cwd=BUILD_PATH,
    )
    await run_cmd("tar", "xvf", "zig.tar.gz", cwd=BUILD_PATH)
    shutil.move(BUILD_PATH.joinpath(ZIG_VERSION), ZIG_PATH)


@dataclass
class ArchInfo:
    """编译架构信息"""

    name: str
    clang_target: str
    gdb_host: str
    arch_option: Optional[str] = None


ARCH_LIST = [
    ArchInfo(
        name="mipsel-linux-musleabi",
        clang_target="mipsel-linux-musleabi",
        gdb_host="mipsel-linux-gnu",
        # rel1
        arch_option="-mcpu=mips32",
    ),
    ArchInfo(
        name="mips-linux-musleabi",
        clang_target="mips-linux-musleabi",
        gdb_host="mips-linux-gnu",
        # rel1
        arch_option="-mcpu=mips32",
    ),
    ArchInfo(
        name="mips64-linux-muslabi64",
        clang_target="mips64-linux-muslabi64",
        gdb_host="mips64-linux-gnuabi64",
        # 不设置的话编译会莫名报 warning
        # zig: warning: ignoring '-fno-PIC' option as it cannot be used with implicit usage of -mabicalls and the N64 ABI [-Woption-ignored]  # noqa: E501
        # 会导致 configure 配置错误
        # https://github.com/crosstool-ng/crosstool-ng/issues/469
        arch_option="-fPIC",
    ),
    ArchInfo(
        name="mips64el-linux-muslabi64",
        clang_target="mips64el-linux-muslabi64",
        gdb_host="mips64el-linux-gnuabi64",
        arch_option="-fPIC",
    ),
    ArchInfo(
        name="arm-linux-musleabi",
        clang_target="arm-linux-musleabi",
        gdb_host="arm-linux-gnueabi",
    ),
    ArchInfo(
        name="aarch64-linux-musl",
        clang_target="aarch64-linux-musl",
        gdb_host="aarch64-linux-gnu",
    ),
    ArchInfo(
        name="powerpc-linux-musleabi",
        clang_target="powerpc-linux-musleabi",
        gdb_host="powerpc-linux-gnu",
    ),
    # zig 不支持
    # ArchInfo(
    #     name="powerpcle-linux-musleabi",
    #     clang_target="powerpcle-linux-musleabi",
    #     gdb_host="powerpcle-linux-gnu",
    # ),
    ArchInfo(
        name="powerpc64-linux-musl",
        clang_target="powerpc64-linux-musl",
        gdb_host="powerpc64-linux-gnu",
    ),
    ArchInfo(
        name="powerpc64le-linux-musl",
        clang_target="powerpc64le-linux-musl",
        gdb_host="powerpc64le-linux-gnu",
    ),
    ArchInfo(
        name="x86_64-linux-musl",
        clang_target="x86_64-linux-musl",
        gdb_host="x86_64-pc-linux-gnu",
    ),
    ArchInfo(
        name="x86-linux-musl",
        clang_target="x86-linux-musl",
        gdb_host="i686-pc-linux-gnu",
    ),
]


async def build_gdbserver(path: Path, arch_info: ArchInfo) -> None:
    """编译 gdbserver"""
    path.mkdir()
    env = os.environ.copy()
    if arch_info.arch_option is not None:
        env["CC"] = f"zig cc -target {arch_info.clang_target} {arch_info.arch_option}"
        env["CXX"] = f"zig c++ -target {arch_info.clang_target} {arch_info.arch_option}"
    else:
        env["CC"] = f"zig cc -target {arch_info.clang_target}"
        env["CXX"] = f"zig c++ -target {arch_info.clang_target}"
    env["CFLAGS"] = "-Os -flto"
    env["CXXFLAGS"] = "-Os -flto"
    env["LDFLAGS"] = "-flto"
    env["LD"] = "zig ld.lld"
    env["AR"] = "zig ar"
    await run_cmd(
        "bash",
        "../gdb-src/configure",
        f"--host={arch_info.gdb_host}",
        "--disable-inprocess-agent",
        cwd=path,
        env=env,
    )
    print(f"configure {arch_info.name} success")
    await run_cmd("make", "all-gdbserver", "-j", cwd=path)
    shutil.copy(
        path.joinpath("gdbserver/gdbserver"),
        BUILD_RESULT_PATH.joinpath(f"{arch_info.name}-gdbserver"),
    )
    print(f"build {arch_info.name} success")


async def main() -> None:
    """主逻辑"""
    BUILD_PATH.mkdir(exist_ok=True)
    if not GDB_SRC_PATH.exists():
        await init_gdb_src()

    print("gdb src init success.")

    if not ZIG_PATH.exists():
        await init_zig()
    os.environ["PATH"] = f"{ZIG_PATH}:{os.environ['PATH']}"
    print("zig init success.")

    task_list: list[asyncio.Task[None]] = []
    for arch_info in ARCH_LIST:
        build_path = BUILD_PATH.joinpath(arch_info.name)
        if build_path.exists():
            print(f"skip {arch_info.name}")
            continue
        task_list.append(asyncio.create_task(build_gdbserver(build_path, arch_info)))

    await asyncio.gather(*task_list)


if __name__ == "__main__":
    asyncio.run(main())

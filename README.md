# gdbserver static

使用 zig 自动构建静态 gdbserver

版本: 12.1 （高版本 gdb 有 bug，调试时可能会有空指针错误）

支持架构:

+ mipsel-linux-musleabi
+ mips-linux-musleabi
+ mips64-linux-muslabi64
+ mips64el-linux-muslabi64
+ arm-linux-musleabi
+ aarch64-linux-musl
+ powerpc-linux-musleabi
+ powerpc64-linux-musl
+ powerpc64le-linux-musl
+ x86_64-linux-musl
+ x86-linux-musl

## patch

会自动应用如下补丁

### disable-remote-libthread_db

gdbserver 会尝试加载远程的 libthread_db, 由于 ld 存在 bug 可能会导致加载时 crash

因此直接进行 patch 使其不会加载

### proc-mem-rw-memory

优先使用 proc/mem 来读写内存

有的程序无法使用 ptrace 写程序段的内存，因此从高版本 gdb backport 了该功能

设置环境变量 GS_PROC_RW_MEM 以启用

### fix-zig-build

因为会有符号冲突，需要修改 gdb 源码 libiberty/strncmp.c，注释原有的 strncmp

"""Minimal stand-ins for the POSIX / OpenOrbis headers, only to let a host compiler check the SYNTAX and TYPES of
RPI/sandbird.c (clang -fsyntax-only style). Nothing is linked or run. Usage: python make_stubs.py <output folder>
"""
import os, sys

out = sys.argv[1]
files = {
'stub_types.h': """#pragma once
#include <stddef.h>
#include <stdint.h>
typedef long long ssize_t;
typedef unsigned int socklen_t;
""",
'pthread.h': """#pragma once
typedef unsigned long long pthread_t;
typedef struct { int x; } pthread_mutex_t;
typedef struct { int x; } pthread_attr_t;
#define PTHREAD_CREATE_DETACHED 1
int pthread_mutex_init(pthread_mutex_t*, const void*);
int pthread_mutex_lock(pthread_mutex_t*);
int pthread_mutex_unlock(pthread_mutex_t*);
int pthread_mutex_destroy(pthread_mutex_t*);
int pthread_create(pthread_t*, const pthread_attr_t*, void* (*)(void*), void*);
void pthread_exit(void*);
int pthread_detach(pthread_t);
int pthread_attr_init(pthread_attr_t*);
int pthread_attr_setdetachstate(pthread_attr_t*, int);
int pthread_attr_destroy(pthread_attr_t*);
""",
'sys/time.h': """#pragma once
struct timeval { long long tv_sec; long tv_usec; };
""",
'sys/socket.h': """#pragma once
#include "../stub_types.h"
#include <sys/time.h>
struct sockaddr { unsigned short sa_family; char sa_data[14]; };
struct sockaddr_storage { char x[128]; };
#define SOL_SOCKET 0xffff
#define SO_REUSEADDR 4
#define SO_RCVTIMEO 0x1006
#define SO_SNDTIMEO 0x1005
#define SO_NOSIGPIPE 0x800
#define MSG_NOSIGNAL 0x20000
#define SHUT_RDWR 2
#define SOCK_STREAM 1
#define AF_INET 2
int accept(int, struct sockaddr*, socklen_t*);
ssize_t recv(int, void*, size_t, int);
ssize_t send(int, const void*, size_t, int);
int setsockopt(int, int, int, const void*, socklen_t);
int getsockopt(int, int, int, void*, socklen_t*);
int shutdown(int, int);
int getpeername(int, struct sockaddr*, socklen_t*);
int listen(int, int);
""",
'netinet/in.h': """#pragma once
#include "../stub_types.h"
struct in_addr { uint32_t s_addr; };
struct sockaddr_in { short sin_family; uint16_t sin_port; struct in_addr sin_addr; char pad[8]; };
#define INADDR_ANY 0
#define IPPROTO_TCP 6
#define INET_ADDRSTRLEN 16
""",
'arpa/inet.h': """#pragma once
#include "../stub_types.h"
#include <netinet/in.h>
int inet_pton(int, const char*, void*);
const char* inet_ntop(int, const void*, char*, socklen_t);
uint16_t htons(uint16_t);
uint32_t htonl(uint32_t);
""",
'unistd.h': """#pragma once
#include "stub_types.h"
int close(int);
ssize_t read(int, void*, size_t);
""",
'fcntl.h': """#pragma once
#define F_GETFL 3
#define F_SETFL 4
#define O_NONBLOCK 0x4
#define O_RDONLY 0
int fcntl(int, int, ...);
int open(const char*, int, ...);
""",
'strings.h': """#pragma once
int strcasecmp(const char*, const char*);
int strncasecmp(const char*, const char*, unsigned long long);
""",
'orbis/Net.h': """#pragma once
#include "../stub_types.h"
struct sockaddr;
int sceNetSocket(const char*, int, int, int);
int sceNetSetsockopt(int, int, int, const void*, unsigned int);
int sceNetBind(int, struct sockaddr*, unsigned int);
""",
}
for name, text in files.items():
    path = os.path.join(out, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', newline='\n').write(text)
print('stubs written to', out)

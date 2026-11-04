"""Compiles the real server_listen() text of RPI/server.c in a tiny harness with a fake clock and fake server and RUNS it,
to see the stats line it prints. Usage: python stats_harness.py <work folder>"""
import os, re, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
work = sys.argv[1]
os.makedirs(work, exist_ok=True)

src = open(os.path.join(root, 'RPI', 'server.c'), encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
start = src.index('bool server_listen(void) {')
end = src.index('\n}\n', start) + 3
function = src[start:end]

harness = r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>

typedef struct {
    unsigned long accepted_total, refused_total, thread_failures;
    int stream_count, peak_streams;
} sb_Server;

static sb_Server* s_server;
static bool s_server_started = true;
static time_t fake_now = 1000;
static int polls = 0;

static time_t fake_time(void) { return fake_now; }
#define time(x) fake_time()

static int sb_poll_server(sb_Server* s) {
    polls++;
    fake_now += 20;                       /* every poll is 20 s later */
    if (polls <= 3) s->accepted_total += 40;      /* connections during the first minute */
    if (polls == 9) s->refused_total = 2;         /* a refusal later */
    if (polls > 12) exit(0);
    return 0;
}
static void sceKernelUsleep(unsigned int us) { (void)us; }

/* ---- the real function ---- */
""" + function + r"""
int main(void) {
    static sb_Server srv;
    srv.stream_count = 2;
    srv.peak_streams = 4;
    s_server = &srv;
    server_listen();
    return 0;
}
"""
c_file = os.path.join(work, 'harness.c')
open(c_file, 'w', newline='\n').write(harness)
print('harness written, function of', function.count('\n'), 'lines')

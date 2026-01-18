#define _GNU_SOURCE
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <time.h>
#include <sys/syscall.h>
#include <linux/sched.h>
#include <sched.h>
#include <string.h>

#define WORK_ITER 800000000ULL
#define N_COMPETITORS 40
#define BOOST_INTERVAL_NS 4000000   // 4 ms

static volatile int start_flag = 0;
static volatile int victim_done = 0;
static pid_t victim_tid;

struct sched_attr {
    uint32_t size;
    uint32_t sched_policy;
    uint64_t sched_flags;
    int32_t  sched_nice;
    uint32_t sched_priority;
    uint64_t sched_runtime;
    uint64_t sched_deadline;
    uint64_t sched_period;
    uint32_t sched_util_min;
    uint32_t sched_util_max;
};

int sched_setattr(pid_t pid, struct sched_attr *attr) {
    return syscall(SYS_sched_setattr, pid, attr, 0);
}

void set_uclamp(pid_t tid, uint32_t min, uint32_t max) {
    struct sched_attr attr;
    memset(&attr, 0, sizeof(attr));
    attr.size = sizeof(attr);
    attr.sched_util_min = min;
    attr.sched_util_max = max;

    if (sched_setattr(tid, &attr) < 0) {
        perror("sched_setattr");
    }
}

void pin_to_cpu(int cpu) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    sched_setaffinity(0, sizeof(set), &set);
}

double now_sec() {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

void* victim(void* arg) {
    pin_to_cpu(2);
    victim_tid = syscall(SYS_gettid);

    while (!start_flag);

    volatile uint64_t x = 0;
    for (uint64_t i = 0; i < WORK_ITER; i++) {
        x += i;
    }

    victim_done = 1;
    return NULL;
}

void* competitor(void* arg) {
    pin_to_cpu(2);

    while (!start_flag);

    volatile uint64_t x = 0;
    while (!victim_done) {
        x += 1;
    }

    return NULL;
}

void* booster(void* arg) {
    struct timespec ts = {0, BOOST_INTERVAL_NS};

    while (!start_flag);

    while (!victim_done) {
        set_uclamp(victim_tid, 1024, 1024);
        clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, NULL);

        set_uclamp(victim_tid, 0, 1024);
        clock_nanosleep(CLOCK_MONOTONIC, 0, &ts, NULL);
    }

    return NULL;
}

int main() {
    pthread_t v;
    pthread_t comps[N_COMPETITORS];
    
    printf("Victim + %d competitors, boost interval = 4ms\n", N_COMPETITORS);
    
    pthread_create(&v, NULL, victim, NULL);
    
    for (int i = 0; i < N_COMPETITORS; i++) {
        pthread_create(&comps[i], NULL, competitor, NULL);
    }
    
#ifdef WITH_BOOSTER
    pthread_t b;
    pthread_create(&b, NULL, booster, NULL);
#endif

    sleep(1);

    double start = now_sec();
    start_flag = 1;

    pthread_join(v, NULL);
    double end = now_sec();

    printf("Victim execution time: %.3f seconds\n", end - start);

    return 0;
}

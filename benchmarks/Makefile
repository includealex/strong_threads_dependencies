CC = gcc
CFLAGS = -Wall -pthread
TARGET = uclamp_bench.out
SRC = uclamp_benchmark.c

all: build_with build_without

build_without:
	$(CC) $(CFLAGS) -o $(TARGET)_without.out $(SRC)

build_with:
	$(CC) $(CFLAGS) -DWITH_BOOSTER -o $(TARGET)_with.out $(SRC)

run: build_with build_without
	@echo "WITHOUT booster:"
	@./$(TARGET)_without.out
	@echo "\nWITH booster:"
	@./$(TARGET)_with.out

clean:
	rm -f $(TARGET)_without.out $(TARGET)_with.out

.PHONY: all build_without build_with run clean

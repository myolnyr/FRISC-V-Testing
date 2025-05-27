#!/bin/bash

./run.sh

ISA="rv32i"

# Map main RAM (64 KB) and TEST_RESULT memory-mapped regions
BASE_SPIKE_OPTS="-m0x80000000:0x10000,0x20000000:0x1000"
START_PC=0x80000000

spike -d --isa=${ISA} ${BASE_SPIKE_OPTS} --pc=${START_PC} --log-commits ./output/bin/test1_alu.elf

#!/usr/bin/env bash

top=$(git rev-parse --show-toplevel)
cd "$top" || exit 1

ruff format yamu tests || exit 1
ruff check yamu tests || exit 1

FROM debian:bookworm-slim

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates python3 ninja-build g++-multilib gcc-multilib \
       libc6-dev:i386 libstdc++-12-dev:i386 pkg-config libnss3-dev \
    && rm -rf /var/lib/apt/lists/*

# Chromium's host tool actions in this experiment use that interpreter path.
RUN mkdir -p /opt/homebrew/bin \
    && ln -s /usr/bin/python3 /opt/homebrew/bin/python3.12

WORKDIR /workspace

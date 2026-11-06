FROM ubuntu:24.04 AS router-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git meson ninja-build pkg-config g++ \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --branch v4 --depth 1 --recurse-submodules --shallow-submodules \
    https://github.com/mavlink-router/mavlink-router.git /src/router \
    && meson setup /src/router/build /src/router --buildtype=release \
       -Dsystemdsystemunitdir=/usr/lib/systemd/system \
    && ninja -C /src/router/build

FROM ubuntu:24.04
ARG ARDUPILOT_VERSION=4.7.1
ARG ARDUPILOT_COMMIT=dbe792162d06cab66c3475fd5556bf7a120f119e
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl libstdc++6 libgcc-s1 python3 python3-venv gettext-base tini \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fL --retry 3 \
      "https://firmware.ardupilot.org/Copter/stable-${ARDUPILOT_VERSION}/SITL_x86_64_linux_gnu/arducopter" \
      -o /usr/local/bin/arducopter \
    && chmod +x /usr/local/bin/arducopter \
    && mkdir -p /opt/sitl \
    && curl -fL --retry 3 \
      "https://raw.githubusercontent.com/ArduPilot/ardupilot/${ARDUPILOT_COMMIT}/Tools/autotest/default_params/copter.parm" \
      -o /opt/sitl/copter.parm
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir pymavlink==2.4.49
RUN /opt/venv/bin/pip install --no-cache-dir \
    fastapi==0.116.1 uvicorn==0.35.0
ENV PATH="/opt/venv/bin:${PATH}"
COPY --from=router-builder /src/router/build/src/mavlink-routerd /usr/local/bin/
COPY config/router.conf.template /opt/sitl/router.conf.template
COPY scripts/start.sh scripts/check_connection.py /opt/sitl/
COPY app /opt/sitl/app
RUN chmod +x /opt/sitl/start.sh && mkdir -p /var/lib/sitl
WORKDIR /var/lib/sitl
ENTRYPOINT ["/usr/bin/tini", "--", "/opt/sitl/start.sh"]

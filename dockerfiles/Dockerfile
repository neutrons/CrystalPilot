ARG SOURCE_IMAGE=source

FROM --platform=amd64 kitware/trame:py3.10-2025-05 AS source

RUN apt update && apt install -y curl libgl1-mesa-dev libxrender1 software-properties-common xvfb
RUN add-apt-repository ppa:mozillateam/ppa
COPY scripts/setup_firefox.sh /setup_firefox.sh
RUN bash /setup_firefox.sh
RUN apt update && apt install -y firefox

COPY . /src
WORKDIR /src

RUN curl -fsSL https://pixi.sh/install.sh | sh
ENV PATH="/root/.pixi/bin:${PATH}"
RUN pixi install
SHELL [ "pixi", "run" ]
ENTRYPOINT [ "pixi", "run" ]

RUN mkdir -p /.cache /.config /.mantid /.mozilla
RUN chmod og+rwX -R /.cache /.config /.mantid /.mozilla /src


# This is a workaround that allows the COPY --from location to be defined as a build argument.
# With this, we can reference the built source image from Harbor in our pipelines, while still
# defaulting to using the previous stage for local builds.
FROM $SOURCE_IMAGE AS source_image


FROM --platform=amd64 kitware/trame:py3.10-2025-05 AS run

RUN mkdir -p /src
COPY --from=source_image /src/pyproject.toml /src/
COPY --from=source_image /src/*.lock /src/
COPY --from=source_image /src/README.md /src/
COPY --from=source_image /src/src /src/src
COPY --from=source_image /src/scripts /src/scripts
WORKDIR /src

RUN apt update && apt install -y curl gettext nginx wget
RUN chmod og+rwX -R /var/lib/nginx
RUN chmod og+rwX -R /var/log/nginx
RUN chmod og+rwX -R /etc/nginx

COPY dockerfiles/nginx.conf.template /etc/nginx/nginx.conf.template
COPY dockerfiles/supervisord.conf /etc/supervisord.conf
COPY dockerfiles/mantid.local.properties /etc/mantid.local.properties
COPY scripts/run_nginx.sh /
COPY scripts/run_trame.sh /

RUN curl -fsSL https://pixi.sh/install.sh | sh
ENV PATH="/root/.pixi/bin:${PATH}"
RUN pixi install -e production
SHELL [ "pixi", "run", "-e", "production" ]
ENTRYPOINT [ "pixi", "run", "-e", "production", "--manifest-path", "/src/pyproject.toml" ]

RUN pixi add --pypi supervisor
RUN scripts/generate_static_client.sh

RUN chmod og+rwX -R /src

CMD [ "supervisord" ]

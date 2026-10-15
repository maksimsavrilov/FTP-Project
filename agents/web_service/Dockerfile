FROM nginx:stable

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /etc/nginx/conf.d/services /run/web-service \
    && chown -R nginx:nginx /etc/nginx/conf.d/services /run/web-service

COPY agents/web_service/adapter.py /opt/web-service/adapter.py
COPY agents/web_service/nginx.conf /etc/nginx/nginx.conf

ENV WEB_SERVICE_SOCKET=/run/web-service/adapter.sock
VOLUME ["/run/web-service"]

CMD ["sh", "-c", "nginx -g 'daemon off;' & exec python3 /opt/web-service/adapter.py"]

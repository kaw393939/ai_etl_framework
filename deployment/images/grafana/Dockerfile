FROM grafana/grafana:latest

# Copy main configuration
COPY config/grafana.ini /etc/grafana/grafana.ini

# Copy dashboards
COPY config/dashboards/ /etc/grafana/dashboards/

# Copy dashboard provisioning config
COPY config/provisioning/dashboards/dashboard.yaml /etc/grafana/provisioning/dashboards/

# Copy datasource provisioning config
COPY config/provisioning/datasources/datasource.yaml /etc/grafana/provisioning/datasources/

USER grafana

EXPOSE 3000
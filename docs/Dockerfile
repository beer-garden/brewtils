FROM nginx:1.19-alpine

# Nginx configuration template
ADD ./default.conf.template /etc/nginx/templates/

# Actual static resources
COPY ./_build/html /usr/share/nginx/html


FROM nginx:alpine

# FIX: Copy the config into the special 'templates' directory
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy the HTML UI
COPY index.html /usr/share/nginx/html/index.html
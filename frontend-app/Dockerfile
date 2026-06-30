# Use the official, lightweight Nginx image
FROM nginx:alpine

# Remove default Nginx config and copy our custom configuration
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/production.conf

# Copy our HTML application into the web server directory
COPY index.html /usr/share/nginx/html/index.html

# Expose port 8080 as required by Google Cloud Run
EXPOSE 8080
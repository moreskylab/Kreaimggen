FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/app.conf
COPY static /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

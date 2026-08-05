FROM nginx:1.27-alpine

# Копируем конфигурацию Nginx
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Копируем статические файлы фронтенда и виджета
COPY widget /usr/share/nginx/html/widget
COPY widget/demo.html /usr/share/nginx/html/index.html
COPY widget/demo.html /usr/share/nginx/html/demo.html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

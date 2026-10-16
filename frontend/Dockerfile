FROM node:20-alpine AS build
WORKDIR /app
# Both files, and `npm ci`: the image must resolve the same dependency tree every
# time. Without the lockfile npm re-resolved everything from the registry on each
# build, which is not reproducible and, with npm 10.8.2, failed outright with
# "Cannot read properties of null (reading 'edgesOut')" (v1.56.0 deploy).
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

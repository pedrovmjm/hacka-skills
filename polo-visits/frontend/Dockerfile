FROM node:22-alpine AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM build AS test
CMD ["npm", "test"]

FROM mcr.microsoft.com/playwright:v1.55.1-noble AS e2e
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "run", "test:e2e"]

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80


FROM node:latest

WORKDIR /app

RUN apt update -y
RUN apt upgrade -y
RUN apt install git -y

RUN git clone https://github.com/KagariET01/DChatGPT.git /app

RUN npm install
RUN npm install -g typescript ts-node
RUN npm install --save-dev @types/node

ADD secret.json /app/secret.json
ADD config.json /app/config.json

RUN npm run build
CMD ["npm","run","start"]

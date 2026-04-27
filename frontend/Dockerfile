# Node.js ortamı
FROM node:22-alpine

WORKDIR /app

# Bağımlılıkları kopyala ve kur
COPY package*.json ./
RUN npm install

# Kaynak kodları kopyala
COPY . .

EXPOSE 5173

# Vite server'ı tüm ağ arayüzlerine (--host) açarak başlat
CMD ["npm", "run", "dev", "--", "--host"]
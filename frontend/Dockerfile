# OSINT Autonomous Analyst - Frontend
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Development mode (production should use: npm run build && npm start)
CMD ["npm", "run", "dev"]

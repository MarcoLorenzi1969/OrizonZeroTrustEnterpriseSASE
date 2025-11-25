FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY tsconfig.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src ./src

# Build TypeScript
RUN npm run build

# Copy templates to dist folder (they are not compiled by TypeScript)
RUN mkdir -p /app/dist/templates && cp -r /app/src/templates/* /app/dist/templates/

# Expose port
EXPOSE 3001

# Start service
CMD ["npm", "start"]

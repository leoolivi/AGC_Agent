#!/bin/bash
# ACG Quick Start Script

set -e

echo "🚀 ACG - Admin & Compliance Guardian"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in ACG directory
if [ ! -f "Makefile" ]; then
    echo -e "${RED}❌ Error: Run this script from the ACG root directory${NC}"
    exit 1
fi

echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.12+${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python found${NC}"

# Check Node
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node.js found${NC}"

# Check PostgreSQL or Docker
if ! command -v psql &> /dev/null && ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Neither PostgreSQL nor Docker found${NC}"
    echo "Please install either:"
    echo "  - PostgreSQL 16+ (https://www.postgresql.org/download/)"
    echo "  - Docker (https://www.docker.com/get-started)"
    exit 1
fi

if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker found${NC}"
    USE_DOCKER=true
else
    echo -e "${GREEN}✅ PostgreSQL found${NC}"
    USE_DOCKER=false
fi

echo ""
echo "🔧 Setup Options:"
echo "1. Quick Start with Docker (recommended)"
echo "2. Manual Setup"
echo "3. Exit"
echo ""
read -p "Choose option [1-3]: " option

case $option in
    1)
        echo ""
        echo "🐳 Starting with Docker..."
        
        # Start Docker services
        echo "Starting PostgreSQL and MinIO..."
        docker-compose up -d postgres minio
        
        # Wait for services
        echo "Waiting for services to be ready..."
        sleep 10
        
        # Backend setup
        echo ""
        echo "📦 Setting up backend..."
        cd backend
        
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        
        source venv/bin/activate
        pip install -q -r requirements.txt
        
        # Generate keys if .env doesn't exist
        if [ ! -f ".env" ]; then
            echo "Generating configuration keys..."
            python scripts/generate_keys.py > /tmp/acg_keys.txt
            cp .env.example .env
            
            # Extract keys
            JWT_KEY=$(grep "JWT_SECRET_KEY:" /tmp/acg_keys.txt | cut -d' ' -f2)
            FERNET_KEY=$(grep "GOOGLE_TOKEN_ENCRYPTION_KEY:" /tmp/acg_keys.txt | cut -d' ' -f2)
            
            # Update .env
            sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_KEY/" .env
            sed -i.bak "s/GOOGLE_TOKEN_ENCRYPTION_KEY=.*/GOOGLE_TOKEN_ENCRYPTION_KEY=$FERNET_KEY/" .env
            rm .env.bak
            
            echo -e "${GREEN}✅ Configuration generated${NC}"
        fi
        
        # Run migrations
        echo "Running database migrations..."
        alembic upgrade head
        
        # Initialize database
        echo "Initializing database..."
        python scripts/init_db.py
        
        cd ..
        
        # Frontend setup
        echo ""
        echo "📦 Setting up frontend..."
        cd frontend
        npm install
        cd ..
        
        echo ""
        echo -e "${GREEN}✅ Setup complete!${NC}"
        echo ""
        echo "🚀 Starting ACG..."
        echo ""
        echo "Backend will be available at: http://localhost:8000"
        echo "Frontend will be available at: http://localhost:5173"
        echo "API Docs: http://localhost:8000/docs"
        echo ""
        echo "Login credentials:"
        echo "  Email: admin@acg.local"
        echo "  Password: admin123"
        echo ""
        echo "Press Ctrl+C to stop"
        echo ""
        
        # Start services
        make run
        ;;
        
    2)
        echo ""
        echo "📝 Manual Setup"
        echo ""
        echo "Please follow these steps:"
        echo ""
        echo "1. Setup database:"
        echo "   createdb acg"
        echo ""
        echo "2. Run setup:"
        echo "   make setup"
        echo ""
        echo "3. Generate keys:"
        echo "   make generate-keys"
        echo ""
        echo "4. Configure .env:"
        echo "   cp backend/.env.example backend/.env"
        echo "   # Edit backend/.env with generated keys"
        echo ""
        echo "5. Verify setup:"
        echo "   make verify"
        echo ""
        echo "6. Start application:"
        echo "   make run"
        echo ""
        ;;
        
    3)
        echo "Exiting..."
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac

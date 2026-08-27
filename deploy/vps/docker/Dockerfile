FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    docker-compose \
    git \
    python3 \
    python3-pip \
    curl \
    jq \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip3 install pandas requests python-dotenv

# Create app user
RUN useradd -m -s /bin/bash scraper && usermod -aG docker scraper

# Setup directories
RUN mkdir -p /opt/scraper/{data,logs,scripts,output} && chown -R scraper:scraper /opt/scraper

USER scraper
WORKDIR /opt/scraper

# Copy scripts
COPY --chown=scraper:scraper scripts/ /opt/scraper/scripts/

# Default command
CMD ["bash"]

#!/usr/bin/env python3
"""
Production monitoring setup script for Golf CMS
Sets up health checks, logging, and basic monitoring endpoints
"""

import os
import json
from datetime import datetime
from pathlib import Path

def create_monitoring_config():
    """Create monitoring configuration files"""
    
    monitoring_dir = Path("monitoring")
    monitoring_dir.mkdir(exist_ok=True)
    
    health_config = {
        "checks": {
            "database": {
                "type": "postgresql",
                "connection_string": "${DATABASE_URL}",
                "timeout": 5
            },
            "supabase_storage": {
                "type": "http",
                "url": "${SUPABASE_URL}/storage/v1/bucket",
                "timeout": 5
            },
            "email_service": {
                "type": "smtp",
                "server": "${SMTP_SERVER}",
                "port": "${SMTP_PORT}",
                "timeout": 10
            }
        },
        "intervals": {
            "health_check": 30,
            "metrics_collection": 60,
            "log_rotation": 3600
        }
    }
    
    with open(monitoring_dir / "health_config.json", "w") as f:
        json.dump(health_config, f, indent=2)
    
    docker_health = """#!/bin/bash

curl -f http://localhost:8000/healthz || exit 1

python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('Database: OK')
except Exception as e:
    print(f'Database: ERROR - {e}')
    exit(1)
"

echo "Health check: PASSED"
"""
    
    with open(monitoring_dir / "health_check.sh", "w") as f:
        f.write(docker_health)
    
    os.chmod(monitoring_dir / "health_check.sh", 0o755)
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "detailed"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/golf_cms.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "level": "INFO",
                "formatter": "json"
            }
        },
        "loggers": {
            "golf_cms": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            }
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console"]
        }
    }
    
    with open(monitoring_dir / "logging_config.json", "w") as f:
        json.dump(logging_config, f, indent=2)
    
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    print("✅ Monitoring configuration created successfully!")
    print(f"📁 Files created in: {monitoring_dir.absolute()}")
    print("📋 Next steps:")
    print("1. Configure SendGrid API key in .env file")
    print("2. Set up log aggregation service (e.g., CloudWatch, ELK)")
    print("3. Configure alerting for critical errors")
    print("4. Set up uptime monitoring (e.g., Pingdom, UptimeRobot)")

if __name__ == "__main__":
    create_monitoring_config()

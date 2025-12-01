📊 Kafka Real-time Dashboard with Elasticsearch
A complete real-time messaging dashboard that streams messages through Kafka, visualizes them in a web interface, and stores/analyzes them in Elasticsearch with Kibana visualization.

🚀 Quick Start
Prerequisites
Docker & Docker Compose

Python 3.9+ (for local development)

Web browser

Installation & Running
Clone/Create the project structure:

bash
mkdir kafka-dashboard
cd kafka-dashboard
Create the required files (copy from the sections below or from the provided code)

Start all services:

bash
docker-compose up --build
Access the applications:

Dashboard: http://localhost:5000

Kibana: http://localhost:5601

Elasticsearch API: http://localhost:9200

📁 Project Structure
text
kafka-dashboard/
├── docker-compose.yml           # Container orchestration
├── Dockerfile                   # Python app container
├── requirements.txt            # Python dependencies
├── app.py                      # Flask application
├── templates/
│   └── index.html             # Web dashboard
├── static/
│   └── style.css              # CSS styles
└── logstash/
    └── logstash.conf          # Kafka → Elasticsearch pipeline
🛠️ Services Overview
Service	Port	Purpose
Zookeeper	22181	Kafka dependency
Kafka	29092	Message broker
Elasticsearch	9200	Data storage/search
Kibana	5601	Data visualization
Logstash	-	Data pipeline
Dashboard App	5000	Web interface
📝 Usage Guide
1. Sending Messages
Open http://localhost:5000

Fill in: Sender Name, Category, Message

Click "Send to Kafka & Elasticsearch"

Watch messages appear in real-time

2. Viewing in Kibana
Open http://localhost:5601

Go to "Stack Management" → "Data Views"

Create data view: kafka-dashboard-*

Go to "Discover" to see messages

Create dashboards and visualizations

3. API Endpoints
GET /api/health - Service health check

GET /api/elasticsearch/indices - List indices

GET /api/elasticsearch/search - Search messages

POST /api/send - Send message (JSON)

4. Command Line Testing
bash
# List Kafka topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check Elasticsearch indices
curl http://localhost:9200/_cat/indices?v

# Send test message
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{"sender":"test","message":"Hello","category":"info"}'
🔧 Configuration
Environment Variables
KAFKA_BOOTSTRAP_SERVERS: Kafka connection (default: kafka:9092)

KAFKA_TOPIC: Kafka topic name (default: dashboard-messages)

FLASK_SECRET_KEY: Flask session secret

Customizing
Edit logstash/logstash.conf to modify data processing

Update templates/index.html for UI changes

Modify app.py for business logic changes

🐛 Troubleshooting

Common Issues
No data in Kibana:

Wait 2-3 minutes for services to start

Check Logstash logs: docker-compose logs logstash

Verify Elasticsearch has indices: curl localhost:9200/_cat/indices

Port conflicts:

Stop local Kafka/Zookeeper if running

Change ports in docker-compose.yml

Connection errors:

Check all services are running: docker-compose ps

View logs: docker-compose logs -f

Useful Commands
bash
# Restart specific service
docker-compose restart dashboard-app

# View real-time logs
docker-compose logs -f

# Clean everything and restart
docker-compose down -v
docker-compose up --build

# Enter container shell
docker-compose exec dashboard-app bash

📊 Features

✅ Real-time message streaming

✅ WebSocket-based live updates

✅ Elasticsearch storage

✅ Kibana visualization

✅ Multi-user support

✅ Message categorization

✅ Health monitoring

✅ REST API

🤝 Contributing

Fork the repository

Create feature branch

Commit changes

Push to branch

Create Pull Request

📄 License
MIT License - see LICENSE file

🙏 Acknowledgments
Apache Kafka

Elastic Stack (ELK)

Flask & SocketIO

Docker community

📞 Support

For issues and questions:

Check troubleshooting section

Review logs with docker-compose logs

Open GitHub issue with logs and steps to reproduce

Happy Streaming! 🚀


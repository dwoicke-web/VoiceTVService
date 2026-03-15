# VoiceTV Service

A comprehensive voice-controlled entertainment system for managing multiple TVs in your basement. Search across all your streaming services and control playback via a web UI or voice commands through your Sonos speakers.

## 🎯 Features

- **Multi-TV Control**: Manage 5 TVs (1x 75" Samsung + 4x 32" Fire TVs)
- **Unified Search**: Search across YouTubeTV, Peacock, ESPN+, Amazon Prime, and HBO Max
- **Voice Control**: Control TVs using voice commands through Sonos speakers
- **Web Interface**: Modern, responsive web UI for managing your entertainment
- **Smart Routing**: Automatically routes content to available TVs and services

## 📋 TV Setup

Your basement entertainment system consists of:

```
┌─────────────────────────────────────┐
│    Upper Left (32")  |  Upper Right  │
│       Fire TV        |    Fire TV     │
│                                      │
│         Big Screen (75")             │
│         Samsung Smart TV             │
│                                      │
│    Lower Left (32")  |  Lower Right  │
│       Fire TV        |    Fire TV     │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 14+
- npm or yarn
- Git

### Installation

1. **Clone the repository**
   ```bash
   cd /home/orangepi/Apps/VoiceTVService
   git clone . .
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate

   # Install dependencies
   cd backend
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Configure Environment**
   ```bash
   # Copy environment template
   cp ../.env.example ../.env

   # Edit .env with your API credentials
   nano ../.env
   ```

### Running the Application

**Terminal 1 - Backend:**
```bash
cd backend
source ../venv/bin/activate
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

The web interface will be available at `http://localhost:3000`
The backend API will be at `http://localhost:5000`

## 🔑 API Credentials Required

To use all features, you'll need to set up API credentials for:

- **YouTubeTV**: [Get API Key](https://www.youtube.com/tv)
- **Peacock**: [Developer Portal](https://developer.peacocktv.com/)
- **ESPN+**: [ESPN Developer](https://developer.espn.com/)
- **Amazon Prime Video**: [AWS Developer](https://developer.amazon.com/)
- **HBO Max**: [HBO Max API](https://www.hbomax.com/)
- **Samsung SmartThings**: [SmartThings Developer](https://smartthings.developer.samsung.com/)
- **Google Cloud Speech-to-Text**: [Google Cloud Console](https://console.cloud.google.com/)
- **Sonos**: [Sonos Developer](https://developer.sonos.com/)

## 📚 Project Structure

```
VoiceTVService/
├── backend/                    # Flask backend
│   ├── apis/                  # Third-party API integrations
│   │   ├── streaming/         # Streaming service APIs
│   │   ├── tv_control/        # TV control APIs
│   │   └── sonos/             # Sonos speaker integration
│   ├── voice/                 # Voice processing
│   ├── database/              # Database models
│   ├── routes/                # API endpoints
│   ├── app.py                 # Main Flask app
│   ├── config.py              # Configuration
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # React web UI
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── styles/            # CSS stylesheets
│   │   ├── App.jsx            # Main app component
│   │   └── index.js           # React entry point
│   ├── public/
│   │   └── index.html         # HTML template
│   └── package.json           # npm dependencies
│
├── docs/                       # Documentation
│   ├── API.md                 # API documentation
│   ├── SETUP.md              # Setup guide
│   └── ARCHITECTURE.md       # Architecture details
│
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## 🔌 API Endpoints

### TVs
- `GET /api/tvs` - Get all available TVs

### Search
- `GET /api/search/all` - Search all streaming services
- `GET /api/search/youtube-tv` - Search YouTubeTV
- `GET /api/search/peacock` - Search Peacock
- `GET /api/search/espn-plus` - Search ESPN+
- `GET /api/search/amazon-prime` - Search Prime Video
- `GET /api/search/hbo-max` - Search HBO Max

### TV Control
- `POST /api/tv/launch` - Launch content on a TV
- `POST /api/tv/power` - Control TV power
- `POST /api/tv/volume` - Control TV volume
- `POST /api/tv/input` - Change TV input source

### Voice
- `POST /api/voice/command` - Process voice command (coming soon)

### Health
- `GET /health` - Health check endpoint

## 🛠️ Development

### Backend Development
- Flask API Framework
- RESTful API design
- CORS enabled for frontend communication
- Mock endpoints for testing

### Frontend Development
- React 18+ with Hooks
- Responsive CSS Grid layout
- Axios for HTTP requests
- Component-based architecture

## 📝 Voice Command Examples

Once voice control is implemented, you'll be able to say:

- "Hey Sonos, put the Pittsburgh Steelers on the Big Screen"
- "Hey Sonos, find The Neighbors and put it on Upper Left TV"
- "Hey Sonos, show me live sports on Big Screen"
- "Hey Sonos, play on all TVs"

## 🧪 Testing

### Frontend Tests
```bash
cd frontend
npm test
```

### Backend Tests (coming soon)
```bash
cd backend
python -m pytest
```

## 📦 Deployment

### Orange Pi Service Setup
```bash
# Create systemd service
sudo nano /etc/systemd/system/voicetv.service

# Enable and start service
sudo systemctl enable voicetv
sudo systemctl start voicetv
```

## 🐛 Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.9+)
- Verify virtual environment: `source venv/bin/activate`
- Check dependencies: `pip install -r requirements.txt`

### Frontend won't start
- Check Node version: `node --version` (should be 14+)
- Clear node_modules: `rm -rf node_modules && npm install`
- Check port 3000 is available: `lsof -i :3000`

### API Connection Issues
- Ensure backend is running on port 5000
- Check CORS settings in config.py
- Verify environment variables in .env file

## 📞 Support

For issues or questions, please refer to the documentation in the `docs/` directory or check the GitHub repository.

## 📄 License

This project is proprietary. All rights reserved.

## 🎉 Roadmap

### Phase 1 (Current): Web UI Foundation ✅
- [x] Project structure setup
- [x] React components for TV layout
- [x] Search interface
- [x] Mock API endpoints

### Phase 2: Backend Search Integration
- [ ] YouTubeTV API integration
- [ ] Peacock API integration
- [ ] ESPN+ API integration
- [ ] Prime Video API integration
- [ ] HBO Max API integration
- [ ] Unified search engine

### Phase 3: Frontend-Backend Integration
- [ ] Connect UI to real search APIs
- [ ] Real-time result updates
- [ ] Search history and suggestions

### Phase 4: TV Control Integration
- [ ] Samsung SmartThings API
- [ ] Fire TV API integration
- [ ] Device discovery and registration
- [ ] Content launching to TVs

### Phase 5: Sonos & Voice Integration
- [ ] Sonos speaker discovery
- [ ] Audio capture from speakers
- [ ] Google Cloud Speech-to-Text
- [ ] Natural language processing
- [ ] Voice command execution

### Phase 6: Polish & Optimization
- [ ] Error handling and logging
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Production deployment

---

**Happy streaming! 🎬**

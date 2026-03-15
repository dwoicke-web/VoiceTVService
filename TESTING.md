# Testing the VoiceTV Web UI

Follow these steps to start the application and test the web interface.

## Prerequisites
✅ Backend dependencies installed in `venv/`
✅ Frontend dependencies installed in `frontend/node_modules/`
✅ Flask configured to run on port 5002
✅ React configured to proxy to port 5002

## Quick Start (Two Terminal Windows)

### Terminal 1: Start the Flask Backend

```bash
cd /home/orangepi/Apps/VoiceTVService
source venv/bin/activate
cd backend
python app.py
```

You should see output like:
```
 * Running on http://0.0.0.0:5002
 * Debug mode: on
```

### Terminal 2: Start the React Frontend

```bash
cd /home/orangepi/Apps/VoiceTVService/frontend
npm start
```

You should see output like:
```
Compiled successfully!
You can now view voicetv-frontend in the browser.
  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

## Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

Or from another machine on your network:
```
http://<orangepi-ip>:3000
```

## What to Test

### 1. TV Layout Visualization
- [ ] Page loads successfully
- [ ] See 5 TVs displayed (1 large center, 4 smaller around it)
- [ ] TV names, sizes, and types are displayed
- [ ] Background has gradient color scheme

### 2. TV Selection
- [ ] Click on each TV - it should highlight with a purple glow
- [ ] Selected TV info appears below the layout
- [ ] Status shows "online" for all TVs
- [ ] Can select different TVs

### 3. Search Interface
- [ ] Search bar is visible with placeholder text
- [ ] Content type filter dropdown works
- [ ] Can type search queries
- [ ] Search button is clickable

### 4. Search Results
- [ ] Click Search (with any query) - mock results appear
- [ ] Results show as cards with:
  - [ ] Poster images
  - [ ] Title and type
  - [ ] Available services badges
  - [ ] Available TV chips
  - [ ] "Play on [TV Name]" button

### 5. Launch Content
- [ ] Select a TV first
- [ ] Search for something
- [ ] Click "Play on [TV Name]" button
- [ ] See a success message or confirmation

### 6. Responsive Design
- [ ] Resize browser window - layout should adapt
- [ ] On mobile width - UI should stack properly
- [ ] All buttons and inputs remain clickable

### 7. Error Handling
- [ ] If Flask backend is down, you should see an error message
- [ ] Try searching with no TV selected - should show prompt

## API Endpoints to Check

While both servers are running, you can test these endpoints:

**Health Check:**
```bash
curl http://localhost:5002/health
```
Should return:
```json
{
  "status": "healthy",
  "service": "VoiceTV Service",
  "version": "0.1.0"
}
```

**Get TVs:**
```bash
curl http://localhost:5002/api/tvs
```
Should return list of 5 TVs with their configuration.

**Search (Mock):**
```bash
curl "http://localhost:5002/api/search/all?query=Breaking%20Bad&content_type=show"
```
Should return mock search results.

## Troubleshooting

### Flask backend won't start
```bash
# Check if port 5002 is available
lsof -i :5002

# If occupied, kill the process
kill -9 <PID>

# Or change the port in backend/app.py
```

### React won't start
```bash
# Clear npm cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### CORS errors in browser console
- Flask backend should be running on port 5002
- Frontend proxy in package.json should point to http://localhost:5002
- Verify with: `curl http://localhost:5002/health`

### Can't reach frontend from another machine
- Check Orange Pi IP: `hostname -I`
- Use: `http://<orange-pi-ip>:3000`
- Ensure firewall allows port 3000

## Next Steps

After testing the UI successfully:

1. **Phase 2**: Implement real streaming service API integrations
2. **Phase 3**: Connect UI to real search results
3. **Phase 4**: Add TV control (SmartThings + Fire TV)
4. **Phase 5**: Add Sonos voice command support

---

**Happy testing! 🎉**
